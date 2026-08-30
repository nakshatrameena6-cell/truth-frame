"""Dependency-free temperature scaling for binary detector logits."""
from __future__ import annotations

import math


class TemperatureScaler:
    """Map logits to calibrated probabilities with a positive temperature."""

    def __init__(self, temperature: float = 1.0):
        if temperature <= 0:
            raise ValueError("temperature must be positive")
        self.temperature = float(temperature)

    def transform(self, scores: list[float]) -> list[float]:
        """Return sigmoid probabilities for the supplied uncalibrated logits."""
        return [self._sigmoid(score / self.temperature) for score in scores]

    def fit(self, scores: list[float], labels: list[int]) -> "TemperatureScaler":
        """Choose a temperature by grid-searching binary negative log-likelihood."""
        if len(scores) != len(labels) or not scores:
            raise ValueError("scores and labels must be non-empty and have equal length")
        if any(label not in (0, 1) for label in labels):
            raise ValueError("labels must be binary")

        candidates = [step / 20 for step in range(1, 201)]
        self.temperature = min(candidates, key=lambda temperature: self._nll(scores, labels, temperature))
        return self

    @staticmethod
    def _sigmoid(value: float) -> float:
        if value >= 0:
            return 1.0 / (1.0 + math.exp(-value))
        exponent = math.exp(value)
        return exponent / (1.0 + exponent)

    @classmethod
    def _nll(cls, scores: list[float], labels: list[int], temperature: float) -> float:
        epsilon = 1e-15
        probabilities = [cls._sigmoid(score / temperature) for score in scores]
        return -sum(
            label * math.log(max(probability, epsilon))
            + (1 - label) * math.log(max(1 - probability, epsilon))
            for label, probability in zip(labels, probabilities)
        ) / len(labels)
