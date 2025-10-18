# hcm_chatbot/tools.py

from langchain.tools import tool

@tool
async def sql_query_tool(query: str) -> str:
    """
    Use this tool to answer questions about an employee's personal data, such as salary, manager,
    employment history, finance details, personal information, or role history.
    The input should be the user's direct question.
    """
    # The actual implementation is set dynamically in the router.
    pass


@tool
async def rag_query_tool(query: str) -> str:
    """
    Use this tool to answer general questions about company policies, such as dress code, leave policies,
    work-from-home policies, or code of conduct.
    The input should be the user's direct question.
    """
    # The actual implementation is set dynamically in the router.
    pass
