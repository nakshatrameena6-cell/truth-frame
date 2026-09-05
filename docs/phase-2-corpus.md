# Phase 2 corpus

The checked-in manifest contains four locally stored, validated PCM-WAV
derivatives of two natural conversations. It is a small integration corpus,
not a representative spoof-detection training or benchmark corpus.

## Provenance and licence

| Source | URL | Snapshot | Licence | Audio used | Speaker information |
| --- | --- | --- | --- | --- | --- |
| Doctor–Patient Indic Speech Dataset (Balaji Seetharaman) | https://github.com/bala-ceg/doctor-patient-indic-speech-dataset | `38533f09c97806df09e982ff3f63b31b6527d33a` | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | `audio/hindi/convo_001.mp3`, `audio/tamil/convo_001.mp3` | Source metadata records two speakers (doctor and patient) per conversation; it does not identify or segment individual speakers. |

The source repository describes these as natural two-speaker clinic dialogues,
labels the files Hindi and Tamil, and provides `speaker_count=2` in its CSV
metadata. Manifest `speaker_id` values deliberately identify the *unsegmented
speaker pair*, not a person. Both copies of a conversation have the same
source and pair ID, keeping them in one split.

## Processing and composition

`scripts/build_phase2_corpus.py` decoded the two source MP3 files using the
locally installed libsndfile bindings, mixed to mono (the inputs are already
mono), and wrote clean 44.1 kHz signed-PCM WAV files. It then resampled to 8
kHz with `scipy.signal.resample_poly`, applied the repository's
`g711_mulaw` utility, decoded the G.711 μ-law stream back to PCM, and wrote
the `g711_8khz` WAV derivatives. The command uses `assign_splits` rather than
hand-setting splits; the current two source/speaker components both hash to
`train` for the Phase 1 default seed.

The manifest records only these truthful categories:

- Languages: Hindi (`hi`) and Tamil (`ta`); no Hinglish (`hi-en`).
- Labels: four human/real samples (`generator: "human"`); no synthetic data.
- Degradations: two `clean`, two `g711_8khz`; no `amr_nb` or `whatsapp_opus`.

AMR-NB and Opus were investigated but not generated: no local `ffmpeg` binary
is available. No generated-speech source with documented generator identity,
and no real held-out generator, was acquired. The Phase 1 held-out-generator
IDs remain placeholders and are not used as provenance.

## Validation

Run from the repository root:

```powershell
$env:PYTHONPATH='src'; python scripts/validate_corpus.py
$env:PYTHONPATH='src'; python -m unittest discover -s tests -v
```

The validator loads the exact manifest schema, checks duplicate IDs and paths,
checks leakage and held-out-generator constraints, and reads each local
PCM-WAV. It reports missing files, invalid paths, unsupported/corrupt media,
empty or near-empty audio, invalid sample rates/channels, and metadata
mismatches. It intentionally accepts PCM WAV only.

Known limitations: this corpus is tiny, has no validation/test components for
the current seed, has no Hinglish or synthetic audio, and no AMR-NB/Opus
derivatives. It must not be used to claim detection performance or balanced
coverage.
