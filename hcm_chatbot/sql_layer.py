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

# The improved prompt template with schema descriptions, relationships, and examples.
SQL_PROMPT_TEMPLATE = """You are an AI assistant for HCMatrix, designed to answer employee questions by querying a SQLite database.
Given an input question, you must first create a syntactically correct SQLite query, then execute it, and finally return the answer in a natural, friendly tone.
You are currently assisting employee with ID: {employee_id}. Frame all queries for this specific employee.

**IMPORTANT RULES:**
1.  **NEVER** query all columns from a table. Only select the specific columns needed to answer the question.
2.  Pay attention to which table contains the information you need.
3.  Do not make up information. If the answer is not in the database, say "I'm sorry, I couldn't find that information in your records."
4.  Do not expose table or column names in your final answer. Just give the answer.

**DATABASE SCHEMA AND RELATIONSHIPS:**

Here is the schema of the tables you can query:
{table_info}

**KEY RELATIONSHIPS TO REMEMBER:**

-   To find an employee's **Line Manager's Name**:
    1.  Find the `lineManagerId` from the `employees_job_information` table using the employee's `employeeId`.
    2.  Use that `lineManagerId` to look up the manager's details in the `employees` table where the `employeeId` matches the `lineManagerId`.

-   To find an employee's **Current Salary**:
    1.  Query the `employees_salary_history` table for the `employeeId`.
    2.  The current salary is the record where the `to` column is NULL.

**EXAMPLE QUERIES:**

---
Question: What is my line manager's name?
SQLQuery: SELECT T2."firstName", T2."lastName" FROM employees_job_information AS T1 INNER JOIN employees AS T2 ON T1."lineManagerId" = T2."employeeId" WHERE T1."employeeId" = {employee_id}
---
Question: When did I start this job?
SQLQuery: SELECT "startDate" FROM employees_job_information WHERE "employeeId" = {employee_id}
---
Question: How much do I earn per month?
SQLQuery: SELECT "monthlyGross" FROM employees_salary_history WHERE "employeeId" = {employee_id} AND "to" IS NULL
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

    This function retrieves employee-specific SQL data from Azure Data Lake Storage (ADLS)
    and caches it for efficient querying. If a cached SQL toolkit exists, it is used;
    otherwise, the function fetches the SQL database from ADLS, initializes an SQL agent,
    and executes the query using an AI-powered agent.

    Args:
        company_id (str): Unique identifier of the company.
        employee_id (str): Unique identifier of the employee.
        query (str): The SQL-related user query.
        llm_4O (AzureChatOpenAI): The AI model used for processing the SQL query.
        gold_adls_conn (GoldLayerUtilsAsync): Utility for accessing structured data in ADLS.
        chatbot_cache (LRUCache): Cache for storing and retrieving preloaded SQL toolkits.

    Returns:
        str: The AI-generated response based on the SQL database query.
    """
    start_time = time.time()
    company_data_dir = os.path.join(data_dir, f"cp_{company_id}")
    company_sql_dir = os.path.join(company_data_dir, f"cp_{company_id}_sql")
    employee_sql_db_path_adls = os.path.join(company_sql_dir, f"emp_{employee_id}_sql_db.db")

    cache_key = f"{company_id}_{employee_id}"
    toolkit = chatbot_cache.get(cache_key)

    if toolkit == -1:
        print('No cache available or cache expired. Pulling from ADLS...')
        adls_start = time.time()
        # Ensure the file is downloaded and we get a local path
        local_db_path = await gold_adls_conn.read_file_from_adls(employee_sql_db_path_adls)
        adls_end = time.time()
        print(f"⏳ ADLS Fetch Time: {adls_end - adls_start:.2f} sec")

        db_start = time.time()
        employee_db = await asyncio.to_thread(SQLDatabase.from_uri, f"sqlite:///{local_db_path}")
        print(f"Usable tables: {employee_db.get_usable_table_names()}")
        db_end = time.time()
        print(f"⏳ SQLite Init Time: {db_end - db_start:.2f} sec")

        toolkit = SQLDatabaseToolkit(db=employee_db, llm=llm_4O)
        chatbot_cache.put(cache_key, toolkit)  # Cache the newly created toolkit

    # Create a dynamic prompt with employee_id and table info
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
        verbose=False,  # Set to True for debugging if needed
        max_execution_time=30,
        handle_parsing_errors=True,  # More robust against minor SQL syntax errors from the LLM
        prompt=prompt  # Use the new detailed prompt
    )
    agent_end = time.time()
    print(f"⏳ SQL Agent Init Time: {agent_end - agent_start:.2f} sec")

    query_start = time.time()
    # Invoke the agent with the user query. The key "input" matches the {input} in the prompt template.
    agent_response = await asyncio.to_thread(
        agent_executor.invoke, {"input": query}
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
        return ("Sorry, I couldn't get the best response to your query. "
                "Kindly reach out to your HR department for the best response to your query or retry.")

    return response
