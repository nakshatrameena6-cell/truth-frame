"""PRD-compliant Pydantic schemas for the PandaMIND Audio Scoring API.

Authoritative specification: Audio-Scoring-API-PRD.pdf v1.0 (Phase 1 / M1)
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class VerdictBand(str, Enum):
    """Three-band verdict model required by PRD FR-12."""
    CONSISTENT_WITH_HUMAN = "consistent_with_human"
    INCONCLUSIVE = "inconclusive"
    LIKELY_SYNTHETIC = "likely_synthetic"


class OperatingPoint(str, Enum):
    """Supported operating points required by PRD FR-13."""
    FPR_0_1_PCT = "fpr_0.1pct"
    FPR_1_PCT = "fpr_1pct"
    FPR_5_PCT = "fpr_5pct"


class JobStatus(str, Enum):
    """Status lifecycle for an asynchronous scoring job."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"


class Verdict(BaseModel):
    """Scoring verdict block (PRD Section 05)."""
    band: VerdictBand = Field(
        ...,
        description="Three-band classification verdict: consistent_with_human | inconclusive | likely_synthetic",
    )
    probability: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Calibrated probability of synthetic speech (stub in M1; 0.0 to 1.0).",
    )
    operating_point: str = Field(
        default="fpr_1pct",
        description="Target false-positive rate operating point in force.",
    )
    reason: Optional[str] = Field(
        default=None,
        description="Mandatory explanatory string when band is inconclusive, otherwise null.",
    )


class Segment(BaseModel):
    """Partial spoof localization segment (PRD FR-9)."""
    start_ms: int = Field(..., ge=0, description="Segment start offset in milliseconds.")
    end_ms: int = Field(..., ge=0, description="Segment end offset in milliseconds.")
    score: float = Field(..., ge=0.0, le=1.0, description="Synthetic score for this speech region.")


class Conditions(BaseModel):
    """Input acoustic condition assessment (PRD FR-2). Licenses downstream confidence."""
    effective_bandwidth_hz: int = Field(..., description="Estimated effective bandwidth in Hz.")
    estimated_codec_chain: List[str] = Field(..., description="Best-guess codec chain or degradations.")
    snr_db: float = Field(..., description="Signal-to-noise ratio in dB.")
    speech_duration_ms: int = Field(..., ge=0, description="Total speech duration in milliseconds.")
    quality_gate: str = Field(..., description="Quality gate evaluation status ('passed' or 'failed').")
    clipping_ratio: Optional[float] = Field(
        default=None,
        description="Fraction of samples reaching or exceeding clipping threshold.",
    )


class Provenance(BaseModel):
    """Provenance assessment (PRD FR-7). Missing credentials NEVER contribute to synthetic verdict."""
    c2pa: str = Field(default="not_present", description="C2PA manifest status or trust verification.")
    watermark: str = Field(default="not_present", description="Audio watermark presence status.")
    contributed_to_verdict: bool = Field(
        default=False,
        description="CRITICAL FR-7 safety invariant: must remain False when provenance credentials are absent.",
    )


class SignalContribution(BaseModel):
    """Per-signal contribution in evidence explanation (PRD FR-15)."""
    signal: str = Field(..., description="Signal or feature name (e.g. waveform_norm_rms, spectral_flatness).")
    weight: float = Field(..., description="Relative contribution weight to aggregate decision.")


class Evidence(BaseModel):
    """Auditable evidence block (PRD FR-15)."""
    signal_contributions: List[SignalContribution] = Field(
        default_factory=list,
        description="Contributions from individual constituent detection branches.",
    )
    language_detected: str = Field(
        ...,
        description="Detected language code or code-switching pattern (PRD FR-10).",
    )
    model_version: str = Field(
        ...,
        description="Exact model/scorer identifier (e.g. 'm2-waveform-10d').",
    )
    threshold_version: str = Field(
        ...,
        description="Version of validation calibration thresholds applied.",
    )
    operating_point: Optional[str] = Field(
        default=None,
        description="Active operating point in force.",
    )
    flagged_segment_ranges: Optional[List[Segment]] = Field(
        default_factory=list,
        description="Flagged segment ranges exceeding the operating threshold (FR-9).",
    )
    code_switch_mix: Optional[Dict[str, float]] = Field(
        default=None,
        description="Code-switch language distribution if detected (FR-10).",
    )
    uncertain_language: Optional[bool] = Field(
        default=None,
        description="True if language detection could not be confirmed with high confidence.",
    )


class ScoreJobResponse(BaseModel):
    """HTTP 202 response for accepted score submission."""
    job_id: str = Field(..., description="Unique, stable job identifier (e.g. scr_...).")
    status: JobStatus = Field(default=JobStatus.COMPLETE, description="Current lifecycle state of job.")


class ScoreResponse(BaseModel):
    """Complete PRD-shaped scoring response (PRD Section 05)."""
    job_id: str = Field(..., description="Unique job identifier.")
    status: JobStatus = Field(default=JobStatus.COMPLETE, description="Job status.")
    verdict: Verdict = Field(..., description="Calibrated verdict and operating point.")
    segments: List[Segment] = Field(default_factory=list, description="Localised partial spoof segments.")
    conditions: Conditions = Field(..., description="Acoustic and channel condition metrics.")
    provenance: Provenance = Field(..., description="C2PA and watermark provenance assessment.")
    evidence: Evidence = Field(..., description="Auditable signal weights and version metadata.")


class ApiErrorResponse(BaseModel):
    """Consistent typed error schema across all endpoints (PRD Section 04 / Prompt Section 16)."""
    error_code: str = Field(..., description="Machine-readable typed error identifier.")
    message: str = Field(..., description="Human-readable explanation of the error.")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Optional structured debugging context.")
