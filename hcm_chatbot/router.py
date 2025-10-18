# hcm_chatbot/router.py

from langchain_openai import AzureChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from api.schema import EmployeeMetadataSchema
from module.gold_layer import GoldLayerUtilsAsync
from module.cache_service import LRUCache

# Import the simple tool definitions
from hcm_chatbot.tools import sql_query_tool, rag_query_tool

# Import the actual implementation logic
from hcm_chatbot.sql_layer import sql_layer_agent
from hcm_chatbot.rag_layer import rag_layer_agent


# This prompt acts as the "brain" for the agent, telling it how to behave.
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


# This new function replaces your old rule-based router.
async def chatbot_entry_execution(
        user_query: str,
        employee_metadata: EmployeeMetadataSchema,
        llm_4o: AzureChatOpenAI,
        gold_adls_conn: GoldLayerUtilsAsync,
        chatbot_cache: LRUCache,
) -> str:
    """
    Uses a LangChain agent to decide which tool to use (SQL or RAG) to answer a user's query.
    """
    print(f"User question: {user_query}")

    # Dynamically assign the real-world logic to the simple tool definitions.
    # This connects the tool's "menu item" with the "kitchen's recipe".
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

    # Create the agent and the executor that will run the agent's decisions.
    agent = create_openai_tools_agent(llm_4o, tools, agent_prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    # Run the agent and wait for its final answer.
    result = await agent_executor.ainvoke({
        "input": user_query,
        "chat_history": []  # Pass an empty list if you don't use chat history
    })

    return result["output"]
