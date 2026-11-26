from langchain_pinecone.vectorstores import PineconeVectorStore
from langchain.prompts.chat import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_openai.embeddings import AzureOpenAIEmbeddings
from module.utils import config
from module.query_classifier import filter_valid_chat_history

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

# Cache retrievers and chains
retriever_cache = {}
chain_cache = {}
qa_chain_cache = {}


def get_retriever(company_id: str):
    """Retrieve or create a retriever for a given company ID."""
    if company_id not in retriever_cache:
        retriever_cache[company_id] = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 5, "filter": {"company_id": company_id}}
        )
    return retriever_cache[company_id]


def get_qa_chain(llm_4o: AzureChatOpenAI):
    """Retrieve or create a cached document-stuffing QA chain."""
    key = id(llm_4o)
    if key not in qa_chain_cache:
        qa_chain_cache[key] = create_stuff_documents_chain(llm_4o, prompt)
    return qa_chain_cache[key]


def get_rag_chain(company_id: str, llm_4o: AzureChatOpenAI):
    """Retrieve or create a full RAG chain for a given company ID (legacy helper)."""
    if company_id not in chain_cache:
        retriever = get_retriever(company_id)
        question_answer_chain = get_qa_chain(llm_4o)
        chain_cache[company_id] = create_retrieval_chain(retriever, question_answer_chain)
    return chain_cache[company_id]


def build_rag_search_query(user_query: str, valid_history: list, standalone_query: str = None) -> str:
    """Build a clean, focused Pinecone search query without embedding raw chat history dumps."""
    if standalone_query and standalone_query.strip():
        return standalone_query.strip()
    if valid_history and len((user_query or "").split()) <= 8:
        last_q = str(valid_history[-1].get("question", "")).strip()
        if last_q and last_q.lower() != (user_query or "").strip().lower():
            return f"{last_q} {user_query}".strip()
    return user_query


async def rag_layer_agent(
    user_query: str,
    llm_4o: AzureChatOpenAI,
    company_id: str,
    chat_history: list = None,
    standalone_query: str = None,
) -> str:
    """Processes a user query using decoupled Pinecone retrieval and history-aware QA generation.

    Pinecone embeds ONLY the focused standalone search query (avoiding vector dilution from prior
    payslips or long answers), while the LLM receives the clean conversation history for context.
    """
    valid_history = filter_valid_chat_history(chat_history)
    search_query = build_rag_search_query(user_query, valid_history, standalone_query=standalone_query)

    retriever = get_retriever(company_id)
    docs = await retriever.ainvoke(search_query)

    # Prepend clean conversation history (excluding out-of-scope refusals) for LLM generation only
    augmented_input = user_query
    if valid_history:
        history_lines = []
        for pair in valid_history:
            history_lines.append(f"User: {pair['question']}")
            history_lines.append(f"Assistant: {pair['answer']}")
        history_block = (
            "--- CONVERSATION HISTORY ---\n"
            + "\n".join(history_lines)
            + "\n----------------------------\n"
        )
        augmented_input = f"{history_block}Current Question: {user_query}"

    qa_chain = get_qa_chain(llm_4o)
    result = await qa_chain.ainvoke({"context": docs, "input": augmented_input})
    if isinstance(result, dict):
        return result.get("answer", str(result))
    return result

