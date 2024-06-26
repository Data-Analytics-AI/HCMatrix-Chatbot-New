


from typing import *
from rag_engine.retriever_ import Retriever
from langchain_openai import AzureChatOpenAI
from rag_engine.utils import retieve_user_query_context
from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate,  ChatPromptTemplate


def chat(query, db_retriever, llm_4o):

    general_system_template = """ 
        "You are an AI assistant developed by Snapnet for various organization use, you're capable of giving response,
        any questions related to an orginization within HCMatrix. These questions ranges from HR ploicy, leave policies, 
        workflows, etc and individual employee data."

        Given a specific context, please give a short answer to the question, if the context doesnt make sense in regards 
        to the question kindly disregard the context and give a genral answer. if you don't know, kindly say you don't know the answer
        and refer to the Snapnet Support email info@snapnetsolutions.com. 
        Don't give gibberish or out of place answers.+
        ----
        {context}
        ----
    """
    general_user_template = "Question:```{question}```"
    messages = [
                SystemMessagePromptTemplate.from_template(general_system_template),
                HumanMessagePromptTemplate.from_template(general_user_template)
    ]
    qa_prompt = ChatPromptTemplate.from_messages( messages )

    # assert chain_type in ['stuff', 'map_reduce']
    chain_type = 'stuff'
    chat_history = []

    QA_CHAIN = ConversationalRetrievalChain.from_llm(
        llm_4o, #llm,
        chain_type=chain_type,
        retriever=db_retriever,
        #memory=memory,
        return_source_documents=True,
        return_generated_question=True,
        combine_docs_chain_kwargs={'prompt': qa_prompt}
    )

    response = QA_CHAIN({"question": query, "chat_history": chat_history})
    chat_history.extend([(query, response['answer'])])
    print (response)
    
    return response, chat_history


def execute(
    user_query: str, user_metadata: Dict[str, Any], 
    llm_4O: AzureChatOpenAI, retriever: Retriever):

    db_retriever = retieve_user_query_context(user_query, user_metadata, retriever)
    response, _ = chat(user_query, db_retriever, llm_4O)

    return response

if __name__ == "__main__":
    user_metadata = {
        "user_departement_id" : 43,
        "user_role_id" : 323,
        "user_group_id" : 54
    }

    print (execute("Who is the president of Nigeria.", user_metadata))