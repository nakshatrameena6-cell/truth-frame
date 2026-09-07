"""High-level calibration module to calibrate AudioDetector using validation datasets."""
from __future__ import annotations

from pathlib import Path

from audio_detection.data.manifest import CorpusManifest
from audio_detection.detector import AudioDetector
from audio_detection.models.frontend import HybridFrontend
from audio_detection.preprocessing import decode_wav, vad_segments
from .thresholds import ThresholdConfig, derive_calibration_thresholds


def calibrate_model(
    detector: AudioDetector,
    manifest: CorpusManifest,
    audio_root: Path,
    target_operating_point: str = "fpr_1%",
) -> AudioDetector:
    """Calibrate detector probabilities and derive thresholds from validation split.

    If validation data is missing or insufficient, detector returns 'not_calibrated'
    state with an explicit reason string.
    """
    val_samples = [s for s in manifest.samples if s.split == "validation"]
    labels = [1 if s.is_synthetic else 0 for s in val_samples]

    if not val_samples or set(labels) != {0, 1}:
        reason = "insufficient_validation_data" if not val_samples else "insufficient_validation_data_missing_classes"
        
        # Determine the current calibration parameters safely
        if hasattr(detector.calibrator, "temperature"):
            calib_state = {"temperature": detector.calibrator.temperature}
        else:
            calib_state = {"scale": getattr(detector.calibrator, "scale", 1.0), "shift": getattr(detector.calibrator, "shift", 0.0)}

        config = ThresholdConfig(
            calibration_status="not_calibrated",
            calibration_reason=reason,
            target_operating_point=target_operating_point,
            **calib_state
        )
        detector.threshold_config = config
        return detector

    frontend = detector.frontend
    raw_logits: list[float] = []

    for s in val_samples:
        path = audio_root / s.audio_path
        with open(path, "rb") as f:
            audio_bytes = f.read()
        samples, rate = decode_wav(audio_bytes)
        spans = vad_segments(samples, rate) or [(0, len(samples))]

        seg_logits = []
        for start, end in spans:
            features = frontend.embed(samples[start:end], rate)
            logit = detector.bias + sum(w * x for w, x in zip(detector.weights, features))
            seg_logits.append(logit)

        avg_logit = sum(seg_logits) / len(seg_logits)
        raw_logits.append(avg_logit)

    # Fit temperature scaling on validation set logits
    detector.calibrator.fit(raw_logits, labels)

    # Compute calibrated probabilities
    calibrated_probs = detector.calibrator.transform(raw_logits)

    # Derive operating point thresholds and verdict bands
    threshold_config = derive_calibration_thresholds(
        calibrated_probs,
        labels,
        scale=detector.calibrator.scale,
        shift=detector.calibrator.shift,
        target_operating_point=target_operating_point,
    )
    detector.threshold_config = threshold_config
    return detector
