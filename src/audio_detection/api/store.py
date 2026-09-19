"""In-memory Job Store for PandaMIND M1.

Provides a thread-safe, deterministic in-memory store for asynchronous scoring jobs.
For production (M5+), this will be replaced with persistent storage (e.g. Postgres / Redis).
"""
from __future__ import annotations

import threading
from typing import Dict, Optional

from .schemas import ScoreResponse


class InMemoryJobStore:
    """Thread-safe in-memory store mapping job_id to completed or in-flight ScoreResponse."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._store: Dict[str, ScoreResponse] = {}

    def save_job(self, job_id: str, response: ScoreResponse) -> None:
        with self._lock:
            self._store[job_id] = response

    def get_job(self, job_id: str) -> Optional[ScoreResponse]:
        with self._lock:
            return self._store.get(job_id)

    def delete_job(self, job_id: str) -> bool:
        with self._lock:
            if job_id in self._store:
                del self._store[job_id]
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def count(self) -> int:
        with self._lock:
            return len(self._store)


# Global singleton instance for the process
job_store = InMemoryJobStore()
