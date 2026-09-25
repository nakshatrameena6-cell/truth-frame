"""Speech Windowing, Per-Segment Scoring, and Partial-Spoof Localization (FR-8, FR-9).

Requirements:
- Windowing restricted strictly to active speech regions (non-speech excluded).
- Per-segment model inference producing authentic model scores.
- Utterance-level aggregation from segment scores.
- Partial-spoof localization flagging segments exceeding the operating threshold.
- Deterministic merging of adjacent/overlapping flagged regions.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

from audio_detection.calibration import PlattScaler
from audio_detection.models.frontend import HybridFrontend


@dataclass(frozen=True)
class ScoredSegment:
    start_ms: int
    end_ms: int
    score: float
    raw_logit: float


@dataclass(frozen=True)
class LocalizationResult:
    scored_segments: List[ScoredSegment]
    flagged_segments: List[ScoredSegment]
    aggregate_score: float


def generate_speech_windows(
    spans: List[Tuple[int, int]],
    sample_rate: int,
    window_ms: int = 1000,
    hop_ms: int = 500,
) -> List[Tuple[int, int]]:
    """Generates discrete analysis windows restricted strictly within VAD speech spans."""
    win_samples = max(32, sample_rate * window_ms // 1000)
    hop_samples = max(16, sample_rate * hop_ms // 1000)
    windows: List[Tuple[int, int]] = []

    for st, ed in spans:
        span_len = ed - st
        if span_len < 32:
            continue
        if span_len <= win_samples:
            windows.append((st, ed))
        else:
            cur = st
            while cur + win_samples <= ed:
                windows.append((cur, cur + win_samples))
                cur += hop_samples
            # Catch trailing window if significant duration remains
            if ed - cur >= win_samples // 2 and (cur, ed) not in windows:
                windows.append((cur, ed))

    return windows


def score_speech_segments(
    samples: List[float],
    sample_rate: int,
    windows: List[Tuple[int, int]],
    weights: Tuple[float, ...],
    bias: float,
    calibrator: PlattScaler,
    frontend: HybridFrontend,
) -> List[ScoredSegment]:
    """Evaluates the model over each speech window, computing actual logits and calibrated scores."""
    scored: List[ScoredSegment] = []

    for st, ed in windows:
        seg_samples = samples[st:ed]
        if len(seg_samples) < 32:
            continue

        feats = frontend.embed(seg_samples, sample_rate)[: len(weights)]
        raw_logit = bias + sum(w * x for w, x in zip(weights, feats))
        prob = float(calibrator.transform([raw_logit])[0])
        prob = max(0.0, min(1.0, round(prob, 4)))

        start_ms = round(st * 1000 / sample_rate)
        end_ms = round(ed * 1000 / sample_rate)

        scored.append(
            ScoredSegment(
                start_ms=start_ms,
                end_ms=end_ms,
                score=prob,
                raw_logit=round(float(raw_logit), 4),
            )
        )

    return scored


def localize_partial_spoofs(
    scored_segments: List[ScoredSegment],
    operating_threshold: float,
    max_gap_ms: int = 300,
) -> List[ScoredSegment]:
    """Flags segments exceeding operating threshold and merges adjacent/overlapping flagged regions."""
    # 1. Filter windows exceeding the active operating threshold
    flagged = [seg for seg in scored_segments if seg.score >= operating_threshold]
    if not flagged:
        return []

    # 2. Sort chronologically
    flagged.sort(key=lambda s: s.start_ms)

    # 3. Merge adjacent or overlapping flagged windows
    merged: List[ScoredSegment] = []
    curr_start = flagged[0].start_ms
    curr_end = flagged[0].end_ms
    curr_scores = [flagged[0].score]
    curr_logits = [flagged[0].raw_logit]

    for next_seg in flagged[1:]:
        if next_seg.start_ms <= curr_end + max_gap_ms:
            # Overlapping or contiguous with gap <= max_gap_ms
            curr_end = max(curr_end, next_seg.end_ms)
            curr_scores.append(next_seg.score)
            curr_logits.append(next_seg.raw_logit)
        else:
            # Finish previous cluster
            agg_score = round(float(np.mean(curr_scores)), 4)
            agg_logit = round(float(np.mean(curr_logits)), 4)
            merged.append(
                ScoredSegment(
                    start_ms=curr_start,
                    end_ms=curr_end,
                    score=agg_score,
                    raw_logit=agg_logit,
                )
            )
            curr_start = next_seg.start_ms
            curr_end = next_seg.end_ms
            curr_scores = [next_seg.score]
            curr_logits = [next_seg.raw_logit]

    # Append trailing cluster
    agg_score = round(float(np.mean(curr_scores)), 4)
    agg_logit = round(float(np.mean(curr_logits)), 4)
    merged.append(
        ScoredSegment(
            start_ms=curr_start,
            end_ms=curr_end,
            score=agg_score,
            raw_logit=agg_logit,
        )
    )

    return merged
