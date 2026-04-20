import os
from module.cache_service import LRUCache
from langchain_openai import AzureChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain.prompts.chat import ChatPromptTemplate
from module.gold_layer import GoldLayerUtilsAsync
from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
import time
import asyncio

data_dir = "temp_data/"


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

        Raises:
            Exception: If there is an issue retrieving the SQL database or executing the query.
        """
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

        sql_db = await gold_adls_conn.read_file_from_adls(employee_sql_db)

        adls_end = time.time()
        print(f"⏳ ADLS Fetch Time: {adls_end - adls_start:.2f} sec")

        db_start = time.time()
        employee_db = await asyncio.to_thread(SQLDatabase.from_uri, f"sqlite:///{sql_db}")
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
                       "questions range from HR queries, leave, attendance, loans, payroll, and individual employee "
                       "data. Never talk about the structure of the database, SQL queries, or how you arrived at "
                       "your answer — respond naturally as if you just know the information. \n\n"
                       "DATABASE SCHEMA AND TABLE DESCRIPTIONS:\n"
                       "- companies: company name, details, and organizational information\n"
                       "- employees: core employee records (employee IDs, names, status)\n"
                       "- employees_manager: current manager assignments for each employee\n"
                       "- employees_personal_information: personal details — dob, gender, nationality, "
                       "maritalStatus, phoneNumber, address, NIN, stateOfOrigin, firstName, lastName, email\n"
                       "- employees_job_information: job contract type, work model, hire date, probation end date, "
                       "line manager, payroll details, work days per week\n"
                       "- employees_designation_history: historical record of designation/title changes over time\n"
                       "- employees_role_designation: CURRENT designation/title of employees (e.g. CEO, CTO, "
                       "Manager, Director, VP, Head of Department, etc.)\n"
                       "- employees_employment_history: past employment at other organizations\n"
                       "- employees_role_history: role assignment history with date ranges\n"
                       "- employees_manager_history: historical manager assignments\n"
                       "- employees_skills: employee skills and competencies\n"
                       "- employees_education_details: education records — school, degree, specialization, dates\n"
                       "- employees_emergency_contacts: emergency contact details\n"
                       "- employees_payrolls: payroll records and payment details\n"
                       "- employees_salary_history: salary records — type, frequency, gross, hourly rate, dates\n"
                       "- attendance: daily attendance records\n"
                       "- departments: department names and organizational structure\n"
                       "- leaves: leave requests, balances, and approvals\n"
                       "- leave_types: types of leave available in the organization\n"
                       "- clock-ins: employee clock-in timestamps\n"
                       "- clock-outs: employee clock-out timestamps\n"
                       "- loan_requests: employee loan applications\n"
                       "- loans: active and past employee loans\n"
                       "- holidays: company holidays and calendar\n"
                       "- vehicles: company vehicle inventory\n"
                       "- vehicle_bookings: vehicle reservation records\n"
                       "- health_access_hmo_plans: HMO and health insurance plans\n"
                       "- health_access_hospitals: hospitals in the health access network\n\n"
                       "QUERY GUIDANCE:\n"
                       "- When asked 'who is the [title/designation]' (e.g. CEO, CTO, Manager, Director), "
                       "query the employees_role_designation table to find who holds that designation, "
                       "then join with employees_personal_information to get the person's name.\n"
                       "- When asked about an employee's name, always check employees_personal_information "
                       "for firstName and lastName.\n"
                       "- When asked about reporting structure or 'who reports to whom', use "
                       "employees_manager and employees_personal_information.\n"
                       "- When asked about attendance, clock-in, or clock-out data, use the attendance, "
                       "clock-ins, and clock-outs tables respectively.\n"
                       "- When asked about leave balance or leave requests, use leaves and leave_types.\n"
                       "- When asked about salary or payroll, use employees_salary_history and employees_payrolls.\n"
                       "- When asked about loans, use loans and loan_requests.\n"
                       "- When asked about company details, use the companies table.\n"
                       "- When asked about departments, use the departments table.\n\n"
                       "Do not query for table names or schema — you already have this information above. "
                       "Write your SQL queries directly against the relevant tables.\n\n"
                       "If you cannot help the user, respond with this exact phrase: \n"
                       "Sorry, couldn't get the best response to your query. Kindly reach out to your HR department "
                       "for the best response to your query or retry. \n"
                       "You're currently conversing with employee id `{employee_id}`"),
            ("user", "{user_query}.")
        ]
    )
    query_start = time.time()
    agent_response = await asyncio.to_thread(
        agent_executor.invoke, query_prompt.format(employee_id=employee_id, user_query=query)
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
