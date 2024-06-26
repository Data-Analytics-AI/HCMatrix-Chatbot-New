
import os
from config.params import params_config
from langchain_openai import AzureChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
#from langchain.agents.agent_toolkits.sql import SQLDatabaseToolkit
from langchain.agents.agent_toolkits.sql.toolkit import SQLDatabaseToolkit



data_dir = params_config['data_dir']
def execute(company_id: str, employee_id: str, query: str, llm_4O: AzureChatOpenAI):

    company_data_dir = os.path.join(data_dir, f"cp_{company_id}")
    print (company_data_dir)
    if not os.path.exists(company_data_dir):
        raise NotImplementedError("The company database is yet to be implemented or does not exist.")
    
    company_sql_dir = os.path.join(company_data_dir, f"cp_{company_id}_sql")
    employee_sql_db = os.path.join(company_sql_dir, f"emp_{employee_id}_sql_db.db")
    if not os.path.exists(employee_sql_db):
        raise NotImplementedError("The employee database is yet to be implemented or does not exist.")


    employee_db = SQLDatabase.from_uri(f"sqlite:///{employee_sql_db}")
    toolkit = SQLDatabaseToolkit(db=employee_db, llm=llm_4O)
    toolkit.get_tools()

    agent_executor = create_sql_agent(
        llm_4O, toolkit=toolkit, 
        agent_type='openai-tools',
        verbose=False,
        max_execution_time=30,
        handle_parsing_errors=False)
    
    response = agent_executor.invoke(query)

    ## Note, this chatbot is currently experimental and might return incorrect queries from time to time.
    ## Should that be the case, kindly retry or meet with your organization human resource manager.

    return response
    # return response["output"]


if __name__ == "__main__":
    company_id = "53"
    employee_id = 372 # 373
    # query = 'What is the maximum number of dependents I can register within my HMO Plan?'
    query = 'When is my work anniversary?'

    print (execute(company_id, employee_id, query))