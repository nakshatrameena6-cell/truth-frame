# Phase 0 audio detection

This is a pure offline Python library: it has no REST/API server, credentials, network calls, or infrastructure bindings.

Populate `data/manifests/corpus.jsonl` with real licensed audio before training or benchmarking. Each JSONL sample must satisfy the strict schema in `audio_detection.data.manifest`. The committed held-out generator file contains logical placeholder IDs; replace those with immutable corpus generator IDs before a data run, retaining at least two. No datasets, results, or acceptance claims are included.

Run `python -m unittest discover -s tests -v`. AMR-NB and Opus degradation use an already-local `ffmpeg` only; no downloads occur.

The metrics writer emits only observed rows, each keyed by dataset, split, language, generator, channel condition, degradation, and model version. Evaluate Hindi (`hi`), Tamil (`ta`), and Hinglish (for example `hi-en`) as separate language values. Release thresholds are not evaluated until representative corpus data is supplied.
