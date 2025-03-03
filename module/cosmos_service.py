from pymongo import MongoClient
import warnings
from module.utils import config
from module.utils import timing_decorator
from motor.motor_asyncio import AsyncIOMotorClient
from collections import defaultdict
import asyncio
from collections import deque
from typing import List

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
            config['production']['mongo_database']['connection_string']
        )
        return MongoClient(connection_string)

    def insert_one(self, document):
        self.collection.insert_one(document)

    def fetch_many(self, query):
        return self.collection.find(query)

    def fetch_one(self, query):
        return self.collection.find_one(query)


class AsyncCosmosClient:
    _cached_client = None  # 🔹 Cached MongoDB client
    _buffer = deque()  # 🔹 Buffer for batch inserts
    _buffer_lock = asyncio.Lock()  # 🔹 Lock to prevent race conditions

    def __init__(self, database_name: str, collection_name: str, buffer_size=30, flush_interval=900):
        self.database_name = database_name
        self.collection_name = collection_name
        self.BUFFER_SIZE = buffer_size  # 🔹 Max batch size before auto-flush
        self.FLUSH_INTERVAL = flush_interval  # 🔹 Flush every X seconds

        if not AsyncCosmosClient._cached_client:
            AsyncCosmosClient._cached_client = AsyncIOMotorClient(self._get_connection_string())

        self.client = AsyncCosmosClient._cached_client
        self.collection = self.client[self.database_name][self.collection_name]

        # Start the background flush task only once
        self._flush_task = asyncio.create_task(self._flush_loop())

    def _get_connection_string(self) -> str:
        return (
            config['production']['mongo_database']['connection_string']
        )

    async def insert_one(self, document):
        """Insert a single document into MongoDB (not recommended for high traffic)."""
        await self.collection.insert_one(document)

    async def fetch_many(self, query):
        """Fetch multiple documents matching the query."""
        cursor = self.collection.find(query)
        return await cursor.to_list(length=None)

    async def fetch_one(self, query):
        """Fetch a single document, excluding '_id' from results."""
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

    async def add_to_buffer(self, document: dict):
        """Add a document to the buffer for batch storage."""
        async with self._buffer_lock:
            self._buffer.append(document)
            print(f"🟡 Added document to buffer. Current size: {len(self._buffer)}")  # Debugging

            # 🔹 Logging when skipping storage (buffer not yet full)
            if len(self._buffer) < self.BUFFER_SIZE:
                print(f"🔸 Skipping storage: {len(self._buffer)}/{self.BUFFER_SIZE} messages buffered.")

            if len(self._buffer) >= self.BUFFER_SIZE:
                print("⚡ Buffer full! Flushing to database...")  # Debugging
                asyncio.get_event_loop().call_soon_threadsafe(asyncio.create_task, self.flush_to_db())
                # await self.flush_to_db()  # Flush immediately if full

    async def batch_insert(self, documents: List[dict]):
        """Bulk insert a batch of documents into MongoDB."""
        if documents:
            await self.collection.insert_many(documents)

    async def flush_to_db(self):
        """Flush the buffered chat history to MongoDB."""
        async with self._buffer_lock:
            if self._buffer:
                batch_data = list(self._buffer)
                self._buffer.clear()  # Clear buffer after reading

                try:
                    await self.batch_insert(batch_data)
                    print(f"✅ Flushed {len(batch_data)} messages to MongoDB")
                except Exception as e:
                    print(f"❌ Error flushing to MongoDB: {e}")

    async def _flush_loop(self):
        """Continuously flush chat history at fixed intervals."""
        while True:
            await asyncio.sleep(self.FLUSH_INTERVAL)
            await self.flush_to_db()

    async def on_shutdown(self):
        """Gracefully flush remaining data before shutting down."""
        print("⚠️ FastAPI is shutting down. Cancelling background flush task...")

        if hasattr(self, "_flush_task"):
            self._flush_task.cancel()  # Stop periodic flushing
            try:
                await self._flush_task  # Wait for it to exit cleanly
            except asyncio.CancelledError:
                print("✅ Background flush task successfully cancelled.")

        print("🔹 Flushing remaining messages before shutdown...")
        await self.flush_to_db()
        print("✅ All data safely stored. Shutting down.")
