# PandaMIND Authentic Detection Corpus Documentation

## Overview
This document specifies the authentic, non-contaminated dataset for PandaMIND synthetic audio detection work. All synthetic samples are genuinely synthesized by verified text-to-speech engines (`elevenlabs_v3`, `google_tts`, `edge_tts_neural`), and all real speech samples are sourced from public-domain or open-licensed human speech recordings.

## Summary Metrics
- **Total Samples**: 68 audio files across 17 connected source/speaker groups
- **Real Human Speech Samples**: 8 audio files (4 source groups)
- **Synthetic Speech Samples**: 60 audio files (13 source groups)
- **Languages Covered**:
  - English (`en`): 28 samples
  - Hindi (`hi`): 20 samples
  - Tamil (`ta`): 16 samples
  - Hinglish (`hinglish`): 4 samples
- **Synthetic Generators**:
  - `human` (Real human speech): 8 samples (4 source groups)
  - `elevenlabs_v3` (Seen TTS): 4 samples (1 source group)
  - `google_tts` (Seen TTS): 32 samples (8 source groups)
  - `edge_tts_neural` (Held-out TTS): 24 samples (6 source groups)
- **Degradation Profiles**:
  - `clean` (16 kHz PCM WAV): 17 samples
  - `g711_8khz` (G.711 μ-law 8 kHz PCM WAV): 17 samples
  - `amr_nb` (AMR-NB 8 kHz PCM WAV): 17 samples
  - `whatsapp_opus` (WhatsApp / Opus 16 kHz PCM WAV): 17 samples
- **Split Distribution**:
  - `train`: 24 samples (4 Real, 20 Synthetic)
  - `validation`: 16 samples (4 Real, 12 Synthetic)
  - `test`: 28 samples (28 Synthetic, including 24 `edge_tts_neural` held-out generator)

## Provenance & Licensing
1. **Indic Doctor-Patient Speech Dataset**:
   - License: Creative Commons Attribution 4.0 International (CC BY 4.0)
   - Source: Open Access Indic Speech dataset (`doctor-patient-indic-speech-dataset`)
   - Real Hindi & Tamil speech recordings.
2. **Wikimedia Commons Public Domain Speech Recordings**:
   - Franklin D. Roosevelt Pearl Harbor Speech (1941) – Public Domain (US Federal Government work)
   - Booker T. Washington Atlanta Speech (1895) – Public Domain
   - ElevenLabs v3 Mark Accents Speech Sample – Creative Commons Attribution / Wikimedia Commons
3. **Google Text-to-Speech (gTTS)**:
   - Genuine synthetic speech generated via Google TTS API across `en`, `hi`, and `ta`.
4. **Microsoft Edge Neural TTS (edge_tts)**:
   - Genuine synthetic speech generated via Microsoft Edge Neural TTS voices (`en-US-AvaNeural`, `hi-IN-SwaraNeural`, `ta-IN-PallaviNeural`, `en-IN-NeerjaExpressiveNeural`) across `en`, `hi`, `ta`, and `hinglish`.

## Split & Leakage Rules
- **Disjoint Connected Components**: Source IDs and Speaker IDs are grouped into connected components. Every sample from the same source or speaker is assigned to the exact same split using deterministic SHA-256 bucket hashing (`assign_splits`).
- **Held-Out Generator Isolation**: `edge_tts_neural` is declared in `src/audio_detection/config/held_out_generators.json` and is strictly forbidden in `train` and `validation` splits. All 24 `edge_tts_neural` samples are assigned exclusively to the `test` split.
- **Duplicate-Content Guard**: SHA-256 byte hashing (`validate_corpus_audio`) scans every audio file to ensure no byte-identical audio files exist with conflicting `is_synthetic` or `generator` metadata.

## Limitations & Remaining Data Gaps
- **Real Speech Representation in Test Split**: Real speech is present in `train` (4 samples) and `validation` (4 samples). Expanding real speech coverage into the `test` split is recommended as additional CC/public-domain Indic real speech recordings become available.
- **Unavailable Categories**: No fabricated audio, fake speakers, or artificial split manipulation was performed.
