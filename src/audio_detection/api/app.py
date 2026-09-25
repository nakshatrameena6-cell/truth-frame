"""FastAPI Application for PandaMIND M1 Audio Scoring API.

Endpoints:
  POST /v1/audio/score          -> Submit audio for scoring, returns 202 with job_id
  GET  /v1/audio/score/{job_id} -> Retrieve complete PRD verdict & evidence
  GET  /health                  -> Service health check
"""
from __future__ import annotations

import os
import uuid
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

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
    description="Offline Content Trust Stack Audio Scoring API — M1 Contract + Stub",
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
    # Strictly prevent leaking internal stack traces (PRD NFR-6 / Prompt Section 16)
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
    return os.environ.get("SCORER_BACKEND", "m2").lower()


def get_model_version() -> str:
    backend = get_scorer_backend()
    if backend in ("stub", "m1", "m1-stub"):
        return STUB_MODEL_VERSION
    return scoring_engine.detector.model_version


@app.get("/health", tags=["Health"])
@app.get("/v1/health", tags=["Health"])
async def health_check():
    """Health check verifying API readiness and loaded model version."""
    return {
        "status": "ok",
        "service": "pandamind-audio-scoring",
        "version": "1.0.0",
        "model_version": get_model_version(),
    }


@app.post(
    "/v1/audio/score",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ScoreJobResponse,
    tags=["Scoring"],
    summary="Submit audio for synthetic speech scoring",
)
async def score_audio(
    file: Optional[UploadFile] = File(None, description="Audio file upload (WAV, FLAC, MP3, OGG, Opus, AMR-NB)"),
    audio: Optional[UploadFile] = File(None, description="Alternative field name for audio file"),
    operating_point: Optional[str] = Form("fpr_1pct"),
    language: Optional[str] = Form(None),
    query_op: Optional[str] = Query(None, alias="operating_point"),
    query_lang: Optional[str] = Query(None, alias="language"),
):
    """Submits an audio file for scoring.

    Returns HTTP 202 Accepted with a unique job_id.
    """
    # 1. Resolve uploaded file (accept either 'file' or 'audio' field)
    upload = file or audio
    if upload is None or not upload.filename:
        raise ApiException(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="MISSING_AUDIO",
            message="Required audio file is missing. Please provide a file under form field 'file' or 'audio'.",
        )

    # 2. Resolve operating_point and language (form takes precedence over query)
    effective_op = operating_point or query_op or "fpr_1pct"
    effective_lang = language or query_lang

    if effective_op not in VALID_OPERATING_POINTS:
        raise ApiException(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="INVALID_REQUEST",
            message=f"Invalid operating_point '{effective_op}'. Supported values are: {sorted(list(VALID_OPERATING_POINTS))}.",
            details={"allowed": sorted(list(VALID_OPERATING_POINTS)), "received": effective_op},
        )

    # 3. Extension / Format validation (PRD FR-1)
    filename = upload.filename or "audio.wav"
    _, ext = os.path.splitext(filename.lower())
    if ext not in SUPPORTED_EXTENSIONS:
        raise ApiException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            error_code="UNSUPPORTED_AUDIO",
            message=f"Unsupported audio format '{ext or 'unknown'}'. Expected one of: {sorted(list(SUPPORTED_EXTENSIONS))}.",
            details={"supported_formats": sorted(list(SUPPORTED_EXTENSIONS)), "received_format": ext},
        )

    # 4. Read audio content & validate size (PRD FR-1: max 50 MB)
    content = await upload.read()

    if len(content) == 0:
        raise ApiException(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="EMPTY_AUDIO",
            message="Uploaded audio file is empty (0 bytes).",
        )

    if len(content) > MAX_FILE_SIZE_BYTES:
        raise ApiException(
            status_code=413,
            error_code="FILE_TOO_LARGE",
            message=f"The audio file exceeds the maximum allowed size of 50 MB (received {len(content)} bytes).",
            details={"max_size_bytes": MAX_FILE_SIZE_BYTES, "received_size_bytes": len(content)},
        )

    # 5. Generate stable, unique job identifier
    job_id = f"scr_{uuid.uuid4().hex[:10]}"

    # 6. Compute scoring result (M2 baseline by default, or stub if SCORER_BACKEND=m1-stub)
    backend = get_scorer_backend()
    if backend in ("stub", "m1", "m1-stub"):
        response = compute_stub_score(
            audio_bytes=content,
            job_id=job_id,
            operating_point=effective_op,
            language=effective_lang,
            filename=filename,
        )
    else:
        try:
            response = scoring_engine.score_audio(
                audio_bytes=content,
                job_id=job_id,
                operating_point=effective_op,
                language=effective_lang,
                filename=filename,
            )
        except Exception as exc:
            raise ApiException(
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code="INVALID_AUDIO",
                message=f"Failed to process and score audio: {exc}",
                details={"error": str(exc)},
            )

    # 7. Persist to in-memory job store
    job_store.save_job(job_id, response)

    return ScoreJobResponse(job_id=job_id, status=JobStatus.COMPLETE)


@app.get(
    "/v1/audio/score/{job_id}",
    response_model=ScoreResponse,
    tags=["Scoring"],
    summary="Retrieve scoring result and auditable evidence",
)
async def get_score_job(job_id: str):
    """Retrieves the complete scoring verdict and evidence for a job_id."""
    result = job_store.get_job(job_id)
    if result is None:
        raise ApiException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="JOB_NOT_FOUND",
            message=f"Scoring job '{job_id}' was not found.",
            details={"job_id": job_id},
        )

    return result
