import string
from services.cache_service import LRUCache
from langchain_openai import AzureChatOpenAI
from api.schema import EmployeeMetadataSchema
from data_preprocessing.gold_layer import GoldLayerUtils
from hcm_chatbot.sql_chatbot import execute as sql_chatbot_execute
from hcm_chatbot.layer_1_chatbot import layer_one_agent
from module.utils import timing_decorator


def looks_like(main_txt, ref_text: str) -> bool:
    cln_ref_txt = ref_text.strip().casefold()
    cln_main_txt = (
        main_txt.strip().casefold().translate(str.maketrans("", "", string.punctuation))
    )
    return cln_main_txt == cln_ref_txt


def route_user_query(
    layer_one_answer: str, layer_one_query: str, llm_4o: AzureChatOpenAI
) -> str:
    if looks_like(layer_one_answer, "Invalid Query"):
        return "Query Database Further"
    else:
        return "Return Answer to User"


@timing_decorator
async def chatbot_entry_execution(
    user_query: str,
    employee_metadata: EmployeeMetadataSchema,
    llm_4o: AzureChatOpenAI,
    gold_adls_conn: GoldLayerUtils,
    chatbot_cache: LRUCache,
) -> str:
    """
    this functions routes the user query to a layered route:
    the first route is the db, then external files, then chatgpt.

    Args: user query and employee_metadata structure can be found in API schema class
    """
    print(f"User question: {user_query}")
    print("Attempting to get response from the SQL layer.")
    sql_agent_response = sql_chatbot_execute(
        employee_metadata.company_id,
        employee_metadata.id,
        user_query,
        llm_4o,
        gold_adls_conn,
        chatbot_cache,
    ).strip()
    # .strip() is added to improve consistency for response
    fallback_response = ("Sorry, couldn't get the best response to your query. Kindly reach out to your HR department "
                         "for the best response to your query or retry.")
    if sql_agent_response == fallback_response:
        print("Could not respond to question. Using the SQL layer.")
        print("Generating response from the RAG layer.")
        answer = await layer_one_agent(
            user_query, llm_4o, company_id=employee_metadata.company_id
        )
        return answer

    print("SQL layer sufficient to generate response.")
    return sql_agent_response
