"""Stable raw-waveform features with an optional local SSL embedding adapter."""
from __future__ import annotations
import math

class WavLMXLSRFrontend:
    """Adapter for a locally provisioned WavLM/XLS-R-compatible embedder.

    The callable is injected by the application so this package never fetches
    weights or makes network calls. It must return a deterministic embedding.
    """
    def __init__(self, embedder=None): self.embedder = embedder
    def embed(self, samples: list[float], sample_rate: int) -> list[float]:
        return list(self.embedder(samples, sample_rate)) if self.embedder else []

class HybridFrontend:
    def __init__(self, ssl_embedder=None): self.ssl = WavLMXLSRFrontend(ssl_embedder)
    def embed(self, samples: list[float], sample_rate: int) -> list[float]:
        if not samples: return [0., 0., 0., 0.]
        mean = sum(samples)/len(samples); rms = math.sqrt(sum(x*x for x in samples)/len(samples))
        zc = sum(a*b < 0 for a,b in zip(samples,samples[1:])) / max(1,len(samples)-1)
        raw = [mean, rms, zc, math.log1p(len(samples)/sample_rate)]
        ssl = self.ssl.embed(samples, sample_rate)
        return raw + ssl
