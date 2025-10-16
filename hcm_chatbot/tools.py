# hcm_chatbot/tools.py

# FIX: Removed unused imports for sql_layer_agent and rag_layer_agent
from langchain.tools import tool
from typing import Dict, Any
from langchain_openai import AzureChatOpenAI
from module.gold_layer import GoldLayerUtilsAsync
from module.cache_service import LRUCache
from api.schema import EmployeeMetadataSchema


# FIX: Added two blank lines for PEP 8 compliance
@tool
async def sql_query_tool(query: str, employee_metadata_dict: Dict[str, Any], llm_4o: AzureChatOpenAI, gold_adls_conn: GoldLayerUtilsAsync, chatbot_cache: LRUCache) -> str:
    """
    Use this tool to answer questions about an employee's personal data, such as salary, manager,
    employment history, finance details, personal information, or role history.
    The input should be the user's direct question.
    """
    from hcm_chatbot.sql_layer import sql_layer_agent  # FIX: Import inside the function to avoid circular dependencies
    
    employee_metadata = EmployeeMetadataSchema(**employee_metadata_dict)
    return await sql_layer_agent(
        employee_metadata.company_id,
        employee_metadata.id,
        query,
        llm_4o,
        gold_adls_conn,
        chatbot_cache,
    )


@tool
async def rag_query_tool(query: str, employee_metadata_dict: Dict[str, Any], llm_4o: AzureChatOpenAI) -> str:
    """
    Use this tool to answer general questions about company policies, such as dress code, leave policies,
    work-from-home policies, or code of conduct.
    The input should be the user's direct question.
    """
    from hcm_chatbot.rag_layer import rag_layer_agent  # FIX: Import inside the function
    
    employee_metadata = EmployeeMetadataSchema(**employee_metadata_dict)
    return await rag_layer_agent(query, llm_4o, company_id=employee_metadata.company_id)
