from __future__ import annotations

from dataclasses import asdict, dataclass

from .calibration import TemperatureScaler, ThresholdConfig, assign_verdict_band
from .models import HybridFrontend
from .preprocessing import decode_wav, vad_segments


@dataclass(frozen=True)
class DetectionResult:
    score: float
    segments: list[dict]
    model_version: str
    confidence: float
    raw_score: float = 0.0
    calibrated_probability: float = 0.0
    verdict: str = "not_calibrated"
    calibration_status: str = "not_calibrated"
    operating_point_thresholds: dict[str, float] | None = None
    thresholds: dict[str, float] | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class AudioDetector:
    """Pure deterministic offline inference; defaults are explicitly untrained."""

    def __init__(
        self,
        model_version: str = "phase0-untrained",
        weights: tuple = (0.0,) * 10,
        bias: float = 0.0,
        temperature: float = 1.0,
        threshold_config: ThresholdConfig | None = None,
    ):
        self.model_version = model_version
        self.weights = tuple(weights)
        self.bias = bias
        self.calibrator = TemperatureScaler(temperature)
        self.frontend = HybridFrontend()

        if threshold_config is not None:
            self.threshold_config = threshold_config
            self.calibrator.temperature = threshold_config.temperature
        else:
            self.threshold_config = ThresholdConfig(
                temperature=temperature,
                calibration_status="not_calibrated",
                calibration_reason="insufficient_validation_data",
            )

    def detect(self, audio_bytes: bytes) -> dict:
        samples, rate = decode_wav(audio_bytes)
        spans = vad_segments(samples, rate) or [(0, len(samples))]

        segments = []
        raw_logits = []

        # Keep calibrator temperature synchronized with threshold_config
        if self.threshold_config is not None:
            self.calibrator.temperature = self.threshold_config.temperature

        for start, end in spans:
            features = self.frontend.embed(samples[start:end], rate)
            raw_logit = self.bias + sum(w * x for w, x in zip(self.weights, features))
            raw_logits.append(raw_logit)

            seg_prob = self.calibrator.transform([raw_logit])[0]
            segments.append({
                "start_ms": round(start * 1000 / rate, 3),
                "end_ms": round(end * 1000 / rate, 3),
                "score": round(seg_prob, 6),
                "raw_logit": round(raw_logit, 6),
            })

        avg_raw_logit = sum(raw_logits) / len(raw_logits)
        avg_calibrated_prob = sum(s["score"] for s in segments) / len(segments)

        verdict = assign_verdict_band(avg_calibrated_prob, self.threshold_config)

        op_thresholds = (
            self.threshold_config.operating_point_thresholds
            if self.threshold_config and self.threshold_config.calibration_status == "calibrated"
            else None
        )
        band_thresholds = (
            {
                "low": self.threshold_config.low_threshold,
                "high": self.threshold_config.high_threshold,
            }
            if self.threshold_config and self.threshold_config.calibration_status == "calibrated"
            else None
        )

        result = DetectionResult(
            score=round(avg_calibrated_prob, 6),
            segments=segments,
            model_version=self.model_version,
            confidence=round(abs(avg_calibrated_prob - 0.5) * 2, 6),
            raw_score=round(avg_raw_logit, 6),
            calibrated_probability=round(avg_calibrated_prob, 6),
            verdict=verdict,
            calibration_status=self.threshold_config.calibration_status,
            operating_point_thresholds=op_thresholds,
            thresholds=band_thresholds,
        )
        return result.to_dict()
