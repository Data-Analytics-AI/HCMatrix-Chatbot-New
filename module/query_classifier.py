from langchain_openai import AzureChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from module.utils import config
import os
import re
import json
import inspect
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

OUT_OF_SCOPE_RESPONSE = "sorry i can only provide answers to question relating to HR related questions only"

_ACK_OR_CLOSING_PATTERN = re.compile(
    r"\b(thanks|thank\s+you|thx|ty|appreciate|okay|ok|got\s+it|understood|alright|noted|great|awesome|perfect|bye|goodbye|see\s+ya|have\s+a\s+good)\b",
    re.IGNORECASE,
)


def default_conversational_reply(user_query: str) -> str:
    """Return a polite fallback response for greetings, acknowledgments, or closings."""
    text = (user_query or "").strip()
    if _ACK_OR_CLOSING_PATTERN.search(text):
        return "You're welcome! Let me know if you have any other HR or HCMatrix questions."
    return "Hello! I'm your HCMatrix HR assistant. How can I help you with HR policies or your employee records today?"


def filter_valid_chat_history(chat_history: list) -> list:
    """Return chronological Q&A pairs excluding empty items and prior out-of-scope refusals."""
    if not chat_history or not isinstance(chat_history, list):
        return []
    valid = []
    refusal_lower = OUT_OF_SCOPE_RESPONSE.strip().lower()
    for pair in chat_history:
        if not isinstance(pair, dict):
            continue
        q = str(pair.get("question", "")).strip()
        a = str(pair.get("answer", "")).strip()
        if not q and not a:
            continue
        if a.lower() == refusal_lower:
            continue
        valid.append({"question": q, "answer": a})
    return valid


def summarize_answer_for_classifier(answer: str, head_chars: int = 220, tail_chars: int = 220) -> str:
    """Keep both the start and end of long assistant answers so closing follow-up offers remain visible."""
    a = (answer or "").strip()
    if len(a) <= head_chars + tail_chars + 20:
        return a
    return f"{a[:head_chars].rstrip()} ... {a[-tail_chars:].lstrip()}"


system_prompt = SystemMessage(
    content="""You are an AI assistant that classifies user messages in an enterprise HR chatbot (HCMatrix) into one of four categories:

- "SQL": If the query asks for specific employee data, organizational data, or factual/transactional records stored in the database.
  This includes: employee personal details, job titles, designations, roles (e.g. CEO, Manager, Director), specific salary/payslip figures,
  managers, reporting structure, employment history, education, emergency contacts, attendance, clock-in/clock-out records,
  leave balances and leave applications, loan requests and balances, assets, vehicles, vehicle bookings, departments,
  public holidays, health/HMO plans, hospitals, company directory lookups, and questions asking "who is", "who has", "how many", "list all", "show me", etc.

- "RAG": If the query relates to company policies, workplace guidelines, HR procedures, HR/workplace guidance, or HCMatrix/chatbot usage.
  This includes:
  * Company policies & handbooks: dress code, work-from-home/remote policies, code of conduct, leave policies, salary increment/review policies, appraisal/performance procedures, disciplinary rules, onboarding guides.
  * Workplace & HR advisory follow-ups: questions about how salary reviews or raises work, how much raise/increment an employee can ask for, eligibility questions, how to approach a manager or HR about a workplace/compensation/leave matter, or requests to help draft an HR-related note/message (e.g. salary review justification, leave request note).
  * Chatbot & HCMatrix usage: questions about the chatbot itself (e.g. "what is your name?", "what can you do?"), its microphone/voice feature, how to use HCMatrix, or contacting support.

- "CONVERSATIONAL": ONLY for pure greetings, pleasantries, brief acknowledgments, or polite closings that do NOT ask an HR, policy, or data question.
  Examples: "Hello", "Hi", "Good morning", "Hey there", "Okay thanks", "Thank you", "Alright, got it", "Understood, thanks!", "Bye".
  IMPORTANT: If a greeting is combined with an actual question (e.g. "Hello, what is my role?", "Hi what is your name?", "Thanks, also what is my leave balance?"), do NOT use "CONVERSATIONAL" — classify according to the question ("SQL" or "RAG").

- "OUT_OF_SCOPE": ONLY if the query is genuinely unrelated to HR, the workplace, company policies, employee records, or HCMatrix/chatbot usage.
  Examples: cooking/recipes, sports, entertainment/movies/music, general software coding/debugging, math/science homework, weather, external news, translation of unrelated text, non-work personal/relationship/medical advice, or general world trivia.
  CRITICAL DISTINCTION: Workplace, career, compensation, or HR policy guidance (such as "How much raise do you think I can ask for?", "Should I speak to HR or my manager?", or accepting an offer the assistant made in the prior turn) is NOT out-of-scope — classify it as "RAG".

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

FOLLOW-UP QUESTIONS & CONTEXT AWARENESS (CRITICAL):
- Always inspect the RECENT CONVERSATION CONTEXT before classifying:
  1. Data follow-ups ("provide the names?", "who are they?", "list them", "how many are full time?", "show their emails", "break it down by department", "what about last month?") -> "SQL" when following employee/organizational data queries.
  2. Policy, compensation, & workplace guidance follow-ups ("How much raise do you think I can ask for?", "even for males?", "what if I am on probation?", "how do I request that?", "am I eligible for it?", "yes, help me outline that justification note") -> "RAG".
  3. Assistant offer continuations: Look at the end of the previous Assistant response. If the Assistant offered to explain further, provide an example, or help draft an HR note, and the user accepts or asks a related follow-up ("yes please", "go ahead", "help me write it"), route to "RAG" (or "SQL" if it offered a database lookup).
  4. Polite acknowledgments or closings ("Okay thanks", "Thank you", "Got it", "Alright") -> "CONVERSATIONAL" with a brief, polite plain-text reply. NEVER classify greetings, thanks, or HR follow-ups as "OUT_OF_SCOPE".

STANDALONE SEARCH QUERY (FOR RAG):
- Whenever category is "RAG", set "standalone_query" to a self-contained HR policy search query that resolves pronouns and implicit references from RECENT CONVERSATION CONTEXT (for example, if prior turn was about salary increments and user asks "How much raise do you think I can ask for?", standalone_query should be "salary increment policy raise amount or percentage guidelines"; if user switches topics to "What is the dress code?", standalone_query should simply be "dress code policy" without prior topic noise).

Respond strictly in JSON format:
{
  "category": "SQL" | "RAG" | "CONVERSATIONAL" | "OUT_OF_SCOPE",
  "standalone_query": "self-contained search query (required when category is RAG)",
  "reply": "brief polite plain-text response without markdown bolding (ONLY when category is CONVERSATIONAL)"
}
""")


def classify_query(func):
    """Classifies the user query as 'SQL', 'RAG', 'CONVERSATIONAL', or 'OUT_OF_SCOPE'.

    Uses recent conversation context (preserving both start and end of prior answers and
    ignoring prior out-of-scope refusals) to accurately route follow-up questions, generate
    a clean standalone search query for RAG vector retrieval, and reply directly to
    greetings/acknowledgments without unnecessary DB or vector store calls.
    """
    sig = inspect.signature(func)
    accepts_standalone = (
        "standalone_query" in sig.parameters
        or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
    )

    @wraps(func)
    async def wrapper(user_query, *args, **kwargs):
        # Extract chat_history from kwargs or positional args if present
        chat_history = kwargs.get('chat_history')
        if not chat_history and len(args) >= 6:
            chat_history = args[5]

        # Build context-aware prompt from valid prior turns (skipping out-of-scope refusals)
        content = user_query
        valid_history = filter_valid_chat_history(chat_history)
        if valid_history:
            history_lines = []
            for pair in valid_history[-4:]:
                q = pair['question']
                a = pair['answer']
                if q:
                    history_lines.append(f"User: {q}")
                if a:
                    a_summary = summarize_answer_for_classifier(a)
                    history_lines.append(f"Assistant: {a_summary}")
            if history_lines:
                history_text = "\n".join(history_lines)
                content = (
                    f"--- RECENT CONVERSATION CONTEXT ---\n"
                    f"{history_text}\n"
                    f"------------------------------------\n"
                    f"Current Question: {user_query}"
                )

        user_prompt = HumanMessage(content=content)
        response = await model.ainvoke([system_prompt, user_prompt])
        standalone_query = user_query
        conversational_reply = ""
        try:
            parsed = json.loads(response.content)
            query_class = str(parsed.get('category', 'RAG')).strip().upper()
            if query_class not in ('SQL', 'RAG', 'CONVERSATIONAL', 'OUT_OF_SCOPE'):
                query_class = 'RAG'
            sq = str(parsed.get('standalone_query') or '').strip()
            if sq:
                standalone_query = sq
            conversational_reply = str(parsed.get('reply') or '').replace('**', '').replace('__', '').strip()
        except Exception as e:
            print(f"⚠️ Query classification parsing error: {e}")
            query_class = 'RAG'

        print(f"User question classified as a {query_class} "
              f"query and is being routed to the {query_class} layer")

        # Early exit for out-of-scope queries
        if query_class == 'OUT_OF_SCOPE':
            return OUT_OF_SCOPE_RESPONSE

        # Early exit for pure greetings / acknowledgments / closings
        if query_class == 'CONVERSATIONAL':
            return conversational_reply or default_conversational_reply(user_query)

        if accepts_standalone:
            kwargs['standalone_query'] = standalone_query

        return await func(user_query, *args, layer=query_class, **kwargs)

    return wrapper
