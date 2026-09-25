"""FastAPI Application for PandaMIND M1 Audio Scoring API.

Endpoints:
  POST /v1/audio/score          -> Submit audio for scoring, returns 202 with job_id
  GET  /v1/audio/score/{job_id} -> Retrieve complete PRD verdict & evidence
  GET  /health                  -> Service health check
"""
from __future__ import annotations

import os
import time
import uuid
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, Request, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from audio_detection.config.settings import get_settings
from .audit import audit_logger
from .metrics import metrics_collector
from .schemas import (
    ApiErrorResponse,
    JobStatus,
    OperatingPoint,
    ScoreJobResponse,
    ScoreResponse,
)
from .service import scoring_engine
from .store import job_store
from .stub import STUB_MODEL_VERSION, compute_stub_score

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB per PRD FR-1
SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".opus", ".amr"}
VALID_OPERATING_POINTS = {op.value for op in OperatingPoint}

app = FastAPI(
    title="PandaMIND Audio Scoring API",
    version="1.0.0",
    description="Offline Content Trust Stack Audio Scoring API — VPC Production Ready",
    docs_url="/docs",
    redoc_url="/redoc",
)


class ApiException(HTTPException):
    """Custom API exception with structured error code and details."""

    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        details: Optional[dict] = None,
    ):
        super().__init__(status_code=status_code, detail=message)
        self.error_code = error_code
        self.message = message
        self.details = details


# =====================================================================
# Authentication & Security Helpers
# =====================================================================

def extract_api_key(request: Request) -> Optional[str]:
    """Extracts API key from X-API-Key or Bearer Authorization header."""
    key = request.headers.get("X-API-Key")
    if not key:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.lower().startswith("bearer "):
            key = auth_header[7:].strip()
    return key


def authenticate_request(request: Request) -> Optional[str]:
    """Validates API key if authentication is enabled in settings."""
    cfg = get_settings()
    key = extract_api_key(request)
    if cfg.api_key_auth_enabled:
        if not key or key not in cfg.api_keys:
            metrics_collector.record_validation_error()
            raise ApiException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                error_code="UNAUTHORIZED",
                message="Valid API key required. Provide 'X-API-Key' or 'Authorization: Bearer <key>'.",
                details={"auth_header_checked": ["X-API-Key", "Authorization"]},
            )
    return key


# =====================================================================
# Error Handlers
# =====================================================================

@app.exception_handler(ApiException)
async def api_exception_handler(request: Request, exc: ApiException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiErrorResponse(
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details,
        ).model_dump(),
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    code_map = {
        status.HTTP_400_BAD_REQUEST: "INVALID_REQUEST",
        status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
        status.HTTP_403_FORBIDDEN: "FORBIDDEN",
        status.HTTP_404_NOT_FOUND: "NOT_FOUND",
        status.HTTP_405_METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
        413: "FILE_TOO_LARGE",
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: "UNSUPPORTED_AUDIO",
        status.HTTP_500_INTERNAL_SERVER_ERROR: "INTERNAL_ERROR",
    }
    error_code = code_map.get(exc.status_code, "REQUEST_ERROR")
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiErrorResponse(
            error_code=error_code,
            message=str(exc.detail),
            details=None,
        ).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    metrics_collector.record_validation_error()
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ApiErrorResponse(
            error_code="INVALID_REQUEST",
            message="Malformed request parameters or body.",
            details={"errors": exc.errors()},
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    metrics_collector.record_job_failure()
    # Strictly prevent leaking internal stack traces or filesystem paths (PRD NFR-6)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ApiErrorResponse(
            error_code="INTERNAL_ERROR",
            message="An unexpected internal server error occurred while processing the request.",
            details=None,
        ).model_dump(),
    )


# =====================================================================
# Endpoints
# =====================================================================

def get_scorer_backend() -> str:
    return os.environ.get("SCORER_BACKEND", "m3").lower()


def get_model_version() -> str:
    backend = get_scorer_backend()
    if backend in ("stub", "m1", "m1-stub"):
        return STUB_MODEL_VERSION
    return scoring_engine.detector.model_version


@app.get("/health", tags=["Health"])
@app.get("/v1/health", tags=["Health"])
async def health_check():
    """Health check verifying API readiness, model version, and VPC residency compliance."""
    cfg = get_settings()
    return {
        "status": "ok",
        "service": "pandamind-audio-scoring",
        "version": "1.0.0",
        "model_version": get_model_version(),
        "offline_mode": cfg.offline_mode,
        "data_residency_region": cfg.data_residency_region,
        "retention_policy": "zero_retention" if cfg.zero_retention_mode else f"{cfg.retention_days}_days",
        "auth_enabled": cfg.api_key_auth_enabled,
    }


@app.get(
    "/v1/metrics",
    tags=["Observability"],
    summary="Retrieve production operational metrics without exposing audio content",
)
async def get_metrics(request: Request):
    """Exposes operational counters, latency percentiles, and drift monitoring summary."""
    authenticate_request(request)
    return metrics_collector.get_summary(model_version=get_model_version())


@app.post(
    "/v1/audio/score",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ScoreJobResponse,
    tags=["Scoring"],
    summary="Submit audio for synthetic speech scoring",
)
async def score_audio(
    request: Request,
    file: Optional[UploadFile] = File(None, description="Audio file upload (WAV, FLAC, MP3, OGG, Opus, AMR-NB)"),
    audio: Optional[UploadFile] = File(None, description="Alternative field name for audio file"),
    operating_point: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    query_op: Optional[str] = Query(None, alias="operating_point"),
    query_lang: Optional[str] = Query(None, alias="language"),
):
    """Submits an audio file for scoring.

    Returns HTTP 202 Accepted with a unique job_id.
    """
    t0 = time.perf_counter()
    metrics_collector.record_request()
    cfg = get_settings()

    # 1. API Key Authentication & Per-Key Operating Point Resolution
    client_key = authenticate_request(request)
    key_default_op = cfg.api_keys.get(client_key) if client_key else None

    # 2. Resolve uploaded file (accept either 'file' or 'audio' field)
    upload = file or audio
    if upload is None or not upload.filename:
        metrics_collector.record_validation_error()
        raise ApiException(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="MISSING_AUDIO",
            message="Required audio file is missing. Please provide a file under form field 'file' or 'audio'.",
        )

    # 3. Resolve operating_point and language
    # Priority: form field > query param > per-key default > global default ('fpr_1pct')
    raw_op = operating_point or query_op or key_default_op or "fpr_1pct"
    effective_lang = language or query_lang

    try:
        from audio_detection.calibration import normalize_operating_point
        effective_op = normalize_operating_point(raw_op)
    except Exception:
        metrics_collector.record_validation_error()
        raise ApiException(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="INVALID_REQUEST",
            message=f"Invalid operating_point '{raw_op}'. Supported values are: {sorted(list(VALID_OPERATING_POINTS))}.",
            details={"allowed": sorted(list(VALID_OPERATING_POINTS)), "received": raw_op},
        )

    # 4. Extension / Format validation (PRD FR-1)
    filename = upload.filename or "audio.wav"
    _, ext = os.path.splitext(filename.lower())
    if ext not in SUPPORTED_EXTENSIONS:
        metrics_collector.record_validation_error()
        raise ApiException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            error_code="UNSUPPORTED_AUDIO",
            message=f"Unsupported audio format '{ext or 'unknown'}'. Expected one of: {sorted(list(SUPPORTED_EXTENSIONS))}.",
            details={"supported_formats": sorted(list(SUPPORTED_EXTENSIONS)), "received_format": ext},
        )

    # 5. Read audio content & validate size (PRD FR-1: max 50 MB)
    content = await upload.read()

    if len(content) == 0:
        metrics_collector.record_validation_error()
        raise ApiException(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="EMPTY_AUDIO",
            message="Uploaded audio file is empty (0 bytes).",
        )

    if len(content) > cfg.max_file_size_bytes:
        metrics_collector.record_validation_error()
        raise ApiException(
            status_code=413,
            error_code="FILE_TOO_LARGE",
            message=f"The audio file exceeds the maximum allowed size of 50 MB (received {len(content)} bytes).",
            details={"max_size_bytes": cfg.max_file_size_bytes, "received_size_bytes": len(content)},
        )

    # 6. Generate stable, unique job identifier
    job_id = f"scr_{uuid.uuid4().hex[:10]}"

    # 7. Compute scoring result
    backend = get_scorer_backend()
    try:
        if backend in ("stub", "m1", "m1-stub"):
            response = compute_stub_score(
                audio_bytes=content,
                job_id=job_id,
                operating_point=effective_op,
                language=effective_lang,
                filename=filename,
            )
        else:
            response = scoring_engine.score_audio(
                audio_bytes=content,
                job_id=job_id,
                operating_point=effective_op,
                language=effective_lang,
                filename=filename,
            )
    except Exception as exc:
        metrics_collector.record_job_failure()
        raise ApiException(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="INVALID_AUDIO",
            message=f"Failed to process and score audio: {exc}",
            details={"error": str(exc)},
        )

    # 8. Record Observability Metrics & Privacy-Preserving Audit Trail
    latency_s = time.perf_counter() - t0
    verdict_band = response.verdict.band.value if hasattr(response.verdict.band, "value") else str(response.verdict.band)
    metrics_collector.record_job_completion(
        operating_point=effective_op,
        verdict_band=verdict_band,
        latency_s=latency_s,
    )

    speech_ms = response.conditions.speech_duration_ms if response.conditions else 0
    q_gate = response.conditions.quality_gate if response.conditions else "unknown"
    audit_logger.record_job(
        job_id=job_id,
        operating_point=effective_op,
        verdict_band=verdict_band,
        calibrated_probability=response.verdict.probability,
        speech_duration_ms=speech_ms,
        quality_gate=q_gate,
        processing_time_ms=latency_s * 1000.0,
        client_api_key=client_key,
        data_residency_region=cfg.data_residency_region,
        zero_retention=cfg.zero_retention_mode,
    )

    # 9. Persist to job store (in zero-retention mode, audio is never saved to disk)
    job_store.save_job(job_id, response)

    return ScoreJobResponse(job_id=job_id, status=JobStatus.COMPLETE)


@app.get(
    "/v1/audio/score/{job_id}",
    response_model=ScoreResponse,
    tags=["Scoring"],
    summary="Retrieve scoring result and auditable evidence",
)
async def get_score_job(job_id: str, request: Request):
    """Retrieves the complete scoring verdict and evidence for a job_id."""
    authenticate_request(request)
    result = job_store.get_job(job_id)
    if result is None:
        metrics_collector.record_validation_error()
        raise ApiException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="JOB_NOT_FOUND",
            message=f"Scoring job '{job_id}' was not found.",
            details={"job_id": job_id},
        )

    return result
