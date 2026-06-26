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
  education, emergency contacts, attendance, clock-in/clock-out records, leave balances and requests,
  loan requests and loans, assets, vehicles, vehicle bookings, departments, public holidays, health/HMO plans,
  hospitals, company information, and any question asking "who is", "who has", "how many", "list all", "show me", etc.

- "RAG": If the query is related to company policies, guidelines, or procedural documentation such as:
  dress code, work-from-home policies, code of conduct, leave policies, HR handbooks, onboarding guides,
  or other company policy-related queries.

SQL Layer includes the following views and their relevant data:

Employee Profile Data:
- v_employee_profile (basic employee info, job details, reporting lines)
- v_employee_emergency_contacts (next-of-kin and emergency contact info)
- v_employee_education (educational qualifications and academic history)
- v_employee_employment_history (previous work experience before joining)

Leave Information:
- v_employee_leave_summary (comprehensive leave balance summary across all leave types)
- v_employee_leaves (detailed information about each individual leave application)
- holidays (applicable public holidays based on company and country)

Payroll & Compensation:
- v_employee_payslips (payslip summary: gross pay, net pay, deductions per period)
- v_employee_payslip_components (breakdown of each payslip into allowances, deductions, loan components)
- v_employee_pay_structure (configured ongoing salary structure and custom salary components)

HMO / Benefits Information:
- v_employee_hmo_profile (HMO enrollment, plan details, basic medical info)
- v_employee_hmo_dependents (dependents covered under the employee's HMO plan)
- v_employee_hmo_hospitals (network of hospitals under the employee's HMO plan)

Loan & Advance Management:
- v_employee_loan_eligibility (eligibility for various loan types based on employment status and service duration)
- v_employee_loans (all active and completed loan records, balances, repayment schedules)
- v_employee_loan_requests (pending and historical loan applications and guarantor approvals)
- v_employee_loan_repayments (individual loan installment payments and outstanding balances)

Asset / Vehicle Requests:
- v_employee_assets (assigned assets, asset requisitions, and historical assignments)
- v_employee_vehicles (assigned vehicles, active bookings, and vehicle assignment history)

Attendance & Time Tracking:
- v_employee_daily_attendance (daily attendance summary: clock-in/out times, hours worked, late/absence flags)
- v_employee_latest_clock (most recent clock-in and clock-out events for real-time clock state)

Public Employee Directory (global — available to all employees):
- v_public_employee_directory (public-facing directory of non-confidential employee information)
- v_public_departments (all departments, hierarchies, department heads, and total employee headcount)

IMPORTANT: Any question about a person's title, role, designation, position (e.g. "who is the CEO",
"who is the manager", "who is the director") is an SQL query.
Any question about attendance, clock-in/clock-out times, or hours worked is an SQL query.
Any question about assets, vehicles, or vehicle bookings is an SQL query.
Any question about other employees in the company directory or department listings is an SQL query.

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
