import time
from collections import OrderedDict


class LRUCache:
    """
    Least Recently Used (LRU) cache with an optional Time-To-Live (TTL) mechanism.

    Attributes:
        ttl (int): The time-to-live (TTL) in seconds for cache entries. Default is 86400 seconds (24 hours).
        capacity (int): The maximum number of entries the cache can hold.
        cache (OrderedDict): Stores key-value pairs along with their timestamps in the format (key -> (value, timestamp)).

    Methods:
        get(key: int): Retrieves the value associated with a key if it exists and is not expired. Returns -1 otherwise.
        put(key: int, value: int): Adds or updates a key-value pair in the cache. Removes the least recently used entry if the capacity is exceeded.
        __repr__(): Returns a string representation of the cache contents.
    """

    def __init__(self, capacity: int, ttl: int = 86400):
        """
        Initializes the LRUCache with a specified capacity and TTL.

        Args:
            capacity (int): The maximum number of items the cache can hold.
            ttl (int, optional): The time-to-live (TTL) for cache entries in seconds. Default is 86400 seconds (24 hours).
        """
        self.ttl = ttl
        self.capacity = capacity
        self.cache = OrderedDict()  # Stores (key -> (value, timestamp))

    def _is_expired(self, key: int) -> bool:
        """
        Checks whether a cache entry is expired based on its timestamp.

        Args:
            key (int): The cache key to check.

        Returns:
            bool: True if the entry is expired or does not exist, False otherwise.
        """
        if key not in self.cache:
            return True
        _, timestamp = self.cache[key]
        return time.time() - timestamp > self.ttl

    def get(self, key: int):
        """
        Retrieves a value from the cache if it exists and is not expired.

        Args:
            key (int): The cache key to retrieve.

        Returns:
            int: The cached value if found and valid, otherwise -1.
        """
        if self._is_expired(key):
            self.cache.pop(key, None)  # Remove stale entry if expired
            return -1
        self.cache.move_to_end(key)  # Mark as recently used
        return self.cache[key][0]  # Return only the value

    def put(self, key: int, value: int) -> None:
        """
        Inserts a new key-value pair into the cache or updates an existing one.

        If the key exists but is expired, it is removed before inserting a new value.
        If the cache exceeds its capacity, the least recently used item is evicted.

        Args:
            key (int): The cache key to insert or update.
            value (int): The value to store in the cache.
        """
        if key in self.cache and self._is_expired(key):
            self.cache.pop(key)  # Remove expired entry before adding a new one

        self.cache[key] = (value, time.time())  # Store value with timestamp
        self.cache.move_to_end(key)  # Mark as recently used

        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)  # Remove the least recently used item

    def __repr__(self):
        """
        Returns a string representation of the cache, displaying the keys and their values.

        Returns:
            str: A string representation of the cache contents.
        """
        return f"{[(key, value[0]) for key, value in self.cache.items()]}"
