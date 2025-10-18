# hcm_chatbot/tools.py

from langchain.tools import tool
from typing import Dict, Any
from langchain_openai import AzureChatOpenAI
from module.gold_layer import GoldLayerUtilsAsync
from module.cache_service import LRUCache
from api.schema import EmployeeMetadataSchema


# The @tool decorator now only sees 'query' and can easily create a schema for it.
@tool
async def sql_query_tool(query: str) -> str:
    """
    Use this tool to answer questions about an employee's personal data, such as salary, manager,
    employment history, finance details, personal information, or role history.
    The input should be the user's direct question.
    """
    # This function will be called by the agent, but the extra arguments will be
    # pre-filled (bound) in the router.
    # We'll define the function that does the real work separately.
    pass


@tool
async def rag_query_tool(query: str) -> str:
    """
    Use this tool to answer general questions about company policies, such as dress code, leave policies,
    work-from-home policies, or code of conduct.
    The input should be the user's direct question.
    """
    # Same as above, this is just a schema placeholder.
    pass
