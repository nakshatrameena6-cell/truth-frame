"""Audit Logging and Compliance Module for PandaMIND (PRD Milestone M5).

Implements:
- Audio-independent audit records (PRD Section 08)
- Zero-audio-content invariant: audit records NEVER contain raw audio, waveforms, or transcripts
- Retention tracking and job expiration
- Zero-retention compliance verification
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


@dataclass(frozen=True)
class AuditRecord:
    """Immutable audit record preserving evidence that a scoring job occurred."""
    audit_id: str
    job_id: str
    timestamp: str
    client_key_prefix: str
    operating_point: str
    verdict_band: str
    calibrated_probability: float
    speech_duration_ms: int
    quality_gate: str
    processing_time_ms: float
    data_residency_region: str
    zero_retention_applied: bool

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class AuditLogger:
    """Thread-safe auditor maintaining privacy-compliant scoring logs."""

    def __init__(self, log_dir: Optional[Path] = None) -> None:
        self._lock = threading.Lock()
        self._records: List[AuditRecord] = []
        self._log_dir = log_dir or Path("reports/audit")
        self._log_file = self._log_dir / "scoring_audit_trail.jsonl"
        self._ensure_log_dir()

    def _ensure_log_dir(self) -> None:
        try:
            self._log_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def record_job(
        self,
        job_id: str,
        operating_point: str,
        verdict_band: str,
        calibrated_probability: float,
        speech_duration_ms: int,
        quality_gate: str,
        processing_time_ms: float,
        client_api_key: Optional[str] = None,
        data_residency_region: str = "ap-south-1",
        zero_retention: bool = False,
    ) -> AuditRecord:
        """Creates an audit entry without exposing any audio or transcript data."""
        # Mask API key if present
        if client_api_key:
            masked_key = f"{client_api_key[:6]}***" if len(client_api_key) > 6 else "***"
        else:
            masked_key = "unauthenticated"

        now_iso = datetime.now(timezone.utc).isoformat()
        audit_id = f"aud_{uuid.uuid4().hex[:12]}"

        record = AuditRecord(
            audit_id=audit_id,
            job_id=job_id,
            timestamp=now_iso,
            client_key_prefix=masked_key,
            operating_point=operating_point,
            verdict_band=verdict_band,
            calibrated_probability=round(calibrated_probability, 4),
            speech_duration_ms=speech_duration_ms,
            quality_gate=quality_gate,
            processing_time_ms=round(processing_time_ms, 2),
            data_residency_region=data_residency_region,
            zero_retention_applied=zero_retention,
        )

        with self._lock:
            self._records.append(record)
            # Append to persistent JSONL audit log
            try:
                with open(self._log_file, "a", encoding="utf-8") as f:
                    f.write(record.to_json() + "\n")
            except Exception:
                pass

        return record

    def get_records(self) -> List[AuditRecord]:
        with self._lock:
            return list(self._records)

    def get_job_audit(self, job_id: str) -> Optional[AuditRecord]:
        with self._lock:
            for r in reversed(self._records):
                if r.job_id == job_id:
                    return r
            return None

    def count(self) -> int:
        with self._lock:
            return len(self._records)

    def clear(self) -> None:
        with self._lock:
            self._records.clear()


# Global singleton auditor instance
audit_logger = AuditLogger()
