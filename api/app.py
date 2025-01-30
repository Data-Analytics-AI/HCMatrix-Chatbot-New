from fastapi.responses import FileResponse, JSONResponse
from fastapi import FastAPI, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import *
import uuid
import copy
import time
import os

from speech_impl import spk
from model.azure_oai import AzureOAI

from services.cache_service import LRUCache
from module.utils import config
from services.cosmos_service import CosmosClient
from hcm_chatbot.router import chatbot_entry_execution
from data_preprocessing.gold_layer import GoldLayerUtils
from api.schema import AudioChatSchema, ChatResponseSchema, ChatHistory
from module.log_config import logger

# ===================== Initialize model and embeddings ====================
# ===========================================================================

# Instantiating an instance of the LLM and Speech Synthesis class.
azure_oai_conn = AzureOAI("4O")
llm_4O = azure_oai_conn()

speech_out = spk.HCMSpeechOut()
chatbot_cache = LRUCache(capacity=120)  # This cache is ephemeral to the life of the application.

# initialize connection with DB to read employee sql files

adls_credentials_params = config['production']['adls_credentials']
gold_container_name = config['production']['adls_credentials']['goldlayer_container_name']
gold_account_name = config['production']['adls_credentials']['goldlayer_account_name']
gold_adls_conn = GoldLayerUtils(gold_container_name, adls_credentials_params, gold_account_name)

app = FastAPI()
origins = [
    "http://48.217.20.68:5000",
    "https://deploy-preview-301--hcmatrix-saas.netlify.app",
    "https://hcmatrix-saas.netlify.app",
    "http://127.0.0.1:5000",
    "http://localhost:3000",
    "https://app.hcmatrix.com"
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
    return {"status": "HCMatrix Chatbot is up! Endpoints are `/chat` and `/chat-history`."}


@app.post("/chat", status_code=status.HTTP_200_OK, response_model=ChatResponseSchema)
async def chatbot(request_model: AudioChatSchema) -> ChatResponseSchema:
    for _ in range(2):
        try:
            response_id = str(uuid.uuid4())
            audio_response_data = None

            # generating model response
            response = chatbot_entry_execution(request_model.user_query, request_model.employee_metadata, llm_4O,
                                               gold_adls_conn, chatbot_cache)

            # attempting to synthesize audio for the above model response
            if request_model.audio:
                logger.info('Generating user query from audio.')
                audio_response_data = await speech_out.synthesize_english_to_filepath(response, response_id)
                if audio_response_data is None:
                    logger.error("And error occurred. Audio could not be used.")
                    raise HTTPException(status_code=500, detail="Error in generation audio response")

            local_ip = config['production']['local_ip']

            current_time = time.localtime()
            current_time_str = time.strftime("%Y-%m-%d %H:%M:%S", current_time)

            # Generate output metadata
            response_data = {
                "employee_metadata": request_model.employee_metadata.dict(),
                "question": request_model.user_query,
                "answer": response,
                "timestamp": current_time_str,
                "audio": f"{local_ip}/download_audio/?file={audio_response_data}" if request_model.audio else "",
                # TODO: 1. Security risk as it exposes the IP of the VM.
                # TODO: 2. Scalability issue.
                # TODO: 3. Deployment issues as the code will be running in a docker container.
                "request_id": response_id,
                "chat_id": request_model.chat_id
            }

            with CosmosClient(database_name="hcm-chatbot", collection_name="user-chat") as client:
                # TODO: Add async to the with clause for MongoDB connection.
                logger.info("Attempting to store chat history in database")
                try:
                    client.insert_one(copy.deepcopy(response_data))
                    logger.info("Successfully stored chat history in database")
                except Exception as e:
                    logger.error(f"Error occurred while attempting to store message history in DB {e}")

            return JSONResponse(content=response_data)

        except Exception as reason:
            raise HTTPException(status_code=500, detail=str(reason))


@app.get("/download_audio/")
async def download_audio_file(file: str):
    """
    This function helps with downloading generated audio which has been
    synthesized and saved to memory.
    """
    if not os.path.exists(file):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(path=file, media_type="audio/mpeg")


@app.get("/chat-history", status_code=status.HTTP_200_OK)
def fetch_chat_id(
        chat_id: str = Query(..., description="Chat ID from FE"),
        employee_id: str = Query(..., description="Employee ID to retrieve chat history from"),
        company_id: str = Query(..., description="Employee company Id")
) -> List[ChatResponseSchema]:
    """
    The purpose of this function is to fetch the history of the conversations between
    the user and the assistant so that all conversations are in context.
    """
    query = {
        "chat_id": chat_id,
        "employee_metadata.id": employee_id,
        "employee_metadata.company_id": company_id
    }

    with CosmosClient(database_name="hcm-chatbot", collection_name="user-chat") as client:
        chat_history_pymongo = client.fetch_many(query)
        chat_history = [history for history in chat_history_pymongo]
        return chat_history


@app.get("/all-chat-history", status_code=status.HTTP_200_OK)
def fetch_chat_id(
        employee_id: str = Query(..., description="Employee ID to retrieve chat history from"),
        company_id: str = Query(..., description="Employee company Id")
) -> List[ChatResponseSchema]:
    """
    The purpose of this function is to fetch all the history of the conversations between
    the user and the assistant so that all conversations are in context.
    """
    query = {
        "employee_metadata.id": employee_id,
        "employee_metadata.company_id": company_id
    }

    with CosmosClient(database_name="hcm-chatbot", collection_name="user-chat") as client:
        chat_history_pymongo = client.fetch_many(query)
        chat_history = [history for history in chat_history_pymongo]
        return chat_history
