
from langchain.schema import SystemMessage, HumanMessage
from langchain_openai import AzureChatOpenAI


def layer_one_agent(user_query: str, llm_4o: AzureChatOpenAI) -> str:
    messages = [
        SystemMessage(
            # content=(
            #     "You are an AI assistant developed by Snapnet for various organization use within hcmatrix, your goal as an assistant is to"
            #     "give prescise anwers to general questions.\n"
            #     "Any questions relating to employee inoformation, company information, HR ploicy, leave policies, workflows, etc and individual employee kindly responsd "
            #     "`Invalid Query`.\n"
            #     "Again, your goal as an assistant is to give answers to real life, questions in general."
            # )

            content=(
                "You are an AI assistant developed by Snapnet for various organization use, you're capable of giving response,"
                "any questions related to an orginization within HCMatrix. These questions ranges from HR ploicy, leave policies"
                "workflows, etc and individual employee data"

                "Given a specific context, please give a short answer to the question, if the context doesnt make sense in regards "
                "to the question kindly disregard the context and give a genral answer. if you don't know, kindly say you don't know the answer"
                "and refer to the Snapnet Support email info@snapnetsolutions.com. "
                "Don't give gibberish or out of place answers.+"
            )
        ),
        HumanMessage(content=user_query)
    ]

    response = llm_4o.invoke(messages)
    content = response.content
    return content



def layer_one_validator(user_query: str, llm_answer: str, llm_4o: AzureChatOpenAI) -> str:
    prompt = f"""
        
        Question: {user_query}
        Answer: {llm_answer}

        Assess the correctness of the answer to the given question.
        if the answer is correct and direct reply `Good` if the answer is Invalid Query or not correct reply `No Good`.

        Note, the answer must be direct and specific to the question, not some suggestions or to-do. If the assistant can't provide the right answer,
        then it should be a very low correcness score.
    """

    response = llm_4o.invoke(prompt)
    content = response.content
    return content

