import os
import time
import asyncio
from module.cache_service import LRUCache
from langchain_openai import AzureChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentExecutor
from langchain_community.agent_toolkits import create_sql_agent, SQLDatabaseToolkit
from langchain_core.callbacks import StdOutCallbackHandler
from module.gold_layer import GoldLayerUtilsAsync

data_dir = "temp_data/"

# This prompt has been proven to work in your local test.
SYSTEM_MESSAGE_TEMPLATE = """You are an expert SQLite AI assistant for HCMatrix. Your goal is to answer employee questions by generating and running SQL queries against their personal database.
You are assisting the employee with ID: {employee_id}.

**IMPORTANT RULES:**
1.  **Always** use the `{employee_id}` in your WHERE clauses to filter for the current user's data.
2.  Only query the columns you absolutely need.
3.  Do not expose table or column names in your final answer. Just give the answer in a friendly, natural tone.
4.  If the answer isn't in the database, say "I'm sorry, I couldn't find that information in your records."

**DATABASE SCHEMA AND RELATIONSHIPS:**
{table_info}

**KEY RELATIONSHIPS TO REMEMBER:**
-   The `employees_personal_information` table contains the **current employee's** own name and personal details.
-   The `employees_job_information` table contains the `lineManagerId` for the current employee.
-   The `employees_manager` table contains the names of **managers**, accessible by joining `employees_job_information.lineManagerId` with `employees_manager.employeeId`.

**EXAMPLE QUERIES:**
---
Question: What is my name?
SQLQuery: SELECT "firstName", "lastName" FROM employees_personal_information WHERE "employeeId" = {employee_id}
---
Question: Who is my line manager?
SQLQuery: SELECT T2."mgr_firstName", T2."mgr_lastName" FROM employees_job_information AS T1 INNER JOIN employees_manager AS T2 ON T1."lineManagerId" = T2."employeeId" WHERE T1."employeeId" = {employee_id}
---
"""


async def sql_layer_agent(
        company_id: str, employee_id: str, query: str,
        llm_4O: AzureChatOpenAI, gold_adls_conn: GoldLayerUtilsAsync,
        chatbot_cache: LRUCache):
    """
    Executes a SQL query for an employee by retrieving or creating an AI-powered SQL agent.
    """
    start_time = time.time()
    company_data_dir = os.path.join(data_dir, f"cp_{company_id}")
    company_sql_dir = os.path.join(company_data_dir, f"cp_{company_id}_sql")
    employee_sql_db_path_adls = os.path.join(
        company_sql_dir, f"emp_{employee_id}_sql_db.db"
    )

    cache_key = f"{company_id}_{employee_id}"
    toolkit = chatbot_cache.get(cache_key)

    if toolkit == -1:
        print('No cache available or cache expired. Pulling from ADLS...')
        adls_start = time.time()
        try:
            local_db_path = await gold_adls_conn.read_file_from_adls(
                employee_sql_db_path_adls
            )
        except Exception as e:
            print(f"FATAL ERROR: Could not download database from ADLS. Error: {e}")
            return "I'm sorry, I was unable to access your data. Please contact support."

        adls_end = time.time()
        print(f"⏳ ADLS Fetch Time: {adls_end - adls_start:.2f} sec")

        db_start = time.time()
        employee_db = await asyncio.to_thread(
            SQLDatabase.from_uri, f"sqlite:///{local_db_path}"
        )
        db_end = time.time()
        print(f"⏳ SQLite Init Time: {db_end - db_start:.2f} sec")

        toolkit = SQLDatabaseToolkit(db=employee_db, llm=llm_4O)
        chatbot_cache.put(cache_key, toolkit)

    print(f"Usable tables: {toolkit.db.get_usable_table_names()}")

    # FIX: Format the system message with the dynamic table info and employee ID
    system_message = SYSTEM_MESSAGE_TEMPLATE.format(
        table_info=toolkit.db.get_table_info(),
        employee_id=employee_id
    )

    # FIX: Use the ChatPromptTemplate structure that the agent expects
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_message),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    agent_start = time.time()
    # FIX: Use the updated create_sql_agent structure which returns a runnable agent
    agent = create_sql_agent(
        llm=llm_4O,
        toolkit=toolkit,
        agent_type='openai-tools',
        prompt=prompt
    )
    
    # FIX: Wrap the agent and tools in the final AgentExecutor
    agent_executor = AgentExecutor(agent=agent, tools=toolkit.get_tools(), verbose=True, handle_parsing_errors=True)
    agent_end = time.time()
    print(f"⏳ SQL Agent Init Time: {agent_end - agent_start:.2f} sec")

    query_start = time.time()
    try:
        handler = StdOutCallbackHandler()
        # FIX: Invoke the agent with the correct input structure, including chat_history
        agent_response = await agent_executor.ainvoke(
            {"input": query, "chat_history": []},
            {"callbacks": [handler]}
        )
        response = agent_response['output']
    except Exception as e:
        print(f"ERROR during agent execution: {e}")
        response = ("Sorry, I encountered an error while processing your request. "
                    "Please try rephrasing or contact your HR department.")

    query_end = time.time()
    print(f"⏳ Query Execution Time: {query_end - query_start:.2f} sec")

    total_time = time.time() - start_time
    print(f"🚀 Total Execution Time: {total_time:.2f} sec")

    return response
