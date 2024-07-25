
from fastapi import FastAPI, HTTPException, status, File, Form, UploadFile, Depends
import azure.cognitiveservices.speech as speechsdk
from fastapi.responses import FileResponse
#from rag_engine.pinecone_ import PineconeDB
#from rag_engine.emdedder import EmbedChunks
from pathlib import Path
from typing import *
import aiofiles
import uuid
import json
import time
import os
import io

from speech_impl import spk
from model.azure_oai import AzureOAI
# from rag_engine.retriever_ import Retriever
from hcm_chatbot.router import chatbot_entry_execution
from api.schema import AudioChatSchema, EmployeeMetadataSchema, ChatResponseSchema, ChatSchema
from fastapi.responses import StreamingResponse, JSONResponse

### ===================== Initialize model and embeddings ====================
## ===========================================================================

azure_oai_conn = AzureOAI("4O")
llm_4O = azure_oai_conn()

speech_out = spk.HCMSpeechOut()
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

async def save_audio(file: UploadFile, filename: str):
    async with aiofiles.open(filename, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)


app = FastAPI()

print ("Initializing API....")
@app.get("/", status_code=status.HTTP_200_OK)
def home():
    return {"status": "HCMatrix Chatbot is up! Endpoints are `/chat` and `/update_db`."}

@app.post("/chat", status_code=status.HTTP_200_OK, response_model=ChatResponseSchema)
async def chatbot(request_model: AudioChatSchema) -> ChatResponseSchema:
# async def chatbot(
#     request_model: ChatSchema = Depends(),
#     audio: UploadFile | None = None
# ) -> ChatResponseSchema:

# @app.post("/chat", status_code=status.HTTP_200_OK, response_model=ChatResponseSchema)
# async def chatbot(
#     user_query: str = Form(None),
#     department_id: str = Form(...),
#     role_id: str = Form(...),
#     group_id: str = Form(...),
#     company_id: str = Form(...),
#     id: str = Form(...),
#     audio: UploadFile = File(None)
# ) -> ChatResponseSchema:
    
    # employee_metadata = EmployeeMetadataSchema(
    #     department_id=department_id,
    #     role_id=role_id,
    #     group_id=group_id,
    #     company_id=company_id,
    #     id=id)

    for _ in range(2):
        try:
            response_id = str(uuid.uuid4())
            audio_response_data = None
            # if request_model.audio:
                
            #     filename = f"temp_{audio.filename}"
            #     await save_audio(audio, filename)

            #     user_query = await speech_out.recognize_from_filepath(filename)
            #     os.remove(filename)
            #     if user_query == "ERRPR":
            #         return {"detail": "No Speech detected!"}

            # response = "Hello there"
            response = chatbot_entry_execution(request_model.user_query, request_model.employee_metadata, llm_4O)
            if request_model.audio: # remove this line if you wish to synthesis text from audio and user box
                audio_response_data = await speech_out.synthesize_english_to_filepath(response, response_id)
                if audio_response_data is None:
                    raise HTTPException(status_code=500, details="Error in generation audio response")
            
            print("pringer")
            local_ip = "http://127.0.0.1:5000"

            # Generate output mmetadata
            current_time = time.localtime()
            current_time_str = time.strftime("%Y-%m-%d %H:%M:%S", current_time)

            response_data = {
                "employee_metadata": request_model.employee_metadata.dict(),
                "question": request_model.user_query,
                "answer": response, 
                "timestamp": current_time_str,
                "audio": f"{local_ip}/download_audio/?file=response_audio_{response_id}.wav",
                "request_id": response_id
            }

            save_to_json(os.path.join(os.getcwd(), "query_data.json"), response_data)
            return JSONResponse(content=response_data)
            # if audio_response_data: # return streaming audio
            #     return StreamingResponse(io.BytesIO(audio_response_data), media_type="audio/wav", headers=response_data)
            # else: # return metadata alo9ne
            #     return JSONResponse(content=response_data)

        except Exception as reason:
            raise HTTPException(status_code=500, detail=str(reason))


@app.get("/download_audio/")
async def download_audio_file(file: str):
    if not os.path.exists(file):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(path=file, media_type="audio/mpeg")