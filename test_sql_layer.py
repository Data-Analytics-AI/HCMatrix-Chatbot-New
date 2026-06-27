import traceback
import asyncio
from hcm_chatbot.sql_layer import sql_layer_agent
from module.cache_service import LRUCache
from module.azure_oai import AzureOAI
import urllib.parse
from module.utils import config

async def main():
    try:
        llm_4O = AzureOAI('4O')()
        cache = LRUCache(120)
        schemas = ['hcmatrix-payroll-db', 'hcmatrix-time-and-attendance-db', 'hcmatrix-utility-db']
        
        db_creds = config["production"]["chatbot_db_credentials"]
        _encoded_password = urllib.parse.quote_plus(str(db_creds['password']))
        _port = int(db_creds['port'])

        # Base URI — no database specified; the SQL layer will auto-discover views across schemas
        chatbot_db_base_uri = (
            f"mysql+mysqlconnector://{db_creds['user']}:{_encoded_password}"
            f"@{db_creds['host']}:{_port}/"
        )
        print("URI:", chatbot_db_base_uri)
        
        await sql_layer_agent('1', '1221', 'Who is my line manager?', llm_4O, chatbot_db_base_uri, schemas, cache)
    except Exception as e:
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
