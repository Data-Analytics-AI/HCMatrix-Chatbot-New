
from rag_engine.utils import retrieve_document_metadata, pdf_loader
from rag_engine.emdedder import UserDocument


def upsert_user_document(pdf_path, metadata):
    chunked_docs = pdf_loader(pdf_path, metadata=metadata)

    user_db_instance = UserDocument()
    user_db_instance(chunked_docs)


def execute():

    

    metadata = retrieve_document_metadata(31, access_df)
    upsert_user_document(valid_urls[0], metadata)