"""Phase 1: Extract and cache 778D SSL+classical features for all 108 corpus samples.

Run this once to create the feature cache, then run run_ssl_experiment_eval.py
for training/calibration/evaluation (which is instantaneous from cache).
"""
from __future__ import annotations

import json
import time
from pathlib import Path
import numpy as np

from audio_detection.data.manifest import CorpusManifest
from audio_detection.models import HybridFrontend, Wav2Vec2SSLEmbedder
from audio_detection.preprocessing import decode_wav, vad_segments


def log(msg: str) -> None:
    print(msg, flush=True)


def main() -> None:
    manifest_path = Path("data/manifests/corpus.jsonl")
    cache_path = Path("reports/checkpoints/ssl_feature_cache.json")
    audio_root = Path(".")

    manifest = CorpusManifest.load_jsonl(manifest_path)
    log(f"Total corpus samples: {len(manifest.samples)}")

    log("Loading Wav2Vec2SSLEmbedder (facebook/wav2vec2-base)...")
    ssl_embedder = Wav2Vec2SSLEmbedder("facebook/wav2vec2-base")
    classical_frontend = HybridFrontend(ssl_embedder=None)

    cache: dict[str, dict] = {}
    total = len(manifest.samples)
    t0 = time.time()

    for idx, s in enumerate(manifest.samples):
        p = audio_root / s.audio_path
        with open(p, "rb") as f:
            audio_bytes = f.read()
        samples, rate = decode_wav(audio_bytes)

        # 10D classical features over VAD segments
        spans = vad_segments(samples, rate) or [(0, len(samples))]
        c_seg_feats = [classical_frontend.embed(samples[st:ed], rate) for st, ed in spans]
        avg_c_feat = [sum(col) / len(col) for col in zip(*c_seg_feats)]

        # 768D SSL embedding over full audio clip (1 forward pass)
        ssl_feat = ssl_embedder(samples, rate)

        full_feat = avg_c_feat + ssl_feat

        cache[s.sample_id] = {
            "features": full_feat,
            "label": 1 if s.is_synthetic else 0,
            "split": s.split,
            "generator": s.generator,
            "language": s.language,
            "degradation": s.degradation,
            "is_synthetic": s.is_synthetic,
            "source_id": s.source_id,
            "speaker_id": s.speaker_id,
        }

        elapsed = time.time() - t0
        eta = (elapsed / (idx + 1)) * (total - idx - 1)
        log(f"  [{idx+1}/{total}] {s.sample_id} -> {len(full_feat)}D features ({elapsed:.1f}s elapsed, ETA {eta:.1f}s)")

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache, f)

    elapsed_total = time.time() - t0
    log(f"\nDone. Cached {len(cache)} samples to {cache_path} in {elapsed_total:.1f}s")
    log(f"Feature dimension: {len(next(iter(cache.values()))['features'])}")


if __name__ == "__main__":
    main()
