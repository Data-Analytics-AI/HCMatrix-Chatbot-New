import pandas as pd
from typing import Any, Dict, Optional, Union, List
from pathlib import Path
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter


def retrieve_document_metadata(document_id: int, company_file_access_df: pd.DataFrame) -> Dict[str, Any]:
    department_pass = company_file_access_df[
        (company_file_access_df['fileId'] == document_id) & (company_file_access_df['type'] == "department")][
        'entityId'].to_list()

    role_pass = company_file_access_df[
        (company_file_access_df['fileId'] == document_id) & (company_file_access_df['type'] == "role")][
        'entityId'].to_list()

    group_pass = company_file_access_df[
        (company_file_access_df['fileId'] == document_id) & (company_file_access_df['type'] == "group")][
        'entityId'].to_list()

    metadata = {
        "doc_id": document_id,
        "department_pass": list(map(str, department_pass)),
        "role_pass": list(map(str, role_pass)),
        "group_pass": list(map(str, group_pass)),
    }
    return metadata


def pdf_loader(
        pdf_path: Union[Path, str], chunk_size: int = 600,
        chunk_overlap: int = 80,
        metadata: Optional[Dict[str, Any]] = None
) -> List[Document]:
    """
    Load documents from pdf
    """

    from langchain.document_loaders import PyPDFLoader
    loader = PyPDFLoader(pdf_path)
    docs: List[Document] = loader.load()

    # set a threshold depending on the size of the documents for splitting
    # chunk_size = 350
    # chunk_overlap = 50

    doc_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
        length_function=len,
    )

    chunks = doc_splitter.split_documents(docs)
    if metadata is not None:
        for chunk in chunks:
            chunk.metadata.update(metadata)

    return chunks


# assert search_type in ['mmr', 'similarity', 'similarity_score_threshold']
# This should be part of the retriever class or a more stable place

def retrieve_user_query_context(query: str, user_metadata: Dict[str, Any], retriever):
    user_department_id = str(user_metadata["user_department_id"])
    user_role_id = str(user_metadata["user_role_id"])
    user_group_id = str(user_metadata["user_group_id"])

    user_department_id = "0"
    user_role_id = "0"
    user_group_id = "0"

    search_type = "similarity"

    # Another Idea is to get all the employees and the document_Id they have access to in a database. this will
    # reduce the time. but re-writing code.
    # query = "Who is the president of Nigeria?"
    # query = "Are you an FBI Agent?"
    # query = "What is 2 * 2?"
    filter = {"department_pass": {"$in": [user_department_id]}}
    sim_retriever = retriever.similarity_search(query, filter=filter)

    if (len(sim_retriever) == 0) and (user_role_id is not None):
        filter = {"role_pass": {"$in": [user_role_id]}}
        sim_retriever = retriever.similarity_search(query, filter=filter)

    if (len(sim_retriever) == 0) and (user_group_id is not None):
        filter = {"group_pass": {"$in": [user_group_id]}}
        sim_retriever = retriever.similarity_search(query, filter=filter)

    db_retriever = retriever.default_retriever(
        # search_type, **{
        #     "k": 5, "lambda_mult": 0.6,
        #     "filter": filter,})

        search_type, **{
            "k": 5, "filter": filter, })

    return db_retriever
