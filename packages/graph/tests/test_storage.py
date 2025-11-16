import time
from infrastructure.storage import (
    InMemoryCache,
    InMemoryJobRepository,
)


def test_inmemory_cache_basic():
    cache = InMemoryCache()
    cache.set("a", 1)
    assert cache.get("a") == 1
    cache.delete("a")
    assert cache.get("a") is None
    cache.set("b", 2)
    cache.clear()
    assert cache.get("b") is None


def test_inmemory_cache_ttl():
    cache = InMemoryCache()
    cache.set("a", 1, ttl=0)
    assert cache.get("a") is None


def test_inmemory_job_store_crud():
    store = InMemoryJobRepository()
    job = {"job_id": "1", "tenant_id": "t", "status": "queued", "progress": 0.0}
    store.add(job)
    assert store.get("1") == job
    job["status"] = "running"
    store.update(job)
    assert store.get("1")["status"] == "running"
    assert list(store.list("t"))[0]["job_id"] == "1"
    store.delete("1")
    assert store.get("1") is None
