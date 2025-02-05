import string
from typing import *
from services.cache_service import LRUCache
from langchain_openai import AzureChatOpenAI
from api.schema import EmployeeMetadataSchema
from data_preprocessing.gold_layer import GoldLayerUtils
from hcm_chatbot.rag_chatbot import execute as chatbot_execute
from hcm_chatbot.sql_chatbot import execute as sql_chatbot_execute
from hcm_chatbot.layer_1_chatbot import layer_one_agent, layer_one_validator
from module.log_config import logger


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
    logger.info(f"User question: {user_query}")
    logger.info("Attempting to get response from the SQL layer.")
    sql_aqent_response = sql_chatbot_execute(
        employee_metadata.company_id,
        employee_metadata.id,
        user_query,
        llm_4o,
        gold_adls_conn,
        chatbot_cache,
    ).strip()
    # .strip() is added to improve consistency for response

    if sql_aqent_response == (
        "Sorry, couldn't get the best response to your query, kindly reach out to your HR "
        "department for the best response to your query or retry."
    ):
        logger.debug(f"Could not respond to question. Using the SQL layer.")
        logger.info("Generating response from the RAG layer.")
        answer = layer_one_agent(
            user_query, llm_4o, company_id=employee_metadata.company_id
        )
        logger.info(f"Response: \n {answer}")
        return answer

    logger.info("SQL layer sufficient to generate response.")
    return sql_aqent_response
