from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_pinecone import PineconeVectorStore
from langchain_openai.embeddings import AzureOpenAIEmbeddings
from azure.storage.blob import BlobClient
from urllib.parse import urlparse, unquote
import os
import uuid
from module.utils import config


# Azure OpenAI Configuration

api_key = config['production']['azure_oai_credentials']['AZURE_EMBEDDING_API_KEY']
api_base = config['production']['azure_oai_credentials']['AZURE_EMBEDDING_API_BASE']
api_version = config['production']['azure_oai_credentials']['AZURE_EMBEDDING_API_VERSION']
pinecone_key = config['production']['pinecone_credentials']['PINECONE_API_KEY']


def download_pdf_and_chunk_with_metadata(
        url: str,
        directory: str,
        company_id: str = "1",
        chunk_size: int = 1000,
        chunk_overlap: int = 100):
    """
    Download a PDF from a URL, split it into chunks, and add a company_id and unique chunk_id to the metadata.

    :param url: URL to the PDF file.
    :param directory: Local directory to save the PDF.
    :param company_id: Custom company ID to add to metadata.
    :param chunk_size: Number of characters per chunk.
    :param chunk_overlap: Number of overlapping characters between chunks.
    :return: List of Document objects with updated metadata.
    """
    # Create a BlobClient using the URL
    blob_client = BlobClient.from_blob_url(url)

    # Generate file name from the URL
    file_name = os.path.basename(urlparse(url).path)
    file_name = unquote(file_name)

    # Creates the directory (including parent directories if needed)
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Local file path
    local_file_path = os.path.join(directory, file_name)

    # Download the PDF
    try:
        with open(local_file_path, "wb") as file:
            blob_data = blob_client.download_blob()
            blob_data.readinto(file)
        print(f"File downloaded successfully as {local_file_path}")
    except Exception as e:
        print(f"Error downloading the file: {e}")
        return []

    # Load and process the PDF
    loader = PyPDFLoader(local_file_path)
    documents = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    chunks = text_splitter.split_documents(documents)

    # Add company_id and unique IDs to metadata
    updated_chunks = []
    for chunk in chunks:
        unique_id = str(uuid.uuid4())
        updated_metadata = {**chunk.metadata, 'company_id': company_id, 'chunk_id': unique_id}
        updated_chunk = Document(page_content=chunk.page_content, metadata=updated_metadata)
        updated_chunks.append(updated_chunk)

    return updated_chunks


def store_chunks_in_chromadb(chunks, index_name: str):
    """
    Store the given chunks in ChromaDB with their metadata.

    :param chunks: List of Document objects with metadata.
    :param index_name: The name of the index we want to store our data.
    :return: None
    """
    # Embeddings Setup
    embedding_model = AzureOpenAIEmbeddings(
        model="text-embedding-3-large",
        openai_api_key=api_key,
        azure_endpoint=api_base,
        openai_api_version=api_version
    )

    vectorstore = PineconeVectorStore(embedding=embedding_model, pinecone_api_key=pinecone_key, index_name=index_name)
    vectorstore.from_documents(chunks, index_name=index_name, embedding=embedding_model)

    print(f"Chunks stored in PineconeDb with metadata including company_id and chunk_id.")
