from typing import Dict, Any
from rag_engine.retriever_ import Retriever
from langchain_openai import AzureChatOpenAI
from rag_engine.utils import retrieve_user_query_context
from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate, ChatPromptTemplate


def chat(query, db_retriever, llm_4o):
    general_system_template = """ 
        "You are an AI assistant developed by Snapnet for various organization use, you're capable of giving response,
        any questions related to an organization within HCMatrix. These questions ranges from HR policy, leave policies, 
        workflows, etc and individual employee data."

        Given a specific context, please give a short answer to the question, if the context doesnt make sense in 
        regards to the question kindly disregard the context and give a general answer. if you don't know, kindly say 
        you don't know the answer and refer to the Snapnet Support email info@snapnetsolutions.com. Don't give 
        gibberish or out of place answers.+ ---- {context} ----"""
    general_user_template = "Question:```{question}```"
    messages = [
        SystemMessagePromptTemplate.from_template(general_system_template),
        HumanMessagePromptTemplate.from_template(general_user_template)
    ]
    qa_prompt = ChatPromptTemplate.from_messages(messages)

    # assert chain_type in ['stuff', 'map_reduce']
    chain_type = 'stuff'
    chat_history = []

    qa_chain = ConversationalRetrievalChain.from_llm(
        llm_4o,
        chain_type=chain_type,
        retriever=db_retriever,
        return_source_documents=True,
        return_generated_question=True,
        combine_docs_chain_kwargs={'prompt': qa_prompt}
    )

    response = qa_chain({"question": query, "chat_history": chat_history})
    chat_history.extend([(query, response['answer'])])
    print(response)

    return response, chat_history


def execute(
        user_query: str, user_metadata: Dict[str, Any],
        llm_4O: AzureChatOpenAI, retriever: Retriever):
    db_retriever = retrieve_user_query_context(user_query, user_metadata, retriever)
    response, _ = chat(user_query, db_retriever, llm_4O)

    return response
