import json
import math
import random
from pathlib import Path

from audio_detection.data.manifest import CorpusManifest
from audio_detection.preprocessing import decode_wav, vad_segments
from audio_detection.models.frontend import HybridFrontend
from audio_detection.detector import AudioDetector

class TrainingDataError(ValueError): pass

def _sigmoid(x: float) -> float:
    try:
        return 1.0 / (1.0 + math.exp(-x))
    except OverflowError:
        return 0.0 if x < 0 else 1.0

def train_model(manifest: CorpusManifest, audio_root: Path, held_out_config_path: Path, epochs: int = 10, lr: float = 0.01, seed: int = 42) -> AudioDetector:
    random.seed(seed)
    
    with open(held_out_config_path, "r", encoding="utf-8") as f:
        held_out_data = json.load(f)
    held_out_gens = set(held_out_data.get("generators", []))

    train_samples = [s for s in manifest.samples if s.split == "train"]
    
    for s in train_samples:
        if s.generator in held_out_gens:
            raise TrainingDataError(f"Held-out generator '{s.generator}' found in training data.")
            
    labels = [1 if s.is_synthetic else 0 for s in train_samples]
    if len(set(labels)) < 2:
        raise TrainingDataError("Insufficient labeled data: training requires both real and synthetic samples.")

    frontend = HybridFrontend()
    features = []
    
    for s in train_samples:
        path = audio_root / s.audio_path
        with open(path, "rb") as f:
            audio_bytes = f.read()
        samples, rate = decode_wav(audio_bytes)
        spans = vad_segments(samples, rate) or [(0, len(samples))]
        
        seg_features = []
        for start, end in spans:
            seg_features.append(frontend.embed(samples[start:end], rate))
        
        avg_feat = [sum(col) / len(col) for col in zip(*seg_features)]
        features.append(avg_feat)
        
    num_features = len(features[0])
    weights = [0.0] * num_features
    bias = 0.0
    
    indices = list(range(len(features)))
    for _ in range(epochs):
        random.shuffle(indices)
        for i in indices:
            x = features[i]
            y = labels[i]
            
            z = bias + sum(w * f for w, f in zip(weights, x))
            p = _sigmoid(z)
            
            error = p - y
            
            bias -= lr * error
            for j in range(num_features):
                weights[j] -= lr * error * x[j]
                
    return AudioDetector(model_version="phase4-baseline", weights=tuple(weights), bias=bias)

def save_checkpoint(detector: AudioDetector, config: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "model_version": detector.model_version,
            "weights": detector.weights,
            "bias": detector.bias,
            "temperature": detector.calibrator.temperature,
            "config": config
        }, f, indent=2)

def load_checkpoint(path: Path) -> AudioDetector:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return AudioDetector(
        model_version=data["model_version"],
        weights=tuple(data["weights"]),
        bias=data["bias"],
        temperature=data.get("temperature", 1.0)
    )
