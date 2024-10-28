
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
#from rag_engine.emdedder import EmbedChunks
#from rag_engine.pinecone_ import PineconeDB
# from rag_engine.retriever_ import Retriever
from services.cache_service import LRUCache
from config.params import credentials_config
from services.cosmos_service import CosmosClient
from hcm_chatbot.router import chatbot_entry_execution
from data_preprocessing.gold_layer import GoldLayerUtils
from api.schema import AudioChatSchema, ChatResponseSchema, ChatHistory

### ===================== Initialize model and embeddings ====================
## ===========================================================================


azure_oai_conn = AzureOAI("4O")
llm_4O = azure_oai_conn()

speech_out = spk.HCMSpeechOut()
chatbot_cache = LRUCache(capacity=120) ## This cache is ephemeral to the live of the application.

# initialize connection with DB to read employee sql files
adls_credentials_params     = credentials_config['adls_credentials']
gold_container_name         = credentials_config['adls_credentials']['goldlayer_container_name']
gold_account_name           = credentials_config['adls_credentials']['goldlayer_account_name']
gold_adls_conn  = GoldLayerUtils(gold_container_name, adls_credentials_params, gold_account_name)

# embedding_query = EmbedChunks().embedding_query
# pineconedb = PineconeDB()

# index = pineconedb.index
# retriever = Retriever(index, embedding_query)

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
    allow_origins=origins, #["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


### ===================== Initialize API =================================
## =======================================================================

print ("Initializing API....")
@app.get("/", status_code=status.HTTP_200_OK)
def home():
    return {"status": "HCMatrix Chatbot is up! Endpoints are `/chat` and `/chat-history`."}

@app.post("/chat", status_code=status.HTTP_200_OK, response_model=ChatResponseSchema)
async def chatbot(request_model: AudioChatSchema) -> ChatResponseSchema:

    for _ in range(2):
        try:
            response_id = str(uuid.uuid4())
            audio_response_data = None

            response = chatbot_entry_execution(request_model.user_query, request_model.employee_metadata, llm_4O, gold_adls_conn, chatbot_cache)
            if request_model.audio: # remove this line if you wish to synthesis text from audio and user box
                audio_response_data = await speech_out.synthesize_english_to_filepath(response, response_id)
                if audio_response_data is None:
                    raise HTTPException(status_code=500, details="Error in generation audio response")

            local_ip = "http://48.217.20.68:5000"
            # local_ip = "http://127.0.0.1:5500"

            # Generate output mmetadata
            current_time = time.localtime()
            current_time_str = time.strftime("%Y-%m-%d %H:%M:%S", current_time)

            response_data = {
                "employee_metadata": request_model.employee_metadata.dict(),
                "question": request_model.user_query,
                "answer": response,
                "timestamp": current_time_str,
                "audio": f"{local_ip}/download_audio/?file={audio_response_data}" if request_model.audio else "",
                "request_id": response_id,
                "chat_id": request_model.chat_id
            }

            with CosmosClient(database_name="hcm-chatbot", collection_name="user-chat") as client:
                client.insert_one(copy.deepcopy(response_data))

            return JSONResponse(content=response_data)
            # if audio_response_data: # return streaming audio
            #     return StreamingResponse(io.BytesIO(audio_response_data), media_type="audio/wav", headers=response_data)
            # else: # return metadata alo9ne
            #     return JSONResponse(content=response_data)

        except Exception as reason:
            raise
            raise HTTPException(status_code=500, detail=str(reason))


@app.get("/download_audio/")
async def download_audio_file(file: str):
    if not os.path.exists(file):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(path=file, media_type="audio/mpeg")


@app.get("/chat-history", status_code=status.HTTP_200_OK)
# def fetch_chat_id(request_model: ChatHistory) -> List[ChatResponseSchema]:
def fetch_chat_id(
    chat_id: str = Query(..., description="Chat ID from FE"),
    employee_id: str = Query(..., description="Employee ID to retrieve chat history from"),
    company_id: str = Query(..., description="Employee company Id")
) -> List[ChatResponseSchema]:

    query = {
        "chat_id": chat_id,
        "employee_metadata.id": employee_id,
        "employee_metadata.company_id": company_id
    }

    with CosmosClient(database_name="hcm-chatbot", collection_name="user-chat") as client:
        chat_history_pymongo = client.fetch_many(query)
        chat_history = [history for history in chat_history_pymongo]
        return chat_history
