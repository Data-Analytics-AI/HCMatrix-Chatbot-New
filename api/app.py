from fastapi.responses import FileResponse, JSONResponse
from fastapi import FastAPI, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import *
import uuid
import time
import base64
from model.azure_oai import AzureOAI
import asyncio
from services.cache_service import LRUCache
from module.utils import config
from services.cosmos_service import CosmosClient, AsyncCosmosClient
from hcm_chatbot.router import chatbot_entry_execution
from data_preprocessing.gold_layer import GoldLayerUtils
from api.schema import AudioChatSchema, ChatResponseSchema
from module.spk import SpeechSynthesizerWrapper
import azure.cognitiveservices.speech as speechsdk

# ===================== Initialize model and embeddings ====================
# ===========================================================================

# Instantiating an instance of the LLM and Speech Synthesis class.
azure_oai_conn = AzureOAI("4O")
llm_4O = azure_oai_conn()

# speech_out = spk.HCMSpeechOut()
chatbot_cache = LRUCache(
    capacity=120
)  # This cache is ephemeral to the life of the application.

# initialize connection with DB to read employee sql files

adls_credentials_params = config["production"]["adls_credentials"]
gold_container_name = config["production"]["adls_credentials"][
    "goldlayer_container_name"
]
gold_account_name = config["production"]["adls_credentials"]["goldlayer_account_name"]
gold_adls_conn = GoldLayerUtils(
    gold_container_name, adls_credentials_params, gold_account_name
)

# Azure Speech Config
speech_config = speechsdk.SpeechConfig(
    subscription=config["production"]["speech_service"]["key"], region="eastus"
)
wrapper = SpeechSynthesizerWrapper(speech_config)

client = AsyncCosmosClient(
    database_name="hcm-chatbot", collection_name="user-chat"
)  # ✅ Async Client

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
        "status": "HCMatrix Chatbot is up! Endpoints are `/chat` and `/chat-history`."
    }


@app.post("/chat", status_code=status.HTTP_200_OK, response_model=ChatResponseSchema)
async def chatbot(request_model: AudioChatSchema) -> ChatResponseSchema:

    if (
        not request_model.user_query.strip()
    ):  # Check if user_query is empty or just spaces
        raise HTTPException(status_code=400, detail="User query cannot be empty")

    for _ in range(2):
        try:
            response_id = str(uuid.uuid4())

            # Generating model response
            response = await chatbot_entry_execution(
                request_model.user_query,
                request_model.employee_metadata,
                llm_4O,
                gold_adls_conn,
                chatbot_cache,
            )

            audio_response_data = None

            # Run audio synthesis in the background (non-blocking)
            if request_model.audio:
                try:
                    print("Generating user query from audio.")
                    audio_task = asyncio.create_task(wrapper.synthesize(response))
                    audio_response_data = base64.b64encode(await audio_task).decode(
                        "utf-8"
                    )
                except Exception as e:
                    print(f"Error generating audio: {e}")
                    audio_response_data = None  # Ensure text response is still returned

            current_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

            # Generate output metadata
            response_data = {
                "employee_metadata": request_model.employee_metadata.dict(),
                "question": request_model.user_query,
                "answer": response,
                "timestamp": current_time_str,
                "audio": (
                    audio_response_data
                    if request_model.audio and audio_response_data is not None
                    else ""
                ),
                "request_id": response_id,
                "chat_id": request_model.chat_id,
            }

            # Remove "audio" efficiently
            response_data_without_audio = response_data.copy()
            response_data_without_audio.pop("audio", None)

            # Async database insertion (non-blocking)
            try:
                print("Attempting to store chat history in database")
                await client.insert_one(
                    response_data_without_audio
                )  # ✅ Fully async DB call
                print("Successfully stored chat history in database")
            except Exception as e:
                print(
                    f"Error occurred while attempting to store message history in DB {e}"
                )

            return JSONResponse(content=response_data)

        except Exception as e:
            print(f"Unexpected error: {e}")
            raise HTTPException(status_code=500, detail="Unexpected server error")


@app.get("/chat-history", status_code=status.HTTP_200_OK)
def fetch_chat_id(
    chat_id: str = Query(..., description="Chat ID from FE"),
    employee_id: str = Query(
        ..., description="Employee ID to retrieve chat history from"
    ),
    company_id: str = Query(..., description="Employee company Id"),
) -> List[ChatResponseSchema]:
    """
    The purpose of this function is to fetch the history of the conversations between
    the user and the assistant so that all conversations are in context.
    """
    query = {
        "chat_id": chat_id,
        "employee_metadata.id": employee_id,
        "employee_metadata.company_id": company_id,
    }

    with CosmosClient(
        database_name="hcm-chatbot", collection_name="user-chat"
    ) as client:
        chat_history_pymongo = client.fetch_many(query)
        chat_history = [history for history in chat_history_pymongo]
        return chat_history


@app.get("/all-chat-history", status_code=status.HTTP_200_OK)
def fetch_chat_id(
    employee_id: str = Query(
        ..., description="Employee ID to retrieve chat history from"
    ),
    company_id: str = Query(..., description="Employee company Id"),
) -> List[ChatResponseSchema]:
    """
    The purpose of this function is to fetch all the history of the conversations between
    the user and the assistant so that all conversations are in context.
    """
    query = {
        "employee_metadata.id": employee_id,
        "employee_metadata.company_id": company_id,
    }

    with CosmosClient(
        database_name="hcm-chatbot", collection_name="user-chat"
    ) as client:
        chat_history_pymongo = client.fetch_many(query)
        chat_history = [history for history in chat_history_pymongo]
        return chat_history


@app.on_event("shutdown")
def shutdown_event():
    """Ensure connection closes when the API server stops."""
    wrapper.close_connection()
