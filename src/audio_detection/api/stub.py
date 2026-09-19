"""Deterministic M1 Stub Scoring Engine.

Implements the contract freeze for Milestone M1 per PRD Section 05.
Uses cryptographic hashing (SHA-256) of input audio bytes to generate
reproducible, PRD-compliant synthetic detection outputs.

CRITICAL:
- This is explicitly a STUB scorer for Milestone M1 plumbing and contract validation.
- Returned probabilities are stub placeholders and must NOT be treated as calibrated ML probabilities.
- Model version is explicitly 'm1-stub'.
- FR-7 Invariant: Provenance absence ('not_present') NEVER contributes to synthetic score or verdict.
"""
from __future__ import annotations

import hashlib
from typing import Optional

from .schemas import (
    Conditions,
    Evidence,
    OperatingPoint,
    Provenance,
    ScoreResponse,
    Segment,
    SignalContribution,
    Verdict,
    VerdictBand,
)

STUB_MODEL_VERSION = "m1-stub"
STUB_THRESHOLD_VERSION = "thr-2026-09-01"

# Frozen operating point thresholds for M1 stub
OPERATING_THRESHOLDS = {
    OperatingPoint.FPR_0_1_PCT.value: {"low": 0.75, "high": 0.85},
    OperatingPoint.FPR_1_PCT.value: {"low": 0.40, "high": 0.70},
    OperatingPoint.FPR_5_PCT.value: {"low": 0.30, "high": 0.60},
}


def compute_stub_score(
    audio_bytes: bytes,
    job_id: str,
    operating_point: str = "fpr_1pct",
    language: Optional[str] = None,
    filename: Optional[str] = None,
) -> ScoreResponse:
    """Computes a deterministic, PRD-shaped ScoreResponse from input audio bytes.

    Uses SHA-256 digest to guarantee exact reproducibility for identical audio inputs.
    """
    if not audio_bytes:
        raise ValueError("Cannot score empty audio bytes.")

    # 1. Cryptographic hash of raw audio bytes
    digest = hashlib.sha256(audio_bytes).hexdigest()

    # 2. Derive deterministic pseudo-probability in [0.00, 1.00]
    hash_slice_prob = int(digest[:8], 16)
    probability = round((hash_slice_prob % 1000) / 1000.0, 2)

    # 3. Validate and apply operating point
    valid_op = operating_point if operating_point in OPERATING_THRESHOLDS else OperatingPoint.FPR_1_PCT.value
    thresholds = OPERATING_THRESHOLDS[valid_op]

    # 4. Map probability to 3-band verdict (FR-12)
    # FR-7 enforcement: missing provenance credentials NEVER contribute to synthetic verdict.
    # Note: probability is solely derived from audio hash, independent of provenance.
    if probability > thresholds["high"]:
        band = VerdictBand.LIKELY_SYNTHETIC
        reason = None
    elif probability < thresholds["low"]:
        band = VerdictBand.CONSISTENT_WITH_HUMAN
        reason = None
    else:
        band = VerdictBand.INCONCLUSIVE
        reason = "stub_inconclusive"

    # 5. Localised partial spoof segments (FR-9)
    segments = []
    if band == VerdictBand.LIKELY_SYNTHETIC or probability >= 0.50:
        seg1_score = min(0.99, round(probability + 0.05, 2))
        seg2_score = max(0.50, round(probability - 0.08, 2))
        segments = [
            Segment(start_ms=4120, end_ms=6890, score=seg1_score),
            Segment(start_ms=11040, end_ms=12300, score=seg2_score),
        ]

    # 6. Conditions (FR-2)
    hash_slice_snr = int(digest[8:12], 16)
    snr_db = round(12.0 + (hash_slice_snr % 180) / 10.0, 1)
    bandwidths = [3400, 4000, 8000, 16000]
    bw = bandwidths[int(digest[12:14], 16) % len(bandwidths)]
    codecs_options = [
        ["amr_nb", "opus"],
        ["g711_8khz"],
        ["whatsapp_opus"],
        ["clean"],
    ]
    codecs = codecs_options[int(digest[14:16], 16) % len(codecs_options)]

    conditions = Conditions(
        effective_bandwidth_hz=bw,
        estimated_codec_chain=codecs,
        snr_db=snr_db,
        speech_duration_ms=max(2500, (len(audio_bytes) // 32)),
        quality_gate="passed",
    )

    # 7. Provenance (FR-7: missing credentials reported as not_present; never evidence)
    provenance = Provenance(
        c2pa="not_present",
        watermark="not_present",
        contributed_to_verdict=False,
    )

    # 8. Evidence (FR-15)
    evidence = Evidence(
        signal_contributions=[
            SignalContribution(signal="ssl_frontend", weight=0.62),
            SignalContribution(signal="waveform_branch", weight=0.24),
            SignalContribution(signal="prosody_rhythm", weight=0.14),
        ],
        language_detected=language or "hi-en_codeswitch",
        model_version=STUB_MODEL_VERSION,
        threshold_version=STUB_THRESHOLD_VERSION,
    )

    # Assemble complete PRD response
    return ScoreResponse(
        job_id=job_id,
        status="complete",
        verdict=Verdict(
            band=band,
            probability=probability,
            operating_point=valid_op,
            reason=reason,
        ),
        segments=segments,
        conditions=conditions,
        provenance=provenance,
        evidence=evidence,
    )
