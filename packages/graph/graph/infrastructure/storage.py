from __future__ import annotations

from abc import abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, Optional, Protocol, Tuple
import json
import time
import uuid

from sqlalchemy import Column, DateTime, String
from sqlalchemy.orm import Session, declarative_base, sessionmaker



class CacheProtocol(Protocol):
    """Simple key-value cache interface."""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Retrieve a value from cache if present and not expired."""

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Store a value with optional time-to-live in seconds."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove a key from the cache."""

    @abstractmethod
    def clear(self) -> None:
        """Remove all items from the cache."""


class JobRepository(Protocol):
    """Persistence interface for asynchronous job records.

    Job dictionaries typically contain at minimum ``job_id``, ``status``,
    timestamps, and may optionally include a ``task_id`` for queued Celery
    tasks.
    """

    @abstractmethod
    def add(self, job: Dict[str, Any]) -> None:
        """Persist a new job."""

    @abstractmethod
    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a job by identifier."""

    @abstractmethod
    def update(self, job: Dict[str, Any]) -> None:
        """Update an existing job."""

    @abstractmethod
    def delete(self, job_id: str) -> None:
        """Delete a job."""

    @abstractmethod
    def list(self, tenant_id: Optional[str] = None) -> Iterator[Dict[str, Any]]:
        """Iterate over jobs, optionally filtered by tenant."""


class InMemoryCache(CacheProtocol):
    """Thread-unsafe in-memory cache for tests and local use."""

    def __init__(self) -> None:
        self._store: Dict[str, Tuple[Any, Optional[float]]] = {}

    def get(self, key: str) -> Optional[Any]:
        item = self._store.get(key)
        if not item:
            return None
        value, expires_at = item
        if expires_at is not None and expires_at < time.time():
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        expires_at = time.time() + ttl if ttl is not None else None
        self._store[key] = (value, expires_at)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()

    def __len__(self) -> int:
        return len(self._store)


class InMemoryJobRepository(JobRepository):
    """Thread-safe in-memory implementation of ``JobRepository``."""

    def __init__(self) -> None:
        self._jobs: Dict[str, Dict[str, Any]] = {}

    def add(self, job: Dict[str, Any]) -> None:
        self._jobs[job["job_id"]] = job

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self._jobs.get(job_id)

    def update(self, job: Dict[str, Any]) -> None:
        if job["job_id"] not in self._jobs:
            raise KeyError(f"Job {job['job_id']} not found")
        self._jobs[job["job_id"]] = job

    def delete(self, job_id: str) -> None:
        self._jobs.pop(job_id, None)

    def list(self, tenant_id: Optional[str] = None) -> Iterator[Dict[str, Any]]:
        if tenant_id is None:
            return iter(self._jobs.values())
        return (job for job in self._jobs.values() if job.get("tenant_id") == tenant_id)

    def __len__(self) -> int:
        return len(self._jobs)


class RedisJobRepository(JobRepository):
    """Redis-backed implementation of :class:`JobRepository`."""

    def __init__(self, url: str, prefix: str = "job:") -> None:
        import redis
        self._client = redis.Redis.from_url(url, decode_responses=True)
        self._prefix = prefix

    def _key(self, job_id: str) -> str:
        return f"{self._prefix}{job_id}"

    def add(self, job: Dict[str, Any]) -> None:
        self._client.set(self._key(job["job_id"]), json.dumps(job))

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        data = self._client.get(self._key(job_id))
        return json.loads(data) if data else None

    def update(self, job: Dict[str, Any]) -> None:
        self._client.set(self._key(job["job_id"]), json.dumps(job))

    def delete(self, job_id: str) -> None:
        self._client.delete(self._key(job_id))

    def list(self, tenant_id: Optional[str] = None) -> Iterator[Dict[str, Any]]:
        for key in self._client.scan_iter(f"{self._prefix}*"):
            data = self._client.get(key)
            if not data:
                continue
            job = json.loads(data)
            if tenant_id is None or job.get("tenant_id") == tenant_id:
                yield job


Base = declarative_base()


class RepositoryIngestionModel(Base):
    """SQLAlchemy model for repository_ingestions table."""

    __tablename__ = "repository_ingestions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repo_id = Column(String(255), nullable=False)
    tenant_id = Column(String(36), nullable=False)
    status = Column(String(20), nullable=False)
    result_path = Column(String(255), nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class SQLAlchemyIngestionRepository(JobRepository):
    """Persist ingestion jobs to a SQL database."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self._cache: Dict[str, Dict[str, Any]] = {}

    def add(self, job: Dict[str, Any]) -> None:
        self._cache[job["job_id"]] = job
        model = RepositoryIngestionModel(
            id=job["job_id"],
            repo_id=job["repo_id"],
            tenant_id=job["tenant_id"],
            status=job["status"],
            result_path=job.get("result_path"),
            created_at=datetime.fromtimestamp(job["created_at"], tz=timezone.utc),
            updated_at=datetime.fromtimestamp(job["updated_at"], tz=timezone.utc),
        )
        self.session.add(model)
        self.session.commit()

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        job = self._cache.get(job_id)
        if job:
            return job
        model: RepositoryIngestionModel | None = (
            self.session.get(RepositoryIngestionModel, job_id)
        )
        if not model:
            return None
        job = {
            "job_id": model.id,
            "repo_id": model.repo_id,
            "tenant_id": model.tenant_id,
            "status": model.status,
            "progress": 0.0,
            "created_at": model.created_at.timestamp(),
            "updated_at": model.updated_at.timestamp(),
            "result_path": model.result_path,
            "result": None,
            "error": None,
            "task_id": None,
        }
        self._cache[job_id] = job
        return job

    def update(self, job: Dict[str, Any]) -> None:
        self._cache[job["job_id"]] = job
        model: RepositoryIngestionModel | None = (
            self.session.get(RepositoryIngestionModel, job["job_id"])
        )
        if not model:
            raise KeyError(f"Job {job['job_id']} not found")
        model.status = job["status"]
        model.result_path = job.get("result_path")
        model.updated_at = datetime.fromtimestamp(job["updated_at"], tz=timezone.utc)
        self.session.commit()

    def delete(self, job_id: str) -> None:
        self._cache.pop(job_id, None)
        model: RepositoryIngestionModel | None = (
            self.session.get(RepositoryIngestionModel, job_id)
        )
        if model:
            self.session.delete(model)
            self.session.commit()

    def list(self, tenant_id: Optional[str] = None) -> Iterator[Dict[str, Any]]:
        query = self.session.query(RepositoryIngestionModel)
        if tenant_id is not None:
            query = query.filter_by(tenant_id=tenant_id)
        for model in query.all():
            yield {
                "job_id": model.id,
                "repo_id": model.repo_id,
                "tenant_id": model.tenant_id,
                "status": model.status,
                "progress": 0.0,
                "created_at": model.created_at.timestamp(),
                "updated_at": model.updated_at.timestamp(),
                "result_path": model.result_path,
                "result": None,
                "error": None,
                "task_id": None,
            }
