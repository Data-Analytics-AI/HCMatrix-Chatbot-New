# hcm_chatbot/router.py

from langchain_openai import AzureChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from api.schema import EmployeeMetadataSchema
from module.gold_layer import GoldLayerUtilsAsync
from module.cache_service import LRUCache

# FIX: Removed unused imports and corrected the comment spacing
from hcm_chatbot.tools import sql_query_tool, rag_query_tool  # The new tool functions


# FIX: Corrected prompt to be multi-line and under 120 chars per line
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


# FIX: Added two blank lines for PEP 8 compliance
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
    
    # Bind the necessary arguments to the tools
    sql_tool_with_args = sql_query_tool.bind(
        employee_metadata_dict=employee_metadata.dict(),
        llm_4o=llm_4o,
        gold_adls_conn=gold_adls_conn,
        chatbot_cache=chatbot_cache
    )
    rag_tool_with_args = rag_query_tool.bind(
        employee_metadata_dict=employee_metadata.dict(),
        llm_4o=llm_4o
    )

    tools = [sql_tool_with_args, rag_tool_with_args]

    # Create the agent
    agent = create_openai_tools_agent(llm_4o, tools, agent_prompt)

    # FIX: Corrected comment spacing
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)  # verbose=True is great for debugging

    # We don't have chat history in this example, so we pass an empty list
    result = await agent_executor.ainvoke({
        "input": user_query,
        "chat_history": []
    })

    return result["output"]
