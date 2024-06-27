
from langchain.schema import SystemMessage, HumanMessage
from langchain_openai import AzureChatOpenAI


def layer_one_agent(user_query: str, llm_4o: AzureChatOpenAI) -> str:
    messages = [
        SystemMessage(
            content=(
                "You are an AI assistant developed by Snapnet for various organization use within hcmatrix, your goal as an assistant is to"
                "give prescise anwers to general questions.\n"
                "Any questions relating to employee inoformation, company information, HR ploicy, leave policies, workflows, etc and individual employee kindly responsd "
                "`Invalid Query`.\n"
                "Again, your goal as an assistant is to give answers to real life, questions in general."
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

