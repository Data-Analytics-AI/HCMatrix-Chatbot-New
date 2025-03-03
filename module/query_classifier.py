from langchain_openai import AzureChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from module.utils import config
import os
import json
from functools import wraps

azure_oai_credentials = config['production']['azure_oai_credentials']

os.environ["AZURE_OPENAI_API_KEY"] = azure_oai_credentials['AZURE_OPENAI_API_KEY']
os.environ["AZURE_OPENAI_ENDPOINT"] = azure_oai_credentials['AZURE_OPENAI_ENDPOINT']

model = AzureChatOpenAI(
    api_version=azure_oai_credentials["4O_API_VERSION"],
    azure_deployment=azure_oai_credentials["4O_AZURE_DEPLOYMENT"],
    model=azure_oai_credentials["4O_MODEL_NAME"],
    model_version=azure_oai_credentials["4O_MODEL_VERSION"],
    model_kwargs={"response_format": {"type": "json_object"}},
)

system_prompt = SystemMessage(
    content="""You are an AI assistant that classifies user queries into one of two categories: - "SQL": If 
            the query is related to user metadata, such as salary, manager, employment history, finance details, 
            personal information, or role history. - "RAG": If the query is related to company policies, 
            such as dress code, leave policies, work-from-home policies, or code of conduct.

        SQL Layer includes the following tables and their relevant data: - employees_education_details (school, 
        degree, specialization, startDate, endDate) - employees_emergency_contacts (fullName, relationship, 
        phoneNumber, address) - employees_employment_history (organization, position, startDate, endDate) - 
        employees_finance_details (bank, account details) - employees_job_information (jobContractType, workModel, 
        hireDate, probationEndDate, lineManagerId, payroll details, workDaysPerWeek) - employees_manager_history (
        lineManagerId, currentManager) - employees_personal_information (dob, gender, nationality, maritalStatus, 
        phoneNumber, address, NIN, stateOfOrigin) - employees_role_history (roleId, from, 
        to) - employees_salary_history (salary type, frequency, monthlySalaryGross, salaryHourlyRate, from, to)

        RAG Layer is used for company policies and guidelines such as:
        - Dress code
        - Work-from-home policies
        - Code of conduct
        - Leave policies
        - Other HR or company policy-related queries

        Respond strictly in JSON format: {"category": "SQL" or "RAG"}
        """)


def classify_query(func):
    """Classify the user query as either 'SQL' or 'RAG'."""

    @wraps(func)
    async def wrapper(user_query, *args, **kwargs):
        user_prompt = HumanMessage(content=user_query)
        response = await model.ainvoke([system_prompt, user_prompt])
        query_class = json.loads(response.content)['category']
        print(f"User question classified as a {query_class} "
              f"query and is being routed to the {query_class} layer")
        return await func(user_query, *args, layer=query_class, **kwargs)

    return wrapper
