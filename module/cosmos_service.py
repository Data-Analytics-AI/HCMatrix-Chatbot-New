from pymongo import MongoClient
import warnings
from module.utils import config
# from module.utils import timing_decorator
from motor.motor_asyncio import AsyncIOMotorClient
from collections import defaultdict
import asyncio
from collections import deque
from typing import List

warnings.filterwarnings("ignore")


class CosmosClient:
    """
    A singleton-style MongoDB client for interacting with a specific database and collection.

    This class ensures that only one connection is established to the MongoDB instance and reuses
    the same connection for all instances of the `CosmosClient`.

    Attributes:
        _cached_client (MongoClient): A class-level cached connection to MongoDB.
        database_name (str): The name of the database to connect to.
        collection_name (str): The name of the collection to interact with.
        client (MongoClient): An instance-level reference to the cached MongoDB client.
        collection (Collection): A reference to the specified MongoDB collection.

    Methods:
        insert_one(document: dict): Inserts a single document into the collection.
        fetch_many(query: dict): Retrieves multiple documents matching the query.
        fetch_one(query: dict): Retrieves a single document matching the query.
    """

    _cached_client = None  # 🔹 Class variable to store cached connection

    def __init__(self, database_name: str, collection_name: str):
        """
        Initializes the CosmosClient for a specific MongoDB database and collection.

        If no connection has been established yet, it initializes a new connection
        and caches it for future use.

        Args:
            database_name (str): The name of the MongoDB database.
            collection_name (str): The name of the MongoDB collection.
        """
        self.database_name = database_name
        self.collection_name = collection_name

        if not CosmosClient._cached_client:  # Create connection only once
            CosmosClient._cached_client = self._establish_connection()

        self.client = CosmosClient._cached_client
        self.collection = self.client[self.database_name][self.collection_name]

    def _establish_connection(self):
        """
        Establishes a connection to MongoDB using the connection string from the configuration.

        Returns:
            MongoClient: A MongoDB client instance.
        """
        connection_string = (
            config['production']['mongo_database']['connection_string']
        )
        return MongoClient(connection_string)

    def insert_one(self, document: dict):
        """
        Inserts a single document into the MongoDB collection.

        Args:
            document (dict): The document to insert.
        """
        self.collection.insert_one(document)

    def fetch_many(self, query: dict):
        """
        Retrieves multiple documents from the collection that match the query.

        Args:
            query (dict): A dictionary specifying the query conditions.

        Returns:
            Cursor: A cursor to iterate over the matching documents.
        """
        return self.collection.find(query)

    def fetch_one(self, query: dict):
        """
        Retrieves a single document from the collection that matches the query.

        Args:
            query (dict): A dictionary specifying the query conditions.

        Returns:
            dict or None: The first matching document, or None if no match is found.
        """
        return self.collection.find_one(query)


class AsyncCosmosClient:
    """
        An asynchronous MongoDB client for efficient batch inserts and data retrieval.
        This client supports buffering of documents before inserting them in bulk,
        reducing the number of direct database writes to improve performance.
        """
    _cached_client = None  # 🔹 Cached MongoDB client
    _buffer = deque()  # 🔹 Buffer for batch inserts
    _buffer_lock = asyncio.Lock()  # 🔹 Lock to prevent race conditions

    def __init__(self, database_name: str, collection_name: str, buffer_size=30, flush_interval=900):
        """
        Initializes the async MongoDB client and starts a background task for periodic flushing.

        :param database_name: Name of the MongoDB database.
        :param collection_name: Name of the collection to store/retrieve data.
        :param buffer_size: Maximum buffer size before auto-flush to MongoDB.
        :param flush_interval: Time interval (in seconds) for automatic flushing of the buffer.
            """
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
        """
        Retrieves the MongoDB connection string from configuration.

        :return: MongoDB's connection string.
            """
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
        """
        Fetches multiple documents and groups them by a specified key.

        :param query: Query dictionary to filter documents.
        :param group_key: Key to group results by (default is "chat_id").
        :return: Dictionary where keys are unique values of group_key, and values are lists of documents.
        """
        cursor = self.collection.find(query, {"_id": 0})
        documents = await cursor.to_list(length=None)
        grouped_results = defaultdict(list)
        for doc in documents:
            key_value = doc.get(group_key, "undefined")  # Default to 'undefined' if key is missing
            grouped_results[key_value].append(doc)
        return dict(grouped_results)

    async def add_to_buffer(self, document: dict):
        """
        Adds a document to the buffer for batch insertion.
        If the buffer reaches its defined capacity, it triggers an automatic flush.

        :param document: Document to be added to the buffer.
        """
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
        """
        Inserts multiple documents into MongoDB in a single operation.

        :param documents: List of dictionaries representing the documents to be inserted.
        """
        if documents:
            await self.collection.insert_many(documents)

    async def flush_to_db(self):
        """
        Flushes the buffered documents to MongoDB and clears the buffer after a successful insert.
        """
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
