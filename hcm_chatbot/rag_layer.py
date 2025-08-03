from langchain_pinecone.vectorstores import PineconeVectorStore
from langchain.prompts.chat import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_openai.embeddings import AzureOpenAIEmbeddings
from module.utils import config

# Azure OpenAI Configuration


api_key = config['production']['azure_oai_credentials']['AZURE_EMBEDDING_API_KEY']
api_base = config['production']['azure_oai_credentials']['AZURE_EMBEDDING_API_BASE']
api_version = config['production']['azure_oai_credentials']['AZURE_EMBEDDING_API_VERSION']
vector_store_path = config['production']['vector_db_config']['path']
layer_one_agent_prompt = config['production']['layer_one_agent_prompt']
pinecone_key = config['production']['pinecone_credentials']['PINECONE_API_KEY']
index_name = config['production']['pinecone_credentials']['index_name']

# Embeddings Setup
embedding_model = AzureOpenAIEmbeddings(
    model="text-embedding-3-large",
    openai_api_key=api_key,
    azure_endpoint=api_base,
    openai_api_version=api_version
)

# Load the vector store
vector_store = PineconeVectorStore(
    embedding=embedding_model,
    pinecone_api_key=pinecone_key,
    index_name=index_name)

# Global prompt (only needs to be created once)
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", layer_one_agent_prompt),
        ("human", "{input}"),
    ]
)

# Cache retrievers and chains per company_id
retriever_cache = {}
chain_cache = {}


def get_retriever(company_id: str):
    """Retrieve or create a retriever for a given company ID.

    This function checks if a retriever exists in the cache for the specified
    `company_id`. If not, it creates a new retriever from the vector store,
    using similarity-based search with a filter for the given company.

    Args:
        company_id (str): The unique identifier of the company.

    Returns:
        object: A retriever instance configured for the specified company.
        """
    if company_id not in retriever_cache:
        retriever_cache[company_id] = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 8, "filter": {"company_id": company_id}}
        )
    return retriever_cache[company_id]


def get_rag_chain(company_id: str, llm_4o: AzureChatOpenAI):
    """Retrieve or create a RAG (Retrieval-Augmented Generation) chain for a given company ID.

        This function checks if a RAG chain exists in the cache for the specified `company_id`.
        If not, it retrieves or creates a retriever, then constructs a retrieval chain using
        a question-answering model.

        Args:
            company_id (str): The unique identifier of the company.
            llm_4o (object): The language model used for generating responses.

        Returns:
            object: A retrieval-augmented generation (RAG) chain for the specified company.
        """
    if company_id not in chain_cache:
        retriever = get_retriever(company_id)  # Get cached retriever
        question_answer_chain = create_stuff_documents_chain(llm_4o, prompt)
        chain_cache[company_id] = create_retrieval_chain(retriever, question_answer_chain)
    return chain_cache[company_id]


async def rag_layer_agent(user_query: str, llm_4o: AzureChatOpenAI, company_id: str) -> str:
    """Processes a user query using a Retrieval-Augmented Generation (RAG) chain.

    This function retrieves or creates a cached RAG chain for the specified company ID
    and asynchronously invokes it with the user query to generate a response.

    Args:
        user_query (str): The input query from the user.
        llm_4o (AzureChatOpenAI): The language model used for generating responses.
        company_id (str): The unique identifier of the company.

    Returns:
        str: The generated response from the RAG chain.

    """
    rag_chain = get_rag_chain(company_id, llm_4o)  # Get cached chain
    result = await rag_chain.ainvoke({"input": user_query})
    return result['answer']
