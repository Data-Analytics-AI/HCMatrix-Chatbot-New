
from fastapi import FastAPI, HTTPException, status, Form
from rag_engine.pinecone_ import PineconeDB
from rag_engine.emdedder import EmbedChunks
from pathlib import Path
from typing import *
import logging
import uuid
import json
import time
import os

from model.azure_oai import AzureOAI
from rag_engine.retriever_ import Retriever
from api.schema import ChatSchema, ChatResponseSchema
from hcm_chatbot.router import chatbot_entry_execution


### ===================== Initialize model and embeddings ====================
## ===========================================================================

azure_oai_conn = AzureOAI("4O")
llm_4O = azure_oai_conn()

# embedding_query = EmbedChunks().embedding_query
# pineconedb = PineconeDB()

# index = pineconedb.index
# retriever = Retriever(index, embedding_query)



### ===================== Initialize API =================================
## =======================================================================

def save_to_json(json_path: str, data: Dict[str, str]):
    with open(json_path, "a+") as fle:
        fle.write(json.dumps(data))
        fle.write("\n")

app = FastAPI()

print ("Initializing API....")
@app.get("/", status_code=status.HTTP_200_OK)
def home():
    return {"status": "HCMatrix Chatbot is up! Endpoints are `/chat` and `/update_db`."}


@app.post("/chat", status_code=status.HTTP_200_OK)
def chatbot(request_model: ChatSchema) -> ChatResponseSchema:
    for _ in range(2):
        try:

            response = chatbot_entry_execution(request_model.user_query, request_model.employee_metadata, llm_4O)
            current_time = time.localtime()
            current_time_str = time.strftime("%Y-%m-%d %H:%M:%S", current_time)

            data = {
                "employee_metadata": request_model.employee_metadata.dict(),
                "question": request_model.user_query,
                "answer": response, 
                "timestamp": current_time_str,
                "request_id": str(uuid.uuid4())
            }
            save_to_json(os.path.join(os.getcwd(), "query_data.json"), data)
            return ChatResponseSchema(**data)
        except Exception as reason:
            raise HTTPException(status_code=500, detail=str(reason))

## @app.post("/update_database")
