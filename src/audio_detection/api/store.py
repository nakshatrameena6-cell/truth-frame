"""In-memory Job Store for PandaMIND with retention policy management (PRD Milestone M5).

Provides:
- Thread-safe, deterministic storage for scoring jobs
- Timestamp tracking for PRD 7-day retention enforcement
- Automatic purge of expired jobs
- Zero-retention mode compliance
"""
from __future__ import annotations

import threading
import time
from typing import Dict, List, Optional, Tuple

from .schemas import ScoreResponse


class InMemoryJobStore:
    """Thread-safe store mapping job_id to ScoreResponse with retention management."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._store: Dict[str, ScoreResponse] = {}
        self._timestamps: Dict[str, float] = {}

    def save_job(self, job_id: str, response: ScoreResponse) -> None:
        with self._lock:
            self._store[job_id] = response
            self._timestamps[job_id] = time.time()

    def get_job(self, job_id: str) -> Optional[ScoreResponse]:
        with self._lock:
            return self._store.get(job_id)

    def delete_job(self, job_id: str) -> bool:
        with self._lock:
            self._timestamps.pop(job_id, None)
            if job_id in self._store:
                del self._store[job_id]
                return True
            return False

    def purge_expired_jobs(self, max_age_seconds: float = 7 * 86400) -> int:
        """Purges jobs older than max_age_seconds (default 7 days per PRD)."""
        now = time.time()
        purged = 0
        with self._lock:
            expired_ids = [
                jid for jid, created_at in self._timestamps.items()
                if (now - created_at) > max_age_seconds
            ]
            for jid in expired_ids:
                self._store.pop(jid, None)
                self._timestamps.pop(jid, None)
                purged += 1
        return purged

    def get_job_age_seconds(self, job_id: str) -> Optional[float]:
        with self._lock:
            t = self._timestamps.get(job_id)
            return (time.time() - t) if t else None

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._timestamps.clear()

    def count(self) -> int:
        with self._lock:
            return len(self._store)


# Global singleton instance for the process
job_store = InMemoryJobStore()
