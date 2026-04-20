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
    Routes the user query to the appropriate processing layer based on classification.

    This function relies on the `classify_query` decorator to first categorize the user
    query as either SQL-related or RAG-related. If classified as SQL-related, the query
    is handled by the SQL agent. Otherwise, it is processed using the retrieval-augmented
    generation (RAG) layer.

    Args:
        user_query (str): The input query from the user.
        employee_metadata (EmployeeMetadataSchema): Employee details containing company ID, user ID, etc.
        llm_4o (AzureChatOpenAI): The language model used for query processing.
        gold_adls_conn (GoldLayerUtilsAsync): Connection utility for accessing structured data storage.
        chatbot_cache (LRUCache): Cache for user specific data.
        layer (str): The processing layer determined by classification ('SQL' or 'RAG').

    Returns:
        str: The final response generated from the selected processing layer.
    """
    print(f"User question: {user_query}")

    # Known failure responses from the SQL layer
    sql_failure_phrases = [
        "sorry, couldn't get the best response",
        "agent stopped due to iteration limit or time limit",
        "agent stopped due to max iterations",
    ]

    if layer == 'SQL':
        try:
            sql_agent_response = await sql_layer_agent(
                employee_metadata.company_id,
                employee_metadata.id,
                user_query,
                llm_4o,
                gold_adls_conn,
                chatbot_cache,
            )
            response = sql_agent_response.strip()

            # Check if the SQL response is empty or a known failure
            has_error_phrase = any(
                phrase in response.lower() for phrase in sql_failure_phrases
            )
            is_failed = not response or has_error_phrase

            if not is_failed:
                return response

            print("⚠️ SQL layer returned an unsatisfactory response. Falling back to RAG layer...")

        except Exception as e:
            print(f"⚠️ SQL layer encountered an error: {e}. Falling back to RAG layer...")

        # Fallback to RAG layer
        answer = await rag_layer_agent(user_query, llm_4o, company_id=employee_metadata.company_id)
        return answer

    # Instead, it should use the RAG layer
    answer = await rag_layer_agent(user_query, llm_4o, company_id=employee_metadata.company_id)
    return answer
