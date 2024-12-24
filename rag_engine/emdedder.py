
import os
import uuid
from typing import *
from langchain.docstore.document import Document
from langchain_openai import AzureOpenAIEmbeddings
from module.utils import config
# from config.params import credentials_config
from rag_engine.pinecone_ import PineconeDB

azure_oai_credentials = config['production']['azure_oai_credentials']

os.environ["AZURE_OPENAI_API_KEY"]  = azure_oai_credentials['AZURE_OPENAI_API_KEY']
os.environ["AZURE_OPENAI_ENDPOINT"] = azure_oai_credentials['AZURE_OPENAI_ENDPOINT']

class EmbedChunks:

    """
    Embedding class for embedding both text and documents using the embeddings model
    """

    def __init__(self) -> None:

        self.embeddings_model = AzureOpenAIEmbeddings(
            azure_deployment   = azure_oai_credentials["AZURE_EMBEDDING_DEPLOYMENT"],
            openai_api_version = azure_oai_credentials["AZURE_EMBEDDING_API_VERSION"]
        )
    
    @property
    def embedding_query(self,):
        return self.embeddings_model.embed_query

    def __call__(self, batch_docs: List[str]) -> List[float]:
        embeddings = self.embeddings_model.embed_documents(batch_docs)
        return embeddings



class UserDocument(PineconeDB):

    """
    ### This class process a user document and upsert it to the VDB
    """
    def __init__(self,) -> None:
        """
        doc_id: str = A unique id for the user document to query whenever the user want to converse
        """
        super().__init__()
        self.chunk_batch_size = 32 # 64
        self.embeddings_inst = EmbedChunks()
        # self.index = self.init_index()

    def _prepare_batch(self, chunks: List[Document]) -> Tuple[List[str], List[dict], List[str]]:
        batch_text = [text.page_content for text in chunks]
        batch_metadata = []
        uuid_strings = []

        for text in chunks:
            text.metadata.update({"content": text.page_content})
            batch_metadata.append(text.metadata)
            uuid_strings.append(str(uuid.uuid4()))

        return batch_text, batch_metadata, uuid_strings

    def __call__(self, chunks: List[Document],) -> None:
        """
        chunks: List[Document] = A list of chunked document to send to the VDB
        """
        for i in range(0, len(chunks), self.chunk_batch_size):
            batch_end = min(len(chunks), i + self.chunk_batch_size)
            batch = chunks[i:batch_end]

            batch_text, batch_metadata, uuid_strings = self._prepare_batch(batch)
            batch_embeddings = self.embeddings_inst(batch_text)
            self.upsert_to_index(uuid_strings, batch_embeddings, batch_metadata)
        print ("Succefully upserted documents to Pinecone")
