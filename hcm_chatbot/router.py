from module.cache_service import LRUCache
from langchain_openai import AzureChatOpenAI
from api.schema import EmployeeMetadataSchema
from module.gold_layer import GoldLayerUtilsAsync
from hcm_chatbot.sql_layer import sql_layer_agent
from hcm_chatbot.rag_layer import rag_layer_agent
from module.utils import timing_decorator
from module.query_classifier import classify_query


@timing_decorator
@classify_query
async def chatbot_entry_execution(
        user_query: str,
        employee_metadata: EmployeeMetadataSchema,
        llm_4o: AzureChatOpenAI,
        gold_adls_conn: GoldLayerUtilsAsync,
        chatbot_cache: LRUCache,
        layer: str
) -> str:
    """
    this functions routes the user query to a layered route:
    the first route is the db, then external files, then chatgpt.

    Args: user query and employee_metadata structure can be found in API schema class
    """
    print(f"User question: {user_query}")

    if layer == 'SQL':
        sql_agent_response = await sql_layer_agent(
            employee_metadata.company_id,
            employee_metadata.id,
            user_query,
            llm_4o,
            gold_adls_conn,
            chatbot_cache,
        )
        return sql_agent_response.strip()

    # Instead, it should use the rag layer
    answer = await rag_layer_agent(
            user_query, llm_4o, company_id=employee_metadata.company_id
        )
    return answer
