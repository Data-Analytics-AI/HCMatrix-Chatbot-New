from langchain_community.vectorstores.chroma import Chroma
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

# Embeddings Setup
embedding_model = AzureOpenAIEmbeddings(
    model="text-embedding-3-large",
    openai_api_key=api_key,
    azure_endpoint=api_base,
    openai_api_version=api_version
)

# Load the vector store
vector_store = Chroma(persist_directory=vector_store_path, embedding_function=embedding_model)


def layer_one_agent(user_query: str, llm_4o: AzureChatOpenAI, company_id) -> str:
    # The implementation below is for chat models

    # Create the prompt template
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", layer_one_agent_prompt),
            ("human", "{input}"),
        ]
    )

    # Create a retriever
    retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={
            "k": 5,  # Number of results to return
            "filter": {"company_id": company_id}  # Filter by company_id
        })

    # Step 4: Create a RetrievalQA chain
    question_answer_chain = create_stuff_documents_chain(llm_4o, prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)

    response = rag_chain.invoke({"input": user_query})
    return response['answer']


def layer_one_validator(user_query: str, llm_answer: str, llm_4o: AzureChatOpenAI) -> str:
    prompt = f"""
        
        Question: {user_query}
        Answer: {llm_answer}

        Assess the correctness of the answer to the given question.
        if the answer is correct and direct reply `Good` if the answer is Invalid Query or not correct reply `No Good`.

        Note, the answer must be direct and specific to the question, not some suggestions or to-do. If the assistant 
        can't provide the right answer, then it should be a very low correctness score."""

    response = llm_4o.invoke(prompt)
    content = response.content
    return content
