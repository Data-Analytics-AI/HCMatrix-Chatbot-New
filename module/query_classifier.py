import json
from functools import wraps
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from module.utils import config

# Load Azure credentials from your config
azure_oai_credentials = config['production']['azure_oai_credentials']

# Initialize the LLM for classification
model = AzureChatOpenAI(
    api_version=azure_oai_credentials["4O_API_VERSION"],
    azure_deployment=azure_oai_credentials["4O_AZURE_DEPLOYMENT"],
    model=azure_oai_credentials["4O_MODEL_NAME"],
    model_kwargs={"response_format": {"type": "json_object"}},
)

# A more robust and maintainable prompt
system_prompt = SystemMessage(
    content="""You are an AI assistant that classifies user queries into one of two categories:
- "SQL": If the query is related to the user's own specific data, like their name, salary, manager, hire date, personal information, or role history.
- "RAG": If the query is about general company policies, like dress code, leave, work-from-home, or code of conduct.

Respond strictly in JSON format: {"category": "SQL" or "RAG"}
"""
)


def classify_query(func):
    """
    Decorator that classifies a user query as 'SQL' or 'RAG' and passes the
    classification to the wrapped function.
    """
    @wraps(func)
    async def wrapper(user_query, *args, **kwargs):
        user_prompt = HumanMessage(content=user_query)
        try:
            response = await model.ainvoke([system_prompt, user_prompt])
            query_class = json.loads(response.content)['category']
            print(f"Query classified as '{query_class}'")
            # Pass the classification result to the decorated function
            return await func(user_query, *args, layer=query_class, **kwargs)
        except Exception as e:
            # This block prevents the app from crashing if the LLM fails
            print(f"Error during query classification: {e}. Defaulting to RAG.")
            return await func(user_query, *args, layer="RAG", **kwargs)

    return wrapper

