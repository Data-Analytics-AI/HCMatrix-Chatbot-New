from langchain.tools import Tool
from hcm_chatbot.sql_layer import sql_layer_agent # Your existing function
from hcm_chatbot.rag_layer import rag_layer_agent # Your existing function

# You'll need to slightly adjust your agent functions to fit the tool input format
# For example, they might need to accept a single string or a dictionary

def create_sql_tool(llm, gold_adls_conn, chatbot_cache, employee_metadata):
    return Tool(
        name="EmployeeDataSQLTool",
        func=lambda query: sql_layer_agent(
            company_id=employee_metadata.company_id,
            employee_id=employee_metadata.id,
            query=query,
            llm_4O=llm,
            gold_adls_conn=gold_adls_conn,
            chatbot_cache=chatbot_cache
        ),
        description="""Use this tool to answer specific questions about an employee's personal data. 
                     This includes their salary, leave balance, manager's name, role history, 
                     personal information, and employment history. Input should be a full question."""
    )

def create_rag_tool(llm, employee_metadata):
    return Tool(
        name="CompanyPolicyRAGTool",
        func=lambda query: rag_layer_agent(
            user_query=query,
            llm_4o=llm,
            company_id=employee_metadata.company_id
        ),
        description="""Use this tool to answer general questions about company policies, procedures, 
                     and guidelines from the HR handbook. This includes topics like dress code, 
                     leave policies, work-from-home rules, and code of conduct."""
    )
