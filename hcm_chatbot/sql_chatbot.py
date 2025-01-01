import os
from services.cache_service import LRUCache
from langchain_openai import AzureChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain.prompts.chat import ChatPromptTemplate
from data_preprocessing.gold_layer import GoldLayerUtils
from langchain_community.agent_toolkits import create_sql_agent
from langchain.agents.agent_toolkits.sql.toolkit import SQLDatabaseToolkit

data_dir = "temp_data/"


def execute(
        company_id: str, employee_id: str, query: str,
        llm_4O: AzureChatOpenAI, gold_adls_conn: GoldLayerUtils,
        chatbot_cache: LRUCache):
    company_data_dir = os.path.join(data_dir, f"cp_{company_id}")
    print(company_data_dir)

    company_sql_dir = os.path.join(company_data_dir, f"cp_{company_id}_sql")
    employee_sql_db = os.path.join(company_sql_dir, f"emp_{employee_id}_sql_db.db")

    # Minimalistic cache implementation
    cache_key = f"{company_id}_{employee_id}"
    cache_data = chatbot_cache.get(cache_key)
    if cache_data == -1:
        sql_db = gold_adls_conn.read_file_from_adls(employee_sql_db)
        employee_db = SQLDatabase.from_uri(f"sqlite:///{sql_db}")

        toolkit = SQLDatabaseToolkit(db=employee_db, llm=llm_4O)
        chatbot_cache.put(cache_key, toolkit)  # cache individual toolkit
        cache_data = chatbot_cache.get(cache_key)
        # toolkit.get_tools()

    agent_executor = create_sql_agent(
        llm_4O, toolkit=cache_data,
        agent_type='openai-tools',
        verbose=False,
        max_execution_time=30,
        handle_parsing_errors=False)

    query_promt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are an AI assistant developed by Snapnet for various organization use, you're capable of "
                       "giving response to any questions related to an organization within HCMatrix. These "
                       "questions ranges from HR policy, leave policies, workflows, etc and individual employee "
                       "data. Don't talk about the structure of the database or how you arrived at your answer. \n"
                       "if you can help the user, response with this exact words: \n Sorry, couldn't get the best "
                       "response to your query, kindly reach out to your HR department for the best response to your "
                       "query or retry. \n"
                       "You're currently conversing with employee id `{employee_id}`"),
            ("user", "{user_query}.")
        ]
    )

    agent_response = agent_executor.invoke(
        query_promt.format(employee_id=employee_id, user_query=query)
    )
    response = agent_response['output']

    # Note, this chatbot is currently experimental and might return incorrect queries from time to time.
    # Should that be the case, kindly retry or meet with your organization human resource manager.
    wrong_response_list = [
        "Agent stopped due to iteration limit or time limit.",
        "Agent stopped due to max iterations."
    ]

    if response in wrong_response_list:
        return ("Sorry, couldn't get the best response to your query, kindly reach out to your HR department for the "
                "best response to your query or retry.")
    return response
    # return response["output"]


if __name__ == "__main__":
    company_id = "53"
    employee_id = 372  # 373
    # query = 'What is the maximum number of dependents I can register within my HMO Plan?'
    query = 'When is my work anniversary?'

    print(execute(company_id, employee_id, query))
