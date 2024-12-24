

from pinecone import Pinecone, ServerlessSpec
from typing import *
import time
from module.utils import config

pinecone_configs = config['production']['pinecone_credentials']
specs = config['production']['pinecone_credentials']['specs']

class PineconeDB:

    """
    ### PineconeDB Engine
    This context manager deals with everything related to pinecone connection, querying and closing.

    ##### NOTE: Samu, a context manger should be used here as its a resources we trying to manage here.
    Do it when you're chanced
    """

    def __init__(self) -> None:

        self.index_name = pinecone_configs['index_name']
        self.index_metric = pinecone_configs['index_metric']
        self.pc = Pinecone(api_key=pinecone_configs['PINECONE_API_KEY'],)

        try:
            if self.index_name not in self.pc.list_indexes():
                self.pc.create_index(
                    name = self.index_name,
                    spec = ServerlessSpec(cloud=specs['cloud'], region=specs['region']),
                    dimension= pinecone_configs['embedding_dim'],
                    metric = self.index_metric,
                )

                # wait for the index to finish initilization
                while not self.pc.describe_index(self.index_name).status['ready']:
                    time.sleep(1)

                # print (self.pc.describe_index(self.index_name))
        except Exception as reason:
            print (reason)

        self.host = self.pc.describe_index(self.index_name).host
        self.index = self.init_index()


    def init_index(self, ) -> Any:
        for _ in range(2):
            try:
                index = self.pc.Index(
                    self.index_name,
                    self.host)
                print (index.describe_index_stats())
                return index
            except Exception as reason:
                print (f"An Error Occured reasons due to {reason}")


    def upsert_to_index(self, id: List[str], embeddings: List[Any], metadata: List[Dict], namespace: Optional[str] = None,) -> None:
        self.index.upsert(
            vectors = zip(id, embeddings, metadata), # append user id as document id to metadata
            namespace = namespace# namespace should correspond to the pdf file
        )

    def query_vectors(
        self, text: str, top_k: int = 3, embedding_model: Optional[Any] = None,
        filters: Optional[Dict] = None, namespace: Optional[str] = None,):

        if embedding_model:
            vectors = embedding_model.embed_documents(text)
            results = self.index.query(
                namespace=namespace,
                vectors=vectors,
                top_k = top_k,
                filter=filters,
                include_values=False,
                include_metadata=True,
            )

            return results

    def fetch_from_id(self, id: str):
        return self.index.fetch(id)

    def delete_index(self,):
        self.pc.delete_index(self.index_name)