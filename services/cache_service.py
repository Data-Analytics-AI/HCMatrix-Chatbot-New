import time
from collections import OrderedDict


class LRUCache:
    def __init__(self, capacity: int, ttl: int = 86400):
        self.ttl = ttl
        self.capacity = capacity
        self.cache = OrderedDict()
        self.entry_time = time.time()

    def get(self, key: int) -> int:
        if time.time() - self.entry_time > self.ttl:
            self.cache = OrderedDict()  # clear the list
            self.entry_time = time.time()
        if key not in self.cache:
            return -1
        else:
            self.cache.move_to_end(key)  # Move the accessed key to the end (most recently used)
            return self.cache[key]

    def put(self, key: int, value: int) -> None:
        if time.time() - self.entry_time > self.ttl:
            self.cache = OrderedDict()  # clear the list
            self.entry_time = time.time()
        if key in self.cache:
            self.cache.move_to_end(key)  # Update the value and move it to the end
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)  # Pop the first item (least recently used)

    def __repr__(self):
        return f"{self.cache}"


"""

import time
from collections import OrderedDict

class LRUCache:
    def __init__(self, capacity: int, ttl: int = 86400):
        self.ttl = ttl
        self.capacity = capacity
        self.cache = OrderedDict()  # Store items as (key: (value, timestamp))

    def _is_expired(self, key: int) -> bool:
        current_time = time.time()
        timestamp = self.cache[key][1]
        return (current_time - timestamp) > self.ttl

    def _remove_expired(self):
        keys_to_delete = []
        for key in list(self.cache.keys()):
            if self._is_expired(key):
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del self.cache[key]

    def get(self, key: int) -> int:
        self._remove_expired()  # Clear expired items before accessing
        if key not in self.cache:
            return -1
        else:
            # Move the accessed key to the end (most recently used)
            self.cache.move_to_end(key)
            return self.cache[key][0]  # Return the value only

    def put(self, key: int, value: int) -> None:
        self._remove_expired()  # Clear expired items before adding new ones
        if key in self.cache:
            # Update the value and move it to the end
            self.cache.move_to_end(key)
        self.cache[key] = (value, time.time())  # Store value with current timestamp
        if len(self.cache) > self.capacity:
            # Pop the first item (least recently used)
            self.cache.popitem(last=False)

    def __repr__(self):
        return f"{[(key, value[0]) for key, value in self.cache.items()]}"


"""
