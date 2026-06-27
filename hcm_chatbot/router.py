from module.cache_service import LRUCache
from langchain_openai import AzureChatOpenAI
from api.schema import EmployeeMetadataSchema
from api.schema import EmployeeMetadataSchema
from hcm_chatbot.sql_layer import sql_layer_agent
from hcm_chatbot.rag_layer import rag_layer_agent
from module.utils import timing_decorator
from module.query_classifier import classify_query
from module.security_guardrail import check_prompt_injection


@timing_decorator
@classify_query
async def chatbot_entry_execution(
        user_query: str,
        employee_metadata: EmployeeMetadataSchema,
        llm_4o: AzureChatOpenAI,
        chatbot_db_uri: str,
        chatbot_db_schemas: list,
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
        chatbot_db_uri (str): Base MySQL connection URI (no trailing database name).
        chatbot_db_schemas (list): List of MySQL schema/database names to search for views.
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
            # 1. Run the Security Guardrail Analyzer
            security_check = await check_prompt_injection(user_query, llm_4o)
            if not security_check.get("is_safe", False):
                reason = security_check.get("reason", "Violates security policy.")
                print(f"🚨 Security Block: {reason}")
                return f"I'm sorry, I cannot process this request. Reason: {reason}"

            # 2. Execute SQL Agent if safe
            sql_agent_response = await sql_layer_agent(
                employee_metadata.company_id,
                employee_metadata.id,
                user_query,
                llm_4o,
                chatbot_db_uri,
                chatbot_db_schemas,
                chatbot_cache,
            )
            response = sql_agent_response.strip()

            # If the response is empty or hit an iteration limit, return a clean message
            has_error_phrase = any(
                phrase in response.lower() for phrase in sql_failure_phrases
            )
            if not response or has_error_phrase:
                return "I'm sorry, I couldn't find that information in your profile."

            return response

        except Exception as e:
            print(f"⚠️ SQL layer encountered an error: {e}")
            return "I'm sorry, I couldn't find that information due to a database error."

    # Instead, it should use the RAG layer
    answer = await rag_layer_agent(user_query, llm_4o, company_id=employee_metadata.company_id)
    return answer
