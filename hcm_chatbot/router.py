# hcm_chatbot/router.py

from langchain_openai import AzureChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from api.schema import EmployeeMetadataSchema
from module.gold_layer import GoldLayerUtilsAsync
from module.cache_service import LRUCache

# Import the tools we defined
from hcm_chatbot.tools import sql_query_tool, rag_query_tool

# Import the actual logic functions
# (You can place these functions in any logical place, like a 'services' or 'layers' file)
from hcm_chatbot.sql_layer import sql_layer_agent
from hcm_chatbot.rag_layer import rag_layer_agent


agent_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", (
            "You are a helpful assistant for company employees. You have access to tools to answer questions "
            "about company policy and an employee's personal data. Use the tools as needed to construct a "
            "complete answer."
        )),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ]
)


async def chatbot_entry_execution(
        user_query: str,
        employee_metadata: EmployeeMetadataSchema,
        llm_4o: AzureChatOpenAI,
        gold_adls_conn: GoldLayerUtilsAsync,
        chatbot_cache: LRUCache,
) -> str:
    """
    Routes the user query to the appropriate tool using an agent.
    """
    print(f"User question: {user_query}")
    
    # Set the implementation for each tool
    sql_query_tool.func = lambda query: sql_layer_agent(
        query=query,
        company_id=employee_metadata.company_id,
        employee_id=employee_metadata.id,
        llm_4O=llm_4o,
        gold_adls_conn=gold_adls_conn,
        chatbot_cache=chatbot_cache,
    )
    
    rag_query_tool.func = lambda query: rag_layer_agent(
        query=query,
        llm_4o=llm_4o,
        company_id=employee_metadata.company_id
    )

    tools = [sql_query_tool, rag_query_tool]

    # Create the agent
    agent = create_openai_tools_agent(llm_4o, tools, agent_prompt)
    
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    # Invoke the agent
    result = await agent_executor.ainvoke({
        "input": user_query,
        "chat_history": []
    })

    return result["output"]
