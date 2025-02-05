from pymongo import MongoClient
import warnings
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Dict, List

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


class AsyncCosmosClient:
    def __init__(self, database_name: str, collection_name: str):
        """Initialize an async MongoDB client using motor."""
        self.database_name = database_name
        self.collection_name = collection_name
        self.client = AsyncIOMotorClient(self._get_connection_string())
        self.collection = self.client[self.database_name][self.collection_name]

    def _get_connection_string(self) -> str:
        """Return MongoDB connection string."""
        return (
            "mongodb://hcmatrix-cosmos"
            ":FQwuYHLYfp3whgnG6tkbCCIzSd17RGcS5LXm6YZbI9CazFjWRVHFoy0sFQjgjiEc5Ya4SzkOajCTACDbiqVKXA=="
            "@hcmatrix-cosmos.mongo.cosmos.azure.com:10255/?ssl=true&retrywrites=false&replicaSet=globaldb"
            "&maxIdleTimeMS=120000&appName=@hcmatrix-cosmos@"
        )

    async def insert_one(self, document: Dict):
        """Insert a document asynchronously."""
        await self.collection.insert_one(document)

    async def fetch_many(self, query: Dict) -> List[Dict]:
        """Fetch multiple documents asynchronously."""
        cursor = self.collection.find(query)
        return await cursor.to_list(length=100)  # Convert cursor to list

    async def fetch_one(self, query: Dict = {}) -> Dict:
        """Fetch a single document asynchronously."""
        return await self.collection.find_one(query)
