from __future__ import annotations
from dataclasses import asdict, dataclass
from .models import HybridFrontend
from .preprocessing import decode_wav, vad_segments
from .calibration import TemperatureScaler

@dataclass(frozen=True)
class DetectionResult:
    score: float; segments: list[dict]; model_version: str; confidence: float
    def to_dict(self) -> dict: return asdict(self)

class AudioDetector:
    """Pure deterministic inference; model parameters are supplied locally."""
    def __init__(self, model_version: str = "phase0-untrained", weights: tuple = (0., 0., 0., 0.), bias: float = 0., temperature: float = 1.):
        self.model_version, self.weights, self.bias = model_version, tuple(weights), bias
        self.calibrator, self.frontend = TemperatureScaler(temperature), HybridFrontend()
    def detect(self, audio_bytes: bytes) -> dict:
        samples, rate = decode_wav(audio_bytes); spans = vad_segments(samples, rate) or [(0, len(samples))]
        segments = []
        for start, end in spans:
            features = self.frontend.embed(samples[start:end], rate)
            score = self.calibrator.transform([self.bias + sum(w * x for w, x in zip(self.weights, features))])[0]
            segments.append({"start_ms": round(start * 1000 / rate, 3), "end_ms": round(end * 1000 / rate, 3), "score": score})
        score = sum(s["score"] for s in segments) / len(segments)
        return DetectionResult(score, segments, self.model_version, abs(score - .5) * 2).to_dict()
