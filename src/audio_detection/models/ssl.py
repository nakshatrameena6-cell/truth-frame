"""Pretrained SSL Speech/Audio Feature Extractor.

Extracts deterministic 768-dimensional embeddings using facebook/wav2vec2-base.
"""
from __future__ import annotations

import numpy as np
import torch
from transformers import AutoFeatureExtractor, AutoModel


class Wav2Vec2SSLEmbedder:
    """Deterministic, offline SSL feature extractor based on Wav2Vec2."""

    def __init__(self, model_name: str = "facebook/wav2vec2-base", local_dir: str | None = None):
        self.model_name = model_name
        self.local_dir = local_dir

        if local_dir:
            import os
            if not os.path.isdir(local_dir):
                raise FileNotFoundError(f"Offline weights directory not found: {local_dir}")
            
            # Strict offline enforcement
            self.feature_extractor = AutoFeatureExtractor.from_pretrained(local_dir, local_files_only=True)
            self.model = AutoModel.from_pretrained(local_dir, local_files_only=True)
        else:
            self.feature_extractor = AutoFeatureExtractor.from_pretrained(model_name)
            self.model = AutoModel.from_pretrained(model_name)
            
        self.model.eval()

    def __call__(self, samples: list[float] | np.ndarray, sample_rate: int) -> list[float]:
        arr = np.asarray(samples, dtype=np.float32)
        if len(arr) == 0:
            return [0.0] * 768

        # 1. Peak normalization
        peak = float(np.max(np.abs(arr)))
        if peak > 1e-6:
            arr = arr / peak

        # 2. Resample to 16000 Hz if necessary
        target_sr = 16000
        if sample_rate != target_sr and len(arr) > 1:
            n_target = int(round(len(arr) * target_sr / sample_rate))
            if n_target > 0:
                orig_x = np.linspace(0, len(arr) - 1, len(arr))
                target_x = np.linspace(0, len(arr) - 1, n_target)
                arr = np.interp(target_x, orig_x, arr).astype(np.float32)

        # 3. Extract SSL features
        inputs = self.feature_extractor(arr, sampling_rate=target_sr, return_tensors="pt")
        with torch.no_grad():
            outputs = self.model(**inputs)
            pooled = outputs.last_hidden_state.mean(dim=1).squeeze(0).cpu().numpy()

        return [round(float(v), 6) for v in pooled]
