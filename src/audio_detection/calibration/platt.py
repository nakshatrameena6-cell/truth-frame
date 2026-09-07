"""Dependency-free Platt scaling for binary detector logits."""
from __future__ import annotations

import math


class PlattScaler:
    """Map logits to calibrated probabilities using a learned scale and shift.
    
    Optimizes for Brier Score natively to minimize Expected Calibration Error (ECE).
    """

    def __init__(self, scale: float = 1.0, shift: float = 0.0):
        self.scale = float(scale)
        self.shift = float(shift)

    def transform(self, scores: list[float]) -> list[float]:
        """Return sigmoid probabilities for the supplied uncalibrated logits."""
        return [self._sigmoid(score * self.scale + self.shift) for score in scores]

    def fit(self, scores: list[float], labels: list[int]) -> "PlattScaler":
        """Choose scale and shift by grid-searching binary Brier score."""
        if len(scores) != len(labels) or not scores:
            raise ValueError("scores and labels must be non-empty and have equal length")
        if any(label not in (0, 1) for label in labels):
            raise ValueError("labels must be binary")

        # We use Logistic Regression (NLL with L2 regularization) for principled Platt scaling.
        # This prevents the scale parameter from exploding to infinity on perfectly separable data,
        # which would otherwise destroy soft probability calibration bounds on generalized test sets.
        try:
            from sklearn.linear_model import LogisticRegression
        except ImportError:
            raise ImportError("scikit-learn is required for Platt calibration optimization.")
        
        import numpy as np
        
        X = np.array(scores).reshape(-1, 1)
        y = np.array(labels)
        
        lr = LogisticRegression(C=1.0, penalty="l2")
        lr.fit(X, y)
        
        self.scale = float(lr.coef_[0][0])
        self.shift = float(lr.intercept_[0])
        return self

    @staticmethod
    def _sigmoid(value: float) -> float:
        if value >= 0:
            return 1.0 / (1.0 + math.exp(-value))
        exponent = math.exp(value)
        return exponent / (1.0 + exponent)

    @classmethod
    def _brier(cls, scores: list[float], labels: list[int], scale: float, shift: float) -> float:
        probabilities = [cls._sigmoid(score * scale + shift) for score in scores]
        return sum((p - y) ** 2 for p, y in zip(probabilities, labels)) / len(labels)
