
import os
from typing import *
from langchain_openai import AzureChatOpenAI, AzureOpenAI, AzureOpenAIEmbeddings
from config.params import credentials_config

azure_oai_credentials = credentials_config['azure_oai_credentials']

os.environ["AZURE_OPENAI_API_KEY"]  = azure_oai_credentials['AZURE_OPENAI_API_KEY']
os.environ["AZURE_OPENAI_ENDPOINT"] = azure_oai_credentials['AZURE_OPENAI_ENDPOINT']

class AzureOAI:

    def __init__(self, model_type: str, ) -> None:
        assert model_type in ["3.5", "4O"], "model_type must be '3.5' or '4O'"
        self.model_type = model_type
        # self.embedding = self._initialize_embedding()

    def __call__(self) -> Any:
        
        if self.model_type == "4O":
            # The implementation below is for chat models
            llm_4o = AzureChatOpenAI( 
                # azure_endpoint    =azure_oai_credentials[""],
                # api_key           =azure_oai_credentials[""],
                api_version         =azure_oai_credentials["4O_API_VERSION"],
                azure_deployment    =azure_oai_credentials["4O_AZURE_DEPLOYMENT"],
                model               =azure_oai_credentials["4O_MODEL_NAME"],
                model_version       =azure_oai_credentials["4O_MODEL_VERSION"],
                streaming=True
            )
            
            return llm_4o

        elif self.model_type == "3.5":
            # The implementation below is for instruct models
            llm = AzureOpenAI(
                model_name       =azure_oai_credentials["MODEL_NAME"],
                api_version      =azure_oai_credentials["API_VERSION"],
                azure_deployment =azure_oai_credentials["AZURE_DEPLOYMENT"],
                temperature      =1,
                streaming=True
            )

            return llm
    
    def _initialize_embedding(self):
        embedding = AzureOpenAIEmbeddings(
            azure_deployment   = azure_oai_credentials["azure_oai_credentials"]["AZURE_EMBEDDING_DEPLOYMENT"],
            openai_api_version = azure_oai_credentials["azure_oai_credentials"]["AZURE_EMBEDDING_API_VERSION"]
        )
        return embedding

    def get_embedding(self):
        return self.embedding
