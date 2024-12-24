from pymongo import MongoClient
from typing import *
import warnings

warnings.filterwarnings("ignore")


class CosmosClient:
    def __init__(self, database_name, collection_name):
        self.database_name = database_name
        self.collection_name = collection_name
        self.client = None
        self.collection = None

    def __enter__(self):
        self.client = self._establish_connection()
        self.collection = self.client[self.database_name][self.collection_name]
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._close_connection()

    def _establish_connection(self):
        connection_string = (
            "mongodb://hcmatrix-cosmos"
            ":FQwuYHLYfp3whgnG6tkbCCIzSd17RGcS5LXm6YZbI9CazFjWRVHFoy0sFQjgjiEc5Ya4SzkOajCTACDbiqVKXA=="
            "@hcmatrix-cosmos.mongo.cosmos.azure.com:10255/?ssl=true&retrywrites=false&replicaSet=globaldb"
            "&maxIdleTimeMS=120000&appName=@hcmatrix-cosmos@"
        )
        return MongoClient(connection_string)

    def _close_connection(self):
        if self.client:
            self.client.close()

    def insert_one(self, document):
        self.collection.insert_one(document)

    def fetch_many(self, query):
        return self.collection.find(query)

    def fetch_one(self, query: Dict = {}):
        return self.collection.find_one(query)
