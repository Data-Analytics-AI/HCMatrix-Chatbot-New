from pymongo import MongoClient
import warnings
from module.utils import timing_decorator
from motor.motor_asyncio import AsyncIOMotorClient
from collections import defaultdict

warnings.filterwarnings("ignore")


class CosmosClient:
    _cached_client = None  # 🔹 Class variable to store cached connection

    def __init__(self, database_name, collection_name):
        self.database_name = database_name
        self.collection_name = collection_name

        if not CosmosClient._cached_client:  # Create connection only once
            CosmosClient._cached_client = self._establish_connection()

        self.client = CosmosClient._cached_client
        self.collection = self.client[self.database_name][self.collection_name]

    def _establish_connection(self):
        connection_string = (
            "mongodb://hcmatrix-cosmos"
            ":FQwuYHLYfp3whgnG6tkbCCIzSd17RGcS5LXm6YZbI9CazFjWRVHFoy0sFQjgjiEc5Ya4SzkOajCTACDbiqVKXA=="
            "@hcmatrix-cosmos.mongo.cosmos.azure.com:10255/?ssl=true&retrywrites=false&replicaSet=globaldb"
            "&maxIdleTimeMS=120000&appName=@hcmatrix-cosmos@"
        )
        return MongoClient(connection_string)

    def insert_one(self, document):
        self.collection.insert_one(document)

    def fetch_many(self, query):
        return self.collection.find(query)

    def fetch_one(self, query):
        return self.collection.find_one(query)


class AsyncCosmosClient:
    _cached_client = None  # 🔹 Class variable for cached connection

    def __init__(self, database_name: str, collection_name: str):
        self.database_name = database_name
        self.collection_name = collection_name

        if not AsyncCosmosClient._cached_client:  # Create connection only once
            AsyncCosmosClient._cached_client = AsyncIOMotorClient(self._get_connection_string())

        self.client = AsyncCosmosClient._cached_client
        self.collection = self.client[self.database_name][self.collection_name]

    def _get_connection_string(self) -> str:
        return (
            "mongodb://hcmatrix-cosmos"
            ":FQwuYHLYfp3whgnG6tkbCCIzSd17RGcS5LXm6YZbI9CazFjWRVHFoy0sFQjgjiEc5Ya4SzkOajCTACDbiqVKXA=="
            "@hcmatrix-cosmos.mongo.cosmos.azure.com:10255/?ssl=true&retrywrites=false&replicaSet=globaldb"
            "&maxIdleTimeMS=120000&appName=@hcmatrix-cosmos@"
        )

    @timing_decorator
    async def insert_one(self, document):
        await self.collection.insert_one(document)

    async def fetch_many(self, query):
        cursor = self.collection.find(query)
        return await cursor.to_list(length=None)

    async def fetch_one(self, query):
        return await self.collection.find_one(query, {"_id": 0})

    async def fetch_and_group_by_key(self, query, group_key="chat_id"):
        """Fetch multiple documents and group them by a specified key."""
        cursor = self.collection.find(query, {"_id": 0})
        documents = await cursor.to_list(length=None)
        grouped_results = defaultdict(list)
        for doc in documents:
            key_value = doc.get(group_key, "undefined")  # Default to 'undefined' if key is missing
            grouped_results[key_value].append(doc)
        return dict(grouped_results)
