from langchain_openai import AzureChatOpenAI
from api.schema import EmployeeMetadataSchema
from module.gold_layer import GoldLayerUtilsAsync
from module.cache_service import LRUCache

# Import the classifier and the layer-specific agents
from hcm_chatbot.query_classifier import classify_query
from hcm_chatbot.sql_layer import sql_layer_agent
from hcm_chatbot.rag_layer import rag_layer_agent


@classify_query
async def chatbot_entry_execution(
        user_query: str,
        employee_metadata: EmployeeMetadataSchema,
        llm_4o: AzureChatOpenAI,
        gold_adls_conn: GoldLayerUtilsAsync,
        chatbot_cache: LRUCache,
        layer: str  # This argument is provided by the @classify_query decorator
) -> str:
    """
    Routes the user query to the appropriate processing layer (SQL or RAG)
    based on the classification from the decorator.
    """
    print(f"User question: '{user_query}' -> Routing to {layer} layer.")

    if layer == 'SQL':
        response = await sql_layer_agent(
            company_id=employee_metadata.company_id,
            employee_id=employee_metadata.id,
            query=user_query,
            llm_4O=llm_4o,
            gold_adls_conn=gold_adls_conn,
            chatbot_cache=chatbot_cache,
        )
        return response.strip()

    # If not 'SQL', default to the RAG layer
    response = await rag_layer_agent(
        user_query,
        llm_4o,
        company_id=employee_metadata.company_id
    )
    return response
