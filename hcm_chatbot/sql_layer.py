# hcm_chatbot/sql_layer.py

import os
import time
import asyncio
from module.cache_service import LRUCache
from langchain_openai import AzureChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain.prompts import PromptTemplate
from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from module.gold_layer import GoldLayerUtilsAsync

data_dir = "temp_data/"

# --- CORRECTED PROMPT TEMPLATE ---
# This prompt now accurately reflects the schema from your screenshot.
SQL_PROMPT_TEMPLATE = """You are an AI assistant for HCMatrix, designed to answer employee questions by querying a SQLite database.
Given an input question, you must first create a syntactically correct SQLite query, then execute it, and finally return
the answer in a natural, friendly tone.
You are currently assisting employee with ID: {employee_id}. Frame all queries for this specific employee.

**IMPORTANT RULES:**
1.  **NEVER** query all columns from a table. Only select the specific columns needed.
2.  If the answer is not in the database, say "I'm sorry, I couldn't find that information in your records."
3.  Do not expose table or column names in your final answer. Just give the answer.

**DATABASE SCHEMA AND RELATIONSHIPS:**
{table_info}

**KEY RELATIONSHIPS TO REMEMBER:**

-   To find an employee's **own name**:
    1.  Query the `employees_personal_information` table.
    2.  Use the `firstName` and `lastName` columns where the `employeeId` matches {employee_id}.

-   To find an employee's **Line Manager's Name**:
    1.  First, get the `lineManagerId` from the `employees_job_information` table for the current `employeeId`.
    2.  Then, use that `lineManagerId` to find the manager in the `employees_manager` table by matching it to the `employeeId` column.
    3.  The manager's name is in the `mgr_firstName` and `mgr_lastName` columns of the `employees_manager` table.

**EXAMPLE QUERIES:**

---
Question: What is my name?
SQLQuery: SELECT "firstName", "lastName" FROM employees_personal_information WHERE "employeeId" = {employee_id}
---
Question: What is my line manager's name?
SQLQuery: SELECT T2."mgr_firstName", T2."mgr_lastName" FROM employees_job_information AS T1 INNER JOIN employees_manager AS T2 ON T1."lineManagerId" = T2."employeeId" WHERE T1."employeeId" = {employee_id}
---

**User Question:**
{input}
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

    # --- LOGGING FIX ---
    # This will now print the table names on every single run, whether from cache or new.
    print(f"Usable tables: {toolkit.db.get_usable_table_names()}")
    
    prompt = PromptTemplate.from_template(
        template=SQL_PROMPT_TEMPLATE,
        partial_variables={
            "table_info": toolkit.db.get_table_info(),
            "employee_id": employee_id
        }
    )

    agent_start = time.time()
    agent_executor = create_sql_agent(
        llm=llm_4O,
        toolkit=toolkit,
        agent_type='openai-tools',
        verbose=True,  # Set to True to see the agent's thought process for debugging
        max_execution_time=30,
        handle_parsing_errors=True,
        prompt=prompt
    )
    agent_end = time.time()
    print(f"⏳ SQL Agent Init Time: {agent_end - agent_start:.2f} sec")

    query_start = time.time()
    try:
        agent_response = await asyncio.to_thread(
            agent_executor.invoke, {"input": query}
        )
        response = agent_response['output']
    except Exception as e:
        print(f"ERROR during agent execution: {e}")
        response = ("Sorry, I encountered an error while processing your request. "
                    "Please try rephrasing or contact your HR department.")

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
        return (
            "Sorry, I couldn't get the best response to your query. "
            "Kindly reach out to your HR department for the best response "
            "to your query or retry."
        )

    return response
