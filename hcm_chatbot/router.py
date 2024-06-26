
import string
from typing import *
from langchain_openai import AzureChatOpenAI
from hcm_chatbot.rag_chatbot import execute as chatbot_execute
from hcm_chatbot.sql_chatbot import execute as sql_chatbot_execute
from hcm_chatbot.layer_1_chatbot import layer_one_agent, layer_one_validator


def looks_like(main_txt, ref_text: str) -> bool:
    cln_ref_txt = ref_text.strip().casefold()
    cln_main_txt = main_txt.strip().casefold().translate(str.maketrans('', '', string.punctuation))
    return cln_main_txt == cln_ref_txt


def route_user_query(layer_one_answer:str, layer_one_query: str, llm_4o: AzureChatOpenAI)-> str:

    # answer = layer_one_validator(layer_one_query, layer_one_answer, llm_4o)
   
    if looks_like(layer_one_answer, "Invalid Query"):
        return "Query Database Further"
    else:
        return "Return Answer to User"
    # else:
    #     if (answer == "Good") or (looks_like(answer, "Good")):
    #         return "Return Answer to User"
    #     elif (answer == "No Good") or (looks_like(answer, "No Good")):
    #         return "Query Database Further"


#    "employee_metadata": {
#         "departement_id": 43,
#         "role_id": "323",
#         "group_id": "54",
#         "company_id": "53",
#         "id": "373"
#     }

def chatbot_entry_execution(user_query: str, employee_metadata: Dict[str, Any], llm_4o: AzureChatOpenAI) -> str:

    layer_one_answer = layer_one_agent(user_query, llm_4o)
    route = route_user_query(layer_one_answer, user_query, llm_4o)

    if route == "Query Database Further":
        sql_aqent_response = sql_chatbot_execute(
            employee_metadata["company_id"],
            employee_metadata["id"],
            user_query, llm_4o)
        print ("Dodo")
        print (sql_aqent_response)
        
        # if sql_aqent_response == "Sorry, couldn't get the best response to your query, kindly reach out to your HR department for the best response to your query.":
        #     rag_agent_response = chatbot_execute(
        #         user_query, employee_metadata.departement_id,
        #         employee_metadata.role_id,
        #         employee_metadata.group_id)
            
        #     return rag_agent_response['answer']
            
        return sql_aqent_response
    
    elif route == "Return Answer to User":
        return layer_one_answer
