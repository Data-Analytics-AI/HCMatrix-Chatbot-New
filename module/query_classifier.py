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
    content="""You are an AI assistant that classifies user queries into one of two categories:

- "SQL": If the query is related to employee data, organizational data, or any factual/transactional information
  that can be looked up in the database. This includes: employee personal details, job titles, designations,
  roles (e.g. CEO, Manager, Director), salary, payroll, managers, reporting structure, employment history,
  education, emergency contacts, skills, attendance, clock-in/clock-out records, leave balances and requests,
  loan requests and loans, departments, holidays, vehicles and vehicle bookings, health/HMO plans, hospitals,
  company information, and any question asking "who is", "who has", "how many", "list all", "show me", etc.

- "RAG": If the query is related to company policies, guidelines, or procedural documentation such as:
  dress code, work-from-home policies, code of conduct, leave policies, HR handbooks, onboarding guides,
  or other company policy-related queries.

SQL Layer includes the following tables and their relevant data:
- companies (company name, details, and organizational info)
- employees (core employee records)
- employees_manager (current manager assignments)
- employees_personal_information (dob, gender, nationality, maritalStatus, phoneNumber, address, NIN, stateOfOrigin)
- employees_job_information (jobContractType, workModel, hireDate, probationEndDate, lineManagerId, payroll details, workDaysPerWeek)
- employees_designation_history (history of designation/title changes — e.g. CEO, CTO, Manager, Director, etc.)
- employees_role_designation (current designation/title of employees — use this to find who holds a specific title like CEO, CFO, VP, etc.)
- employees_employment_history (organization, position, startDate, endDate)
- employees_role_history (roleId, from, to)
- employees_manager_history (lineManagerId, currentManager)
- employees_skills (employee skills and competencies)
- employees_education_details (school, degree, specialization, startDate, endDate)
- employees_emergency_contacts (fullName, relationship, phoneNumber, address)
- employees_payrolls (payroll records and payment details)
- employees_salary_history (salary type, frequency, monthlySalaryGross, salaryHourlyRate, from, to)
- attendance (daily attendance records)
- departments (department names and structure)
- leaves (leave requests and balances)
- leave_types (types of leave available)
- clock-ins (employee clock-in timestamps)
- clock-outs (employee clock-out timestamps)
- loan_requests (employee loan applications)
- loans (active and past employee loans)
- holidays (company holidays and calendar)
- vehicles (company vehicle inventory)
- vehicle_bookings (vehicle reservation records)
- health_access_hmo_plans (HMO/health insurance plans)
- health_access_hospitals (hospitals in the health access network)

IMPORTANT: Any question about a person's title, role, designation, position (e.g. "who is the CEO",
"who is the manager", "who is the director") is an SQL query — it requires looking up the
employees_role_designation or employees_designation_history table.

Respond strictly in JSON format: {"category": "SQL" or "RAG"}
""")


def classify_query(func):
    """Classifies the user query as either 'SQL' or 'RAG'.

    This decorator uses an AI model to analyze the user query and determine
    whether it should be processed using the SQL or RAG (Retrieval-Augmented
    Generation) layer. The classification result is then passed as an argument
    to the decorated function.

    Args:
        func (Callable): The function to be wrapped, which processes the query.

    Returns:
        Callable: The wrapped function that classifies the query and routes it
        accordingly.
    """

    @wraps(func)
    async def wrapper(user_query, *args, **kwargs):
        user_prompt = HumanMessage(content=user_query)
        response = await model.ainvoke([system_prompt, user_prompt])
        query_class = json.loads(response.content)['category']
        print(f"User question classified as a {query_class} "
              f"query and is being routed to the {query_class} layer")
        return await func(user_query, *args, layer=query_class, **kwargs)

    return wrapper
