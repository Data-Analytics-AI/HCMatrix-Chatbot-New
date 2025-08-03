from module.cache_service import LRUCache
from langchain_openai import AzureChatOpenAI
from api.schema import EmployeeMetadataSchema
from module.gold_layer import GoldLayerUtilsAsync
from hcm_chatbot.sql_layer import sql_layer_agent
from hcm_chatbot.rag_layer import rag_layer_agent
from module.utils import timing_decorator
from module.query_classifier import classify_query

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate
from hcm_chatbot.tools import create_sql_tool, create_rag_tool # The new tool functions

# Define the master agent's prompt
# Note: The placeholder {agent_scratchpad} is crucial for the agent to "think"
agent_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant for company employees. You have access to tools to answer questions about company policy and an employee's personal data. Use the tools as needed to construct a complete answer."),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

async def chatbot_entry_execution(
        user_query: str,
        employee_metadata: EmployeeMetadataSchema,
        llm_4o: AzureChatOpenAI,
        gold_adls_conn: GoldLayerUtilsAsync,
        chatbot_cache: LRUCache,
) -> str:
    """
    This function now uses a tool-based agent to answer complex queries.
    """
    print(f"User question: {user_query}")

    # 1. Create the tools for this specific employee
    sql_tool = create_sql_tool(llm_4o, gold_adls_conn, chatbot_cache, employee_metadata)
    rag_tool = create_rag_tool(llm_4o, employee_metadata)
    tools = [sql_tool, rag_tool]

    # 2. Create the agent
    agent = create_openai_tools_agent(llm_4o, tools, agent_prompt)
    
    # 3. Create the Agent Executor, which runs the agent and its tools
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True) # verbose=True is great for debugging

    # 4. Invoke the agent
    response = await agent_executor.ainvoke({"input": user_query})

    return response['output']
