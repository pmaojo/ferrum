"""Simple cachetools stub used for tests."""

class TTLCache(dict):
    def __init__(self, maxsize=128, ttl=300):
        super().__init__()
        self.maxsize = maxsize
        self.ttl = ttl
        self._store = {}
    def clear(self):
        self._store.clear()
    def __setitem__(self, key, value):
        if len(self._store) >= self.maxsize:
            self._store.pop(next(iter(self._store)))
        self._store[key] = (value, 0)
    def __getitem__(self, key):
        return self._store[key][0]
    def __len__(self):
        return len(self._store)
