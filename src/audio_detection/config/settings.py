"""Production configuration settings for PandaMIND VPC deployment (PRD Milestone M5).

Handles:
- Host, port, worker settings
- Maximum upload size (50 MB) and audio duration limits
- Storage directories and data residency (ap-south-1 / India region)
- Retention policy (7-day default, zero-retention mode)
- API-key authentication and per-key operating point defaults
- Offline air-gapped VPC enforcement (zero external network dependency)
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


@dataclass
class Settings:
    """Production runtime settings."""
    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    log_level: str = "INFO"

    # Audio limits (PRD FR-1)
    max_file_size_bytes: int = 50 * 1024 * 1024  # 50 MB
    max_audio_duration_seconds: int = 300  # 5 minutes

    # Storage and Data Residency (PRD Section 08)
    temp_dir: Path = Path("./tmp")
    data_residency_region: str = "ap-south-1"  # AWS Mumbai / India local compliance
    storage_encryption_hook: str = "local_fs"  # integration boundary for customer KMS

    # Retention Policy (PRD 7-day requirement & zero-retention mode)
    retention_days: int = 7
    zero_retention_mode: bool = False

    # Security & Authentication (PRD NFR-6)
    api_key_auth_enabled: bool = False
    # Mapping of api_key -> default_operating_point
    api_keys: Dict[str, str] = field(default_factory=lambda: {
        "pm-prod-key-standard": "fpr_1pct",
        "pm-prod-key-highsecurity": "fpr_0.1pct",
        "pm-prod-key-triage": "fpr_5pct",
    })

    # Offline / VPC Deployment (PRD Milestone M5)
    offline_mode: bool = True
    scorer_backend: str = "m3"

    @classmethod
    def from_env(cls) -> Settings:
        """Loads settings from environment variables with safe defaults."""
        host = os.environ.get("HOST", "0.0.0.0")
        port = int(os.environ.get("PORT", "8000"))
        workers = int(os.environ.get("WORKERS", os.environ.get("WEB_CONCURRENCY", "1")))
        log_level = os.environ.get("LOG_LEVEL", "INFO").upper()

        max_size = int(os.environ.get("MAX_FILE_SIZE_BYTES", str(50 * 1024 * 1024)))
        max_duration = int(os.environ.get("MAX_AUDIO_DURATION_SECONDS", "300"))

        temp_dir = Path(os.environ.get("TEMP_DIR", "./tmp"))
        data_residency = os.environ.get("DATA_RESIDENCY_REGION", "ap-south-1")
        encryption_hook = os.environ.get("STORAGE_ENCRYPTION_HOOK", "local_fs")

        retention_days = int(os.environ.get("RETENTION_DAYS", "7"))
        zero_retention = os.environ.get("ZERO_RETENTION_MODE", "false").lower() in ("true", "1", "yes")

        auth_enabled = os.environ.get("API_KEY_AUTH_ENABLED", "false").lower() in ("true", "1", "yes")

        # Parse API keys if provided via JSON or comma-separated env
        api_keys_raw = os.environ.get("API_KEYS")
        if api_keys_raw:
            try:
                api_keys = json.loads(api_keys_raw)
            except Exception:
                # Comma separated list of keys defaulted to fpr_1pct
                api_keys = {k.strip(): "fpr_1pct" for k in api_keys_raw.split(",") if k.strip()}
        else:
            api_keys = {
                "pm-prod-key-standard": "fpr_1pct",
                "pm-prod-key-highsecurity": "fpr_0.1pct",
                "pm-prod-key-triage": "fpr_5pct",
            }

        offline_mode = os.environ.get("OFFLINE_MODE", "true").lower() in ("true", "1", "yes")
        backend = os.environ.get("SCORER_BACKEND", "m3").lower()

        return cls(
            host=host,
            port=port,
            workers=workers,
            log_level=log_level,
            max_file_size_bytes=max_size,
            max_audio_duration_seconds=max_duration,
            temp_dir=temp_dir,
            data_residency_region=data_residency,
            storage_encryption_hook=encryption_hook,
            retention_days=retention_days,
            zero_retention_mode=zero_retention,
            api_key_auth_enabled=auth_enabled,
            api_keys=api_keys,
            offline_mode=offline_mode,
            scorer_backend=backend,
        )


# Global settings singleton
settings = Settings.from_env()


def get_settings() -> Settings:
    """Returns the current settings."""
    return settings


def reload_settings() -> Settings:
    """Reloads settings from the environment."""
    global settings
    settings = Settings.from_env()
    return settings
