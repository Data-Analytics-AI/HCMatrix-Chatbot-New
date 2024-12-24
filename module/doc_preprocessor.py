from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain_openai.embeddings import AzureOpenAIEmbeddings
import pdfplumber
from module.utils import config


def preprocess_pdf_with_local_embeddings(pdf_path, vector_store_path="vectorstore"):
    """
    Extracts text and tables from a PDF, preprocesses them, and stores them in a vector database.
    Uses a local HuggingFace embedding model for embeddings.

    Parameters:
        pdf_path (str): Path to the PDF file.
        vector_store_path (str): Path to store the vector database. Defaults to "vectorstore".

    Returns:
        vector_store (Chroma): A Chroma vector store loaded with embeddings.
    """
    # Step 1: Extract text from the PDF
    loader = PyPDFLoader(pdf_path)
    documents = loader.load()  # List of documents per page

    # Step 2: Extract tables using pdfplumber
    table_texts = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()  # Extract tables from the page
                for table in tables:
                    # Convert each table to a string representation
                    table_text = "\n".join(["\t".join(row) for row in table if row])
                    table_texts.append(table_text)
    except Exception as e:
        print(f"Table extraction failed: {e}")

    # Step 3: Preprocess text and tables
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    text_chunks = text_splitter.split_documents(documents)  # Split textual data

    # Process table data into chunks
    table_chunks = [{"page_content": table_text} for table_text in table_texts]

    # Combine text and table chunks
    all_chunks = text_chunks + table_chunks

    # Step 4: Embed and store in a vector database
    # Azure OpenAI Configuration
    api_key = config['production']['azure_oai_credentials']['AZURE_EMBEDDING_API_KEY']
    api_base = config['production']['azure_oai_credentials']['AZURE_EMBEDDING_API_BASE']
    api_version = config['production']['azure_oai_credentials']['AZURE_EMBEDDING_API_VERSION']

    # Embeddings Setup
    embedding_model = AzureOpenAIEmbeddings(
        model="text-embedding-3-large",
        openai_api_key=api_key,
        openai_api_base=api_base,
        openai_api_version=api_version
    )

    vector_store = Chroma.from_documents(all_chunks, embedding_model, persist_directory=vector_store_path)

    # Persist the vector store
    vector_store.persist()
    print(f"Vector store saved at: {vector_store_path}")
    return vector_store

