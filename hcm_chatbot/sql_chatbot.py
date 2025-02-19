import os
from services.cache_service import LRUCache
from langchain_openai import AzureChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain.prompts.chat import ChatPromptTemplate
from data_preprocessing.gold_layer import GoldLayerUtils
from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
import time

data_dir = "temp_data/"


def execute(
        company_id: str, employee_id: str, query: str,
        llm_4O: AzureChatOpenAI, gold_adls_conn: GoldLayerUtils,
        chatbot_cache: LRUCache):
    start_time = time.time()
    company_data_dir = os.path.join(data_dir, f"cp_{company_id}")
    print(company_data_dir)

    company_sql_dir = os.path.join(company_data_dir, f"cp_{company_id}_sql")
    employee_sql_db = os.path.join(company_sql_dir, f"emp_{employee_id}_sql_db.db")

    # Minimalistic cache implementation
    cache_key = f"{company_id}_{employee_id}"
    cache_data = chatbot_cache.get(cache_key)

    if cache_data == -1:

        print('No cache available or cache expired. Pulling from ADLS...')
        adls_start = time.time()

        sql_db = gold_adls_conn.read_file_from_adls(employee_sql_db)

        adls_end = time.time()
        print(f"⏳ ADLS Fetch Time: {adls_end - adls_start:.2f} sec")

        db_start = time.time()
        employee_db = SQLDatabase.from_uri(f"sqlite:///{sql_db}")
        print(employee_db.get_usable_table_names())
        db_end = time.time()
        print(f"⏳ SQLite Init Time: {db_end - db_start:.2f} sec")

        toolkit = SQLDatabaseToolkit(db=employee_db, llm=llm_4O)
        chatbot_cache.put(cache_key, toolkit)  # Cache the toolkit

        cache_data = chatbot_cache.get(cache_key)  # Re-fetch after putting

    agent_start = time.time()
    agent_executor = create_sql_agent(
        llm_4O, toolkit=cache_data,
        agent_type='openai-tools',
        verbose=False,
        max_execution_time=30,
        handle_parsing_errors=False)
    agent_end = time.time()
    print(f"⏳ SQL Agent Init Time: {agent_end - agent_start:.2f} sec")

    query_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are an AI assistant developed by Snapnet for various organization use, you're capable of "
                       "giving responses to any questions related to an organization within HCMatrix. These "
                       "questions range from HR policy, leave policies, workflows, etc., and individual employee "
                       "data. Don't talk about the structure of the database or how you arrived at your answer. \n"
                       "Here are the tables in the database: employees_education_details, "
                       "employees_emergency_contacts, employees_employment_history, employees_finance_details, "
                       "employees_job_information, employees_manager_history, employees_personal_information, "
                       "employees_role_history, employees_salary_history. \n"
                       "Dont query the tables again since you have it already. \n"
                       "If you cannot help the user, respond with this exact phrase: \n"
                       "Sorry, couldn't get the best response to your query. Kindly reach out to your HR department "
                       "for the best response to your query or retry. \n"
                       "You're currently conversing with employee id `{employee_id}`"),
            ("user", "{user_query}.")
        ]
    )
    query_start = time.time()
    agent_response = agent_executor.invoke(
        query_prompt.format(employee_id=employee_id, user_query=query)
    )
    query_end = time.time()
    print(f"⏳ Query Execution Time: {query_end - query_start:.2f} sec")

    response = agent_response['output']
    total_time = time.time() - start_time
    print(f"🚀 Total Execution Time: {total_time:.2f} sec")

    wrong_response_list = [
        "Agent stopped due to iteration limit or time limit.",
        "Agent stopped due to max iterations."
    ]

    if response in wrong_response_list:
        return ("Sorry, couldn't get the best response to your query. Kindly reach out to your HR department for the "
                "best response to your query or retry.")
    return response
