import time
from collections import OrderedDict


class LRUCache:
    def __init__(self, capacity: int, ttl: int = 86400):
        self.ttl = ttl
        self.capacity = capacity
        self.cache = OrderedDict()  # Stores (key -> (value, timestamp))

    def _is_expired(self, key: int) -> bool:
        """Check if a cache entry is expired."""
        if key not in self.cache:
            return True
        _, timestamp = self.cache[key]
        return time.time() - timestamp > self.ttl

    def get(self, key: int):
        """Retrieve value if it's in the cache and not expired, else return -1."""
        if self._is_expired(key):
            self.cache.pop(key, None)  # Remove stale entry if expired
            return -1
        self.cache.move_to_end(key)  # Mark as recently used
        return self.cache[key][0]  # Return only the value

    def put(self, key: int, value: int) -> None:
        """Insert or update cache with a new value and timestamp."""
        if key in self.cache and self._is_expired(key):
            self.cache.pop(key)  # Remove expired entry before adding a new one

        self.cache[key] = (value, time.time())  # Store value with timestamp
        self.cache.move_to_end(key)  # Mark as recently used

        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)  # Remove the least recently used item

    def __repr__(self):
        """Return a string representation of the cache with expiry times."""
        return f"{[(key, value[0]) for key, value in self.cache.items()]}"
