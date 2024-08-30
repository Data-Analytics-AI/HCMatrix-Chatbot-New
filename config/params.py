
from pinecone import ServerlessSpec
import os

params_config = {
    
    "root_dir": os.getcwd(), #"/home/alijoe/Documents/Snapnet Codebase/snapnet-codebase/snapnet-chatbot-v1",
    "data_dir": os.path.join(os.getcwd(), "temp_data") # "/home/alijoe/Documents/Snapnet Codebase/snapnet-codebase/snapnet-chatbot-v1/temp_data",
}

credentials_config = {
    "speech_service": {
        "key": "69c5af99c15547eaa10f4fef81c17317"
    },
    
    "adls_credentials": {
        "account_name": "transformedhcmatrixadls1", # 'transformedhcmatrixadls',
        "client_id": "7d6b30cb-a0db-4eb8-aa94-1deaec9afd9f", # "9dc4d7f9-1edb-484c-bb91-be1e0673e9fc",
        "client_secret": "URN8Q~WdqtACSyTezgFIKjt8h9qPrT_7qX6Zzdwu", # "qtl8Q~x~tV-aRH~bopRJ.-k7cbLF4Dgsj5bV7aDO",
        "tenant_id": "ba130eca-3030-48e1-9089-c979293aeb70", # "ba130eca-3030-48e1-9089-c979293aeb70",
        "goldlayer_container_name": "goldhcmatrixcontainer",
        "goldlayer_account_name": "goldstoragehcmatrix1",
        "stagging_adls_name": "stagingadlshcmatrix1",
    },

    "mysql_credentials": {
        "staging": {
            "auth_db_name": "hcm-auth-staging-db",
            "utils_db_name": "hcm-utility-staging-db"
        },
        "production": {

        }
    },

    "pinecone_credentials": {
        'PINECONE_API_KEY': "f934012c-6c0a-43a9-bfe5-1cf413c26bb3",
        "index_name": "xkaggle-rag-project-astra", #"ExternalFiles",
        "index_metric": "cosine",
        "specs": ServerlessSpec(cloud="aws", region="us-east-1"),
        "embedding_dim": 3072
    },

    "azure_oai_credentials": {
        "AZURE_OPENAI_API_KEY": "2cb8db1fbb1b4d0085f7bf1e38b396fa",
        "AZURE_OPENAI_ENDPOINT": "https://hcmatrix-openai.openai.azure.com/",
        "4O_API_VERSION":"2024-02-01", 
        "4O_AZURE_DEPLOYMENT":"hcmatrix-llm-4o", 
        "4O_MODEL_NAME":"gpt-4o", 
        "4O_MODEL_VERSION":"2024-05-13",
        "MODEL_NAME":"gpt3.5-turbo-instruct",
        "API_VERSION":"2023-12-01-preview",
        "AZURE_DEPLOYMENT": "hcmatrix-llm",
        "AZURE_EMBEDDING_DEPLOYMENT": "hcmatrix-embeddings",
        "AZURE_EMBEDDING_API_VERSION": "2023-05-15"
    }

    
}
