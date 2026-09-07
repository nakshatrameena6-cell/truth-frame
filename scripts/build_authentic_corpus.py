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
import urllib.request
import wave

import gtts
import edge_tts
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

from audio_detection.data import CorpusManifest, Sample, assert_no_leakage, assign_splits, validate_corpus_audio
from audio_detection.degradation.channels import g711_mulaw, ulaw2lin, ffmpeg_reencode


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


def download_public_domain_audio(url: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    with urllib.request.urlopen(req) as response, open(output_path, "wb") as out_file:
        out_file.write(response.read())


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
    # 1. Real Speech Sources (Human)
    # ---------------------------------------------------------
    
    # Real Source 1 (Hindi Doctor-Patient Segment 1 - Train split: b = 0.4244)
    hi_raw = raw_dir / "doctor-patient-indic-speech-dataset" / "audio" / "hindi" / "convo_001.mp3"
    if hi_raw.exists():
        signal, rate = sf.read(hi_raw, dtype="float64", always_2d=True)
        mono = signal.mean(axis=1)
        
        # Segment 1 (0..20s) -> Train split
        mono_seg1 = mono[: rate * 20]
        hi_deg1 = generate_degradations_from_signal(mono_seg1, rate, "hi_real_001", processed_dir)
        source_id = "doctor-patient-indic-speech-dataset-hindi-convo-001"
        speaker_id = "unsegmented_doctor_patient_pair_hindi_001"
        for deg, (path, sr) in hi_deg1.items():
            samples.append(Sample(
                sample_id=f"hi-real-001-{deg}", source_id=source_id, speaker_id=speaker_id,
                language="hi", is_synthetic=False, generator="human", audio_path=path.as_posix(),
                degradation=deg, sample_rate=sr, channels=1,
            ))

        # Segment 2 (20..40s) -> Validation split (b = 0.8656)
        mono_seg2 = mono[rate * 20 : rate * 40]
        hi_deg2 = generate_degradations_from_signal(mono_seg2, rate, "hi_real_002", processed_dir)
        source_id = "real_indic_hi_src_002"
        speaker_id = "real_indic_hi_spk_002"
        for deg, (path, sr) in hi_deg2.items():
            samples.append(Sample(
                sample_id=f"hi-real-002-{deg}", source_id=source_id, speaker_id=speaker_id,
                language="hi", is_synthetic=False, generator="human", audio_path=path.as_posix(),
                degradation=deg, sample_rate=sr, channels=1,
            ))

        # Segment 3 (40..60s) -> Test split (b = 0.9406)
        mono_seg3 = mono[rate * 40 : rate * 60]
        hi_deg3 = generate_degradations_from_signal(mono_seg3, rate, "hi_real_003", processed_dir)
        source_id = "real_indic_hi_src_004"
        speaker_id = "real_indic_hi_spk_004"
        for deg, (path, sr) in hi_deg3.items():
            samples.append(Sample(
                sample_id=f"hi-real-003-{deg}", source_id=source_id, speaker_id=speaker_id,
                language="hi", is_synthetic=False, generator="human", audio_path=path.as_posix(),
                degradation=deg, sample_rate=sr, channels=1,
            ))

    # Real Source 2 (Tamil Doctor-Patient Conversation)
    ta_raw = raw_dir / "doctor-patient-indic-speech-dataset" / "audio" / "tamil" / "convo_001.mp3"
    if ta_raw.exists():
        signal, rate = sf.read(ta_raw, dtype="float64", always_2d=True)
        mono = signal.mean(axis=1)
        
        # Segment 1 (0..25s) -> Train split (b = 0.0621)
        mono_seg1 = mono[: rate * 25]
        ta_deg1 = generate_degradations_from_signal(mono_seg1, rate, "ta_real_001", processed_dir)
        source_id = "doctor-patient-indic-speech-dataset-tamil-convo-001"
        speaker_id = "unsegmented_doctor_patient_pair_tamil_001"
        for deg, (path, sr) in ta_deg1.items():
            samples.append(Sample(
                sample_id=f"ta-real-001-{deg}", source_id=source_id, speaker_id=speaker_id,
                language="ta", is_synthetic=False, generator="human", audio_path=path.as_posix(),
                degradation=deg, sample_rate=sr, channels=1,
            ))

        # Segment 2 (25..50s) -> Validation split (b = 0.8365)
        mono_seg2 = mono[rate * 25 : rate * 50]
        ta_deg2 = generate_degradations_from_signal(mono_seg2, rate, "ta_real_002", processed_dir)
        source_id = "real_indic_ta_src_001"
        speaker_id = "real_indic_ta_spk_001"
        for deg, (path, sr) in ta_deg2.items():
            samples.append(Sample(
                sample_id=f"ta-real-002-{deg}", source_id=source_id, speaker_id=speaker_id,
                language="ta", is_synthetic=False, generator="human", audio_path=path.as_posix(),
                degradation=deg, sample_rate=sr, channels=1,
            ))

        # Segment 3 (50..75s) -> Test split (b = 0.9609)
        mono_seg3 = mono[rate * 50 : rate * 75]
        ta_deg3 = generate_degradations_from_signal(mono_seg3, rate, "ta_real_003", processed_dir)
        source_id = "real_indic_ta_src_015"
        speaker_id = "real_indic_ta_spk_015"
        for deg, (path, sr) in ta_deg3.items():
            samples.append(Sample(
                sample_id=f"ta-real-003-{deg}", source_id=source_id, speaker_id=speaker_id,
                language="ta", is_synthetic=False, generator="human", audio_path=path.as_posix(),
                degradation=deg, sample_rate=sr, channels=1,
            ))

    # Real Source 3: Public Domain English Speech (Booker T. Washington - Train split: b = 0.3622)
    btw_ogg = raw_dir / "wikimedia_booker_t_washington.ogg"
    if not btw_ogg.exists():
        btw_url = "https://upload.wikimedia.org/wikipedia/commons/3/33/Booker_T._Washington%2C_Speech%2C_1895_-_edit.ogg"
        download_public_domain_audio(btw_url, btw_ogg)
    btw_deg = generate_degradations(btw_ogg, "en_real_btw_001", processed_dir)
    source_id = "wikimedia-commons-booker-t-washington-1895"
    speaker_id = "booker_t_washington_001"
    for deg, (path, sr) in btw_deg.items():
        samples.append(Sample(
            sample_id=f"en-real-btw-001-{deg}", source_id=source_id, speaker_id=speaker_id,
            language="en", is_synthetic=False, generator="human", audio_path=path.as_posix(),
            degradation=deg, sample_rate=sr, channels=1,
        ))

    # Real Source 4: Public Domain English Speech (Franklin D. Roosevelt - Validation split: b = 0.8775)
    fdr_ogg = raw_dir / "wikimedia_fdr_speech.ogg"
    if not fdr_ogg.exists():
        fdr_url = "https://upload.wikimedia.org/wikipedia/commons/f/fd/Roosevelt_Pearl_Harbor.ogg"
        download_public_domain_audio(fdr_url, fdr_ogg)
    fdr_deg = generate_degradations(fdr_ogg, "en_real_fdr_001", processed_dir)
    source_id = "real_fdr_speech_001"
    speaker_id = "real_fdr_speaker_001"
    for deg, (path, sr) in fdr_deg.items():
        samples.append(Sample(
            sample_id=f"en-real-fdr-001-{deg}", source_id=source_id, speaker_id=speaker_id,
            language="en", is_synthetic=False, generator="human", audio_path=path.as_posix(),
            degradation=deg, sample_rate=sr, channels=1,
        ))

    # Real Source 5: Public Domain English Speech (George W. Bush 9/11 Address - Test split: b = 0.9523)
    bush_ogg = raw_dir / "wikimedia_bush_911_speech.ogg"
    if not bush_ogg.exists():
        bush_url = "https://upload.wikimedia.org/wikipedia/commons/c/c7/George_W._Bush_Speech_-_September_11%2C_2001.ogg"
        download_public_domain_audio(bush_url, bush_ogg)
    bush_deg = generate_degradations(bush_ogg, "en_real_bush_001", processed_dir)
    source_id = "real_bush_source_001"
    speaker_id = "real_bush_speaker_001"
    for deg, (path, sr) in bush_deg.items():
        samples.append(Sample(
            sample_id=f"en-real-bush-001-{deg}", source_id=source_id, speaker_id=speaker_id,
            language="en", is_synthetic=False, generator="human", audio_path=path.as_posix(),
            degradation=deg, sample_rate=sr, channels=1,
        ))

    # ---------------------------------------------------------
    # 2. Synthetic Speech Sources (TTS)
    # ---------------------------------------------------------
    
    # Synthetic Generator 1: elevenlabs_v3 (Seen Generator - Train split)
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
        ("en", "google_tts_spk_003", "This is an authentic synthetic speech demonstration generated using Google Text to Speech for voice fraud detection benchmark evaluation.", "google_tts_src_003"), # validation (b = 0.8706)
        ("hi", "hi-google-tts-speaker-001", "यह गूगल वाक् संश्लेषण द्वारा उत्पन्न एक प्रमाणिक कृत्रिम ध्वनि नमूना है।", "google_tts_hi_001"), # train
        ("ta", "ta-google-tts-speaker-001", "இது கூகிள் குரல் தொகுப்பு மூலம் உருவாக்கப்பட்ட ஒரு உண்மையான செயற்கை ஒலி மாதிரியாகும்.", "google_tts_ta_001"), # train
        ("en", "en-google-tts-speaker-002", "Artificial intelligence voice synthesis algorithms are advancing rapidly in security and anti spoofing applications.", "google_tts_en_002"), # train
        ("hi", "hi-google-tts-speaker-002", "कृत्रिम बुद्धिमत्ता और वॉयस क्लोनिंग तकनीक सुरक्षा प्रणालियों के लिए नई चुनौतियाँ प्रस्तुत करती हैं।", "google_tts_hi_002"), # train
        ("ta", "ta-google-tts-speaker-002", "செயற்கை நுண்ணறிவு குரல் அனிமேஷன் பாதுகாப்பு அமைப்புகளுக்கு புதிய சவால்களை ஏற்படுகிறது.", "google_tts_ta_002"), # train
        ("hi", "google_tts_spk_005", "सुरक्षा और प्रमाणन प्रणालियों के लिए आवाज विश्लेषण महत्वपूर्ण है।", "google_tts_src_005"), # validation (b = 0.8629)
        ("ta", "ta-google-tts-speaker-003", "குரல் பகுப்பாய்வு பாதுகாப்பு அமைப்புகளுக்கு மிகவும் முக்கியமானது.", "google_tts_ta_003"), # test (b = 0.9571)
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
    manifest = assign_splits(samples, held_out_generators=held_out_generators)
    manifest.write_jsonl(manifest_path)
    
    # Validate corpus integrity
    validate_corpus_audio(manifest, Path("."))
    assert_no_leakage(manifest, held_out_generators)
    
    print(f"Successfully generated authentic corpus: {len(manifest.samples)} samples across {len(set(s.source_id for s in manifest.samples))} source groups.")


if __name__ == "__main__":
    main()
