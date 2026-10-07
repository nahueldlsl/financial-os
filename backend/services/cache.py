"""
TTLCache: Cache con Time-To-Live y tamaño máximo (LRU eviction).
Reemplaza los dicts globales sin límite que causan memory leaks.
"""
from collections import OrderedDict
from datetime import datetime, timedelta
import threading


class TTLCache:
    """Cache con TTL y tamaño máximo (LRU eviction) thread-safe."""

    def __init__(self, maxsize: int = 100, ttl_seconds: int = 3600):
        self._cache: OrderedDict = OrderedDict()
        self._maxsize = maxsize
        self._ttl = timedelta(seconds=ttl_seconds)
        self._lock = threading.RLock()

    def get(self, key):
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if datetime.now() - entry['time'] < self._ttl:
                    self._cache.move_to_end(key)  # Mark as recently used (LRU)
                    return entry['data']
                # Expired
                del self._cache[key]
            return None

    def set(self, key, data):
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self._cache[key] = {'time': datetime.now(), 'data': data}
            else:
                if len(self._cache) >= self._maxsize:
                    self._cache.popitem(last=False)  # Evict oldest
                self._cache[key] = {'time': datetime.now(), 'data': data}

    def clear(self):
        with self._lock:
            self._cache.clear()

    def __len__(self):
        with self._lock:
            return len(self._cache)

    def __contains__(self, key):
        """Check if key exists and is not expired."""
        with self._lock:
            return self.get(key) is not None
