"""Build the reproducible Phase 2 WAV corpus from its documented raw source."""
from __future__ import annotations

import argparse
import audioop
import math
from pathlib import Path
import wave

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

from audio_detection.data import CorpusManifest, Sample, assign_splits
from audio_detection.degradation.channels import g711_mulaw

SOURCE_ID = "doctor-patient-indic-speech-dataset"
SPEAKERS = {
    "hi": "unsegmented_doctor_patient_pair_hindi_001",
    "ta": "unsegmented_doctor_patient_pair_tamil_001",
}


def _pcm16(samples: np.ndarray) -> bytes:
    return np.clip(np.rint(samples * 32767), -32768, 32767).astype("<i2").tobytes()


def _write_wav(path: Path, pcm: bytes, rate: int) -> None:
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(pcm)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-root", type=Path, default=Path("data/raw/doctor-patient-indic-speech-dataset"))
    parser.add_argument("--output-root", type=Path, default=Path("data/processed/phase2"))
    parser.add_argument("--manifest", type=Path, default=Path("data/manifests/corpus.jsonl"))
    args = parser.parse_args()
    args.output_root.mkdir(parents=True, exist_ok=True)
    samples: list[Sample] = []
    for language, folder in (("hi", "hindi"), ("ta", "tamil")):
        source = args.raw_root / "audio" / folder / "convo_001.mp3"
        signal, rate = sf.read(source, dtype="float64", always_2d=True)
        mono = signal.mean(axis=1)
        clean_path = args.output_root / f"{language}_convo_001_clean.wav"
        _write_wav(clean_path, _pcm16(mono), rate)
        source_id = f"{SOURCE_ID}-{folder}-convo-001"
        samples.append(Sample(
            sample_id=f"{language}-doctor-patient-001-clean", source_id=source_id,
            speaker_id=SPEAKERS[language], language=language, is_synthetic=False,
            generator="human", audio_path=clean_path.as_posix(), degradation="clean",
            sample_rate=rate, channels=1,
        ))
        divisor = math.gcd(8000, rate)
        resampled = resample_poly(mono, 8000 // divisor, rate // divisor)
        g711_pcm = audioop.ulaw2lin(g711_mulaw(_pcm16(resampled), 8000), 2)
        g711_path = args.output_root / f"{language}_convo_001_g711_8khz.wav"
        _write_wav(g711_path, g711_pcm, 8000)
        samples.append(Sample(
            sample_id=f"{language}-doctor-patient-001-g711-8khz", source_id=source_id,
            speaker_id=SPEAKERS[language], language=language, is_synthetic=False,
            generator="human", audio_path=g711_path.as_posix(), degradation="g711_8khz",
            sample_rate=8000, channels=1,
        ))
    assign_splits(samples, set()).write_jsonl(args.manifest)


if __name__ == "__main__":
    main()
