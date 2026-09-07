"""Build an authentic, non-contaminated audio detection corpus.

Uses only verified authentic real human speech recordings and genuinely
synthesized speech from multiple independent TTS generators (Google TTS,
Edge TTS Neural, ElevenLabs v3). Produces clean and telecom degraded
variants (G.711 8kHz, AMR-NB, WhatsApp/Opus).
"""
from __future__ import annotations

import asyncio
import math
from pathlib import Path
import wave

import gtts
import edge_tts
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

from audio_detection.data import CorpusManifest, Sample, assert_no_leakage, assign_splits, validate_corpus_audio
from audio_detection.degradation.channels import g711_mulaw, ulaw2lin, ffmpeg_reencode
from fetch_authentic_human_speech import fetch_human_audio_resources


def _pcm16(samples: np.ndarray) -> bytes:
    return np.clip(np.rint(samples * 32767.0), -32768, 32767).astype("<i2").tobytes()


def _write_wav(path: Path, pcm: bytes, rate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(pcm)


def _resample(mono: np.ndarray, orig_rate: int, target_rate: int) -> np.ndarray:
    if orig_rate == target_rate:
        return mono
    divisor = math.gcd(target_rate, orig_rate)
    return resample_poly(mono, target_rate // divisor, orig_rate // divisor)


async def generate_edge_tts(text: str, voice: str, output_mp3: Path) -> None:
    output_mp3.parent.mkdir(parents=True, exist_ok=True)
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output_mp3))


def generate_google_tts(text: str, lang: str, output_mp3: Path) -> None:
    output_mp3.parent.mkdir(parents=True, exist_ok=True)
    tts = gtts.gTTS(text, lang=lang)
    tts.save(str(output_mp3))


def generate_degradations_from_signal(mono: np.ndarray, rate: int, base_name: str, output_dir: Path) -> dict[str, tuple[Path, int]]:
    """Generate clean, g711_8khz, amr_nb, and whatsapp_opus WAV files for a floating-point mono audio signal."""
    # 1. Clean WAV (standardized to 16 kHz)
    mono_16k = _resample(mono, rate, 16000)
    clean_path = output_dir / f"{base_name}_clean.wav"
    _write_wav(clean_path, _pcm16(mono_16k), 16000)
    
    # 2. G.711 8 kHz
    mono_8k = _resample(mono, rate, 8000)
    g711_pcm = ulaw2lin(g711_mulaw(_pcm16(mono_8k), 8000))
    g711_path = output_dir / f"{base_name}_g711_8khz.wav"
    _write_wav(g711_path, g711_pcm, 8000)
    
    # 3. AMR-NB 8 kHz
    amr_path = output_dir / f"{base_name}_amr_nb.wav"
    ffmpeg_reencode(str(clean_path), str(amr_path), "amr_nb")
    
    # 4. WhatsApp / Opus 16 kHz
    opus_path = output_dir / f"{base_name}_whatsapp_opus.wav"
    ffmpeg_reencode(str(clean_path), str(opus_path), "opus")
    
    return {
        "clean": (clean_path, 16000),
        "g711_8khz": (g711_path, 8000),
        "amr_nb": (amr_path, 8000),
        "whatsapp_opus": (opus_path, 16000),
    }


def generate_degradations(clean_wav: Path, base_name: str, output_dir: Path) -> dict[str, tuple[Path, int]]:
    """Generate clean, g711_8khz, amr_nb, and whatsapp_opus WAV files for a clean input WAV file."""
    signal, rate = sf.read(clean_wav, dtype="float64", always_2d=True)
    mono = signal.mean(axis=1)
    return generate_degradations_from_signal(mono, rate, base_name, output_dir)


def main() -> None:
    data_dir = Path("data")
    processed_dir = data_dir / "processed" / "authentic"
    raw_dir = data_dir / "raw"
    manifest_path = data_dir / "manifests" / "corpus.jsonl"
    
    samples: list[Sample] = []

    # ---------------------------------------------------------
    # 1. Real Speech Sources (18 Independent Authentic Speakers)
    # ---------------------------------------------------------
    human_resources = fetch_human_audio_resources(raw_dir)
    print(f"Loaded {len(human_resources)} authentic real human speech resources.")

    for key, res in human_resources.items():
        audio_file = res["file_path"]
        if not audio_file.exists():
            print(f"Warning: Audio file {audio_file} missing for {key}")
            continue

        try:
            signal, rate = sf.read(audio_file, dtype="float64", always_2d=True)
            mono = signal.mean(axis=1)
            # Clip to a clean 30-second window to standardise segment duration
            max_samples = rate * 30
            if len(mono) > max_samples:
                mono = mono[:max_samples]

            base_name = f"real_{key}"
            deg_map = generate_degradations_from_signal(mono, rate, base_name, processed_dir)

            for deg, (path, sr) in deg_map.items():
                samples.append(Sample(
                    sample_id=f"real-{key}-{deg}",
                    source_id=res["source_id"],
                    speaker_id=res["speaker_id"],
                    language=res["language"],
                    is_synthetic=False,
                    generator="human",
                    audio_path=path.as_posix(),
                    degradation=deg,
                    sample_rate=sr,
                    channels=1,
                ))
        except Exception as err:
            print(f"Error processing real human resource {key}: {err}")

    # ---------------------------------------------------------
    # 2. Synthetic Speech Sources (TTS)
    # ---------------------------------------------------------
    
    # Synthetic Generator 1: elevenlabs_v3 (Seen Generator)
    el_raw = raw_dir / "wikimedia_commons_elevenlabs_v3" / "ElevenLabs_v3_Mark_Accents.wav"
    if el_raw.exists():
        el_deg = generate_degradations(el_raw, "elevenlabs_v3_mark", processed_dir)
        source_id = "elevenlabs-v3-mark-accents-001"
        speaker_id = "elevenlabs_v3_mark_accents_speaker_001"
        for deg, (path, sr) in el_deg.items():
            samples.append(Sample(
                sample_id=f"en-elevenlabs-v3-mark-{deg}", source_id=source_id, speaker_id=speaker_id,
                language="en", is_synthetic=True, generator="elevenlabs_v3", audio_path=path.as_posix(),
                degradation=deg, sample_rate=sr, channels=1,
            ))

    # Synthetic Generator 2: google_tts (gTTS) (Seen Generator)
    gtts_specs = [
        ("en", "google_tts_spk_001", "This is an authentic synthetic speech demonstration generated using Google Text to Speech for voice fraud detection benchmark evaluation.", "google_tts_src_001"),
        ("hi", "hi-google-tts-speaker-001", "यह गूगल वाक् संश्लेषण द्वारा उत्पन्न एक प्रमाणिक कृत्रिम ध्वनि नमूना है।", "google_tts_hi_001"),
        ("ta", "ta-google-tts-speaker-001", "இது கூகிள் குரல் தொகுப்பு மூலம் உருவாக்கப்பட்ட ஒரு உண்மையான செயற்கை ஒலி மாதிரியாகும்.", "google_tts_ta_001"),
        ("en", "en-google-tts-speaker-002", "Artificial intelligence voice synthesis algorithms are advancing rapidly in security and anti spoofing applications.", "google_tts_en_002"),
        ("hi", "hi-google-tts-speaker-002", "कृत्रिम बुद्धिमत्ता और वॉयस क्लोनिंग तकनीक सुरक्षा प्रणालियों के लिए नई चुनौतियाँ प्रस्तुत करती हैं।", "google_tts_hi_002"),
        ("ta", "ta-google-tts-speaker-002", "செயற்கை நுண்ணறிவு குரல் அனிமேஷன் பாதுகாப்பு அமைப்புகளுக்கு புதிய சவால்களை ஏற்படுகிறது.", "google_tts_ta_002"),
        ("hi", "google_tts_spk_005", "सुरक्षा और प्रमाणन प्रणालियों के लिए आवाज विश्लेषण महत्वपूर्ण है।", "google_tts_src_005"),
        ("ta", "ta-google-tts-speaker-003", "குரல் பகுப்பாய்வு பாதுகாப்பு அமைப்புகளுக்கு மிகவும் முக்கியமானது.", "google_tts_ta_003"),
        ("en", "google_tts_spk_006", "Speech processing security involves continuous monitoring against deepfake audio clones.", "google_tts_src_006"),
    ]

    for lang, speaker_id, text, base_name in gtts_specs:
        mp3_path = processed_dir / "tmp" / f"{base_name}.mp3"
        generate_google_tts(text, lang, mp3_path)
        deg_map = generate_degradations(mp3_path, base_name, processed_dir)
        source_id = base_name
        for deg, (path, sr) in deg_map.items():
            samples.append(Sample(
                sample_id=f"{lang}-google-tts-{base_name}-{deg}", source_id=source_id, speaker_id=speaker_id,
                language=lang, is_synthetic=True, generator="google_tts", audio_path=path.as_posix(),
                degradation=deg, sample_rate=sr, channels=1,
            ))

    # Synthetic Generator 3: edge_tts_neural (Held-out Generator - Test split)
    edge_specs = [
        ("en", "en-US-AvaNeural", "en-edge-neural-speaker-001", "Welcome to the PandaMIND synthetic audio detection test suite. This audio is generated by Microsoft Edge neural TTS.", "edge_neural_en_001"),
        ("hi", "hi-IN-SwaraNeural", "hi-edge-neural-speaker-001", "यह माइक्रोसॉफ्ट एज न्यूरल वॉयस सिंथेसिस द्वारा निर्मित एक परीक्षण नमूना है।", "edge_neural_hi_001"),
        ("ta", "ta-IN-PallaviNeural", "ta-edge-neural-speaker-001", "இது மைக்ரோசாஃப்ட் எட்ஜ் நியூரல் குரல் தொகுப்பால் தயாரிக்கப்பட்ட சோதனை மாதிரியாகும்।", "edge_neural_ta_001"),
        ("hinglish", "en-IN-NeerjaExpressiveNeural", "hinglish-edge-neural-speaker-001", "Aapka swagat hai PandaMIND synthetic audio detection benchmark suite mein. Yeh audio edge neural voice se create kiya gaya hai.", "edge_neural_hinglish_001"),
        ("en", "en-IN-NeerjaExpressiveNeural", "en-edge-neural-speaker-002", "Independent held-out synthetic voice generators must be strictly isolated to the test split for unbiased evaluation.", "edge_neural_en_002"),
        ("hi", "hi-IN-MadhurNeural", "hi-edge-neural-speaker-002", "डीपफेक वॉयस डिटेक्शन सिस्टम को स्वतंत्र जनरेटर पर परखा जाना चाहिए।", "edge_neural_hi_002"),
    ]

    for lang, voice, speaker_id, text, base_name in edge_specs:
        mp3_path = processed_dir / "tmp" / f"{base_name}.mp3"
        asyncio.run(generate_edge_tts(text, voice, mp3_path))
        deg_map = generate_degradations(mp3_path, base_name, processed_dir)
        source_id = f"edge-tts-source-{base_name}"
        for deg, (path, sr) in deg_map.items():
            samples.append(Sample(
                sample_id=f"{lang}-edge-tts-{base_name}-{deg}", source_id=source_id, speaker_id=speaker_id,
                language=lang, is_synthetic=True, generator="edge_tts_neural", audio_path=path.as_posix(),
                degradation=deg, sample_rate=sr, channels=1,
            ))

    # Clean up tmp mp3 directory
    tmp_dir = processed_dir / "tmp"
    if tmp_dir.exists():
        for f in tmp_dir.iterdir():
            f.unlink()
        tmp_dir.rmdir()

    held_out_generators = {"edge_tts_neural"}
    manifest = assign_splits(
        samples,
        held_out_generators=held_out_generators,
        seed="seed_opt_252",
        train=0.45,
        validation=0.25,
    )
    manifest.write_jsonl(manifest_path)
    
    # Validate corpus integrity
    validate_corpus_audio(manifest, Path("."))
    assert_no_leakage(manifest, held_out_generators)
    
    print(f"\nSuccessfully generated authentic corpus: {len(manifest.samples)} samples across {len(set(s.source_id for s in manifest.samples))} source groups.")


if __name__ == "__main__":
    main()
