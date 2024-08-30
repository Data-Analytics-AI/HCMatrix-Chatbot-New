
import os
from config.params import params_config
from langchain_openai import AzureChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain.prompts.chat import ChatPromptTemplate
from data_preprocessing.gold_layer import GoldLayerUtils
from langchain_community.agent_toolkits import create_sql_agent
#from langchain.agents.agent_toolkits.sql import SQLDatabaseToolkit
from langchain.agents.agent_toolkits.sql.toolkit import SQLDatabaseToolkit



data_dir = "temp_data/" # params_config['data_dir']
def execute(company_id: str, employee_id: str, query: str, llm_4O: AzureChatOpenAI, gold_adls_conn: GoldLayerUtils):

    company_data_dir = os.path.join(data_dir, f"cp_{company_id}")
    print (company_data_dir)
    # if not os.path.exists(company_data_dir):
    #     raise NotImplementedError("The company database is yet to be implemented or does not exist.")
    
    company_sql_dir = os.path.join(company_data_dir, f"cp_{company_id}_sql")
    employee_sql_db = os.path.join(company_sql_dir, f"emp_{employee_id}_sql_db.db")
    # if not os.path.exists(employee_sql_db):
    #     raise NotImplementedError("The employee database is yet to be implemented or does not exist.")

    #################################################################
    ############# There's a bug from line 29 to 38 ##################
    #### the employee_db, sql toolkit and the agent_executor ########
    ## should only be initialized once rahter than re-initializing ##
    # on every api call. the only way i can think of right now is   #
    # create a cache of the three as a single class object then it  #
    ############## should at least reduce the latency.  #############
    ###################### Damn this is huge ########################

    # employee_db = SQLDatabase.from_uri(f"sqlite:///{employee_sql_db}")
    sql_db = gold_adls_conn.read_file_from_adls(employee_sql_db)
    employee_db = SQLDatabase.from_uri(f"sqlite:///{sql_db}")

    toolkit = SQLDatabaseToolkit(db=employee_db, llm=llm_4O)
    toolkit.get_tools()

    agent_executor = create_sql_agent(
        llm_4O, toolkit=toolkit, 
        agent_type='openai-tools',
        verbose=False,
        max_execution_time=30,
        handle_parsing_errors=False)
    
    ################## Bug ends here #################################
    query_promt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are an AI assistant developed by Snapnet for various organization use, you're capable of giving response \
    to any questions related to an orginization within HCMatrix. These questions ranges from HR ploicy, leave policies, workflows,\
    etc and individual employee data. Don't talk about the strucutre of the database or how you arrived at your answer.\
    You're currently conversing with employee id `{employee_id}`"),
            ("user", "{user_query}.")
        ]
    )
    # If you can't find the answer simply give a succint answer and only provide the employee with the needed information \
    
    agent_response = agent_executor.invoke(
        query_promt.format(employee_id= employee_id, user_query=query)
    )
    response = agent_response['output']

    ## Note, this chatbot is currently experimental and might return incorrect queries from time to time.
    ## Should that be the case, kindly retry or meet with your organization human resource manager.
    wrong_response_list = [
        "Agent stopped due to iteration limit or time limit.",
        "Agent stopped due to max iterations."
    ]

    if response in wrong_response_list:
        return "Sorry, couldn't get the best response to your query, kindly reach out to your HR department for the best response to your query or retry."
    return response
    # return response["output"]


if __name__ == "__main__":
    company_id = "53"
    employee_id = 372 # 373
    # query = 'What is the maximum number of dependents I can register within my HMO Plan?'
    query = 'When is my work anniversary?'

    print (execute(company_id, employee_id, query))