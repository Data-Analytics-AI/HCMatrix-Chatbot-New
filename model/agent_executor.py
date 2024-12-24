
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain.agents.agent_toolkits.sql.toolkit import SQLDatabaseToolkit

def sql_agent(employee_sql_db, llm_4O):
    employee_db = SQLDatabase.from_uri(f"sqlite:///{employee_sql_db}")
    toolkit = SQLDatabaseToolkit(db=employee_db, llm=llm_4O)
    toolkit.get_tools()

    agent_executor = create_sql_agent(
        llm_4O, toolkit=toolkit, 
        agent_type='openai-tools',
        verbose=False,
        max_execution_time=30,
        handle_parsing_errors=False)
    
    return agent_executor
