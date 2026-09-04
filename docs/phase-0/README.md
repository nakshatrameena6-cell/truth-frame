# Phase 0 audio detection

This is a pure offline Python library: it has no REST/API server, credentials, network calls, or infrastructure bindings.

Populate `data/manifests/corpus.jsonl` with real licensed audio before training or benchmarking. Each JSONL sample must contain exactly these fields: `sample_id`, `source_id`, `speaker_id`, `language`, `is_synthetic`, `generator`, `audio_path`, `degradation`, `sample_rate`, `channels`, and `split`. IDs, language, path, and degradation are non-empty strings; `is_synthetic` is boolean; sample rate and channels are positive integers; and `split` is one of `train`, `validation`, `test`, or `unassigned`.

Split assignment is deterministic for a supplied seed. It assigns one split to each connected source/speaker group, so neither a source nor a speaker can cross train, validation, and test boundaries. Generators listed in `src/audio_detection/config/held_out_generators.json` are assigned to test only and are rejected if they appear in train or validation. The committed values are clearly labelled logical placeholders; replace them with immutable corpus generator IDs before a data run, retaining at least two. No datasets, results, or acceptance claims are included.

Run `PYTHONPATH=src python -m unittest discover -s tests -v` (on PowerShell: `$env:PYTHONPATH='src'; python -m unittest discover -s tests -v`). AMR-NB and Opus degradation use an already-local `ffmpeg` only; no downloads occur.

The metrics writer emits only observed rows, each keyed by dataset, split, language, generator, channel condition, degradation, and model version. Evaluate Hindi (`hi`), Tamil (`ta`), and Hinglish (for example `hi-en`) as separate language values. Release thresholds are not evaluated until representative corpus data is supplied.
