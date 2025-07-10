from fastapi.responses import StreamingResponse, ORJSONResponse
from fastapi import FastAPI, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import uuid
import time
from module.azure_oai import AzureOAI
from module.cache_service import LRUCache
from module.utils import config
from module.cosmos_service import AsyncCosmosClient
from hcm_chatbot.router import chatbot_entry_execution
from module.gold_layer import GoldLayerUtilsAsync
from api.schema import ChatInputSchema, ChatResponseSchema, AudioInput
from module.spk import SpeechSynthesizerWrapper
from azure.cognitiveservices import speech as speechsdk

# ===================== Initialize model and embeddings ====================
# ===========================================================================

# Instantiating an instance of the LLM and Speech Synthesis class.
azure_oai_conn = AzureOAI("4O")
llm_4O = azure_oai_conn()

chatbot_cache = LRUCache(
    capacity=120
)  # This cache is ephemeral to the life of the application.

# initialize connection with DB to read employee sql files
adls_credentials_params = config["production"]["adls_credentials"]
gold_container_name = config["production"]["adls_credentials"]["goldlayer_container_name"]
gold_account_name = config["production"]["adls_credentials"]["goldlayer_account_name"]
gold_adls_conn = GoldLayerUtilsAsync(
    gold_container_name, adls_credentials_params, gold_account_name
)

# Azure Speech Config
speech_config = speechsdk.SpeechConfig(
    subscription=config["production"]["speech_service"]["key"], region="eastus"
)
wrapper = SpeechSynthesizerWrapper(speech_config)
CHUNK_SIZE = 4096  # 4KB per chunk


async def audio_stream(text: str):
    """Streams the synthesized audio in chunks.

    Args:
        text (str): The input text to be converted into speech.

    Yields:
        bytes: Chunks of synthesized audio data.

    Raises:
        HTTPException: If audio synthesis fails.
    """
    audio_bytes = await wrapper.synthesize(text)  # Directly streaming from Azure

    if not audio_bytes:
        raise HTTPException(status_code=500, detail="Audio synthesis failed")

    for i in range(0, len(audio_bytes), CHUNK_SIZE):
        yield audio_bytes[i:i + CHUNK_SIZE]


async_client = AsyncCosmosClient(
    database_name="hcm-chatbot", collection_name="user-chat"
)  # ✅ Async Client for cusmos DB

app = FastAPI()
origins = [
    "http://48.217.20.68:5000",
    "https://deploy-preview-301--hcmatrix-saas.netlify.app",
    "https://hcmatrix-saas.netlify.app",
    "http://127.0.0.1:5000",
    "http://localhost:3000",
    "https://app.hcmatrix.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===================== Initialize API =================================
# =======================================================================

print("Initializing API....")


@app.get("/", status_code=status.HTTP_200_OK)
def home():
    return {
        "status": "HCMatrix Chatbot is up! Endpoints are `/chat`, `/audio`, `/chat-history` and `all-chat-history`."
    }


# ===================== Chatbot API (Text Response Only) =======================
@app.post("/chat", status_code=status.HTTP_200_OK, response_model=ChatResponseSchema, response_class=ORJSONResponse)
async def chatbot(request_model: ChatInputSchema) -> ORJSONResponse:
    """Processes user queries and returns chatbot responses."""

    if not request_model.user_query.strip():
        raise HTTPException(status_code=400, detail="User query cannot be empty")

    response_id = str(uuid.uuid4())

    try:
        # Generate chatbot response
        response = await chatbot_entry_execution(
            request_model.user_query,
            request_model.employee_metadata,
            llm_4O,
            gold_adls_conn,
            chatbot_cache,
        )

        current_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

        response_data = {
            "employee_metadata": request_model.employee_metadata.dict(),
            "question": request_model.user_query,
            "answer": response,
            "timestamp": current_time_str,
            "request_id": response_id,
            "chat_id": request_model.chat_id,
        }
        print("*" * 20)
        print(response_data)

        # 🔹 Store directly to MongoDB (without buffering)
        try:
            await async_client.insert_one(response_data)
            print("✅ Chat history stored successfully")
        except Exception as db_error:
            print(f"❌ Database error: {db_error}")
            # Continue with response even if DB fails
        
        # Return response data (without _id)
        return ORJSONResponse(response_data)

    except Exception as e:
        print(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Unexpected server error")


async def store_chat_history(chat_data: dict):
    """Stores chat history in the database asynchronously."""
    try:
        await async_client.insert_one(chat_data)
    except Exception as e:
        print(f"Error storing chat history: {e}")


# ===================== Audio Synthesis API (Separate) =======================
@app.post("/audio", status_code=200)
async def generate_audio(input_data: AudioInput):
    """Generates and streams speech audio from text input.

    Args:
        input_data (AudioInput): The input data containing the text to be
            converted into speech.

    Returns:
        StreamingResponse: A streamed audio response in MP3 format.

    Raises:
        HTTPException: If the input text is empty (400).
        HTTPException: If an error occurs during audio synthesis (500).
    """
    if not input_data.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    try:
        print("Streaming audio response ...")
        return StreamingResponse(audio_stream(input_data.text), media_type="audio/mpeg")

    except Exception as e:
        print(f"Error generating audio: {e}")
        raise HTTPException(status_code=500, detail="Audio synthesis failed")


@app.get("/chat-history", status_code=status.HTTP_200_OK)
async def fetch_chat_id(
        chat_id: str = Query(..., description="Chat ID from FE"),
        employee_id: str = Query(
            ..., description="Employee ID to retrieve chat history from"
        ),
        company_id: str = Query(..., description="Employee company Id"),
) -> List[ChatResponseSchema]:
    """Fetches the conversation history between the user and the assistant.

    Args:
        chat_id (str): The unique identifier for the chat session.
        employee_id (str): The unique identifier of the employee.
        company_id (str): The unique identifier of the company.

    Returns:
        List[ChatResponseSchema]: A list of chat history records matching the given identifiers.

    Raises:
        HTTPException: If an error occurs during retrieval.
    """
    query = {
        "chat_id": chat_id,
        "employee_metadata.id": employee_id,
        "employee_metadata.company_id": company_id,
    }

    return await async_client.fetch_many(query)  # Add await here


@app.get("/all-chat-history", status_code=status.HTTP_200_OK)
async def fetch_all_chat_id(
        employee_id: str = Query(
            ..., description="Employee ID to retrieve chat history from"
        ),
        company_id: str = Query(..., description="Employee company Id"),
):
    """Fetches the complete conversation history of a user with the assistant.

    Args:
        employee_id (str): The unique identifier of the employee.
        company_id (str): The unique identifier of the company.

    Returns:
        dict: A grouped chat history for the given employee across all chat sessions.

    Raises:
        HTTPException: If an error occurs during retrieval.
    """
    query = {
        "employee_metadata.id": employee_id,
        "employee_metadata.company_id": company_id,
    }
    return await async_client.fetch_and_group_by_key(query)


@app.on_event("shutdown")
async def shutdown_event():
    """Handles cleanup operations when the API server stops.

    This function ensures that all active connections are properly closed,
    including the speech synthesis wrapper, database connections, and
    Azure Data Lake Storage (ADLS) sessions.

    Raises:
        Exception: If any shutdown operation encounters an error.
    """
    wrapper.close_connection()
    await async_client.on_shutdown()  # Ensure clean shutdown
    await gold_adls_conn.close()  # 🔥 Ensure ADLS session cleanup
