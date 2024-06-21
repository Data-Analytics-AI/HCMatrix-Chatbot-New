
from fastapi import FastAPI, HTTPException, status, Form
from rag_engine.pinecone_ import PineconeDB
from rag_engine.emdedder import EmbedChunks
from pathlib import Path
from typing import *
import logging
import os

from api.schema import ChatSchema
from model.azure_oai import AzureOAI
from rag_engine.retriever_ import Retriever
from hcm_chatbot.chatbot import execute as chatbot_execute
from hcm_chatbot.sql_chatbot import execute as sql_chatbot_execute


### ===================== Initialize model and embeddings ====================
## ===========================================================================

azure_oai_conn = AzureOAI("4O")
llm_4O = azure_oai_conn()

embedding_query = EmbedChunks().embedding_query
pineconedb = PineconeDB()

index = pineconedb.index
retriever = Retriever(index, embedding_query)

### ===================== Initialize API =================================
## =======================================================================

# employee_metadata = {
#     "user_departement_id" : 43,
#     "user_role_id" : 323,
#     "user_group_id" : 54,
#     "company_id": "54",
#     "employee_id": 67,
# }

app = FastAPI()

print ("Initializing API....")
@app.get("/", status_code=status.HTTP_200_OK)
def home():
    return {"status": "HCMatrix Chatbot is up! Endpoints are `/chat` and `/update_db`."}


@app.post("/chat", status_code=status.HTTP_200_OK)
def chatbot(request_model: ChatSchema):
# def chatbot(user_query: str, query_type: str, employee_metadata: Dict[str, Any]):
    assert request_model.query_type in ["general", "database"], "query type must be `qeneral` or `database`"

    for _ in range(2):
        try:

            if request_model.query_type == "general":
                response = chatbot_execute(request_model.user_query, request_model.employee_metadata, llm_4O, retriever)
                answer = response['answer']
                return {"answer": answer}
            
            elif request_model.query_type == "database":
                company_id = request_model.employee_metadata['company_id']
                employee_id = request_model.employee_metadata['employee_id']
                response = sql_chatbot_execute(company_id, employee_id, request_model.user_query, llm_4O)
                answer = response['output']
                return {"answer": answer}
        except Exception as reason:
            raise HTTPException(status_code=500, detail=str(reason))

## @app.post("/update_database")
