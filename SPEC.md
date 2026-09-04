# PandaMIND Phase 1 specification

## Scope

PandaMIND is an offline Python foundation for future synthetic-audio detection work. Phase 1 establishes repository, manifest, split, detector-contract, and evaluation correctness only. It does not include a corpus, training, service/API, deployment, or benchmark claims.

## Manifest contract

`data/manifests/corpus.jsonl` is a JSONL corpus manifest. Every row has exactly: `sample_id`, `source_id`, `speaker_id`, `language`, `is_synthetic`, `generator`, `audio_path`, `degradation`, `sample_rate`, `channels`, and `split`. The loader rejects missing/unknown fields, invalid types or values, and duplicate sample IDs.

## Split contract

Splits are derived deterministically from a seed. The grouping unit is the connected component of source and speaker identifiers: an edge joins each sample's source and speaker. Therefore a source with multiple speakers, or a speaker represented by multiple sources, always remains in one split. Leakage validation independently verifies that no source or speaker crosses splits.

## Held-out generators

`src/audio_detection/config/held_out_generators.json` declares generators reserved for cross-generator evaluation. Its committed IDs are placeholders, not real providers. Samples from a declared held-out generator, and all samples in their linked source/speaker group, are assigned to `test`; validation rejects held-out generators in train or validation.

## Inference and evaluation

`AudioDetector` performs deterministic, offline PCM-WAV inference and returns an overall score plus per-segment scores. Its default `phase0-untrained` parameters are zero/untrained and make no performance claim. Evaluation records retain their slice identity and calculate discrete EER, TPR at 1% FPR, and top-label ECE. Temperature scaling is dependency-free and local.

## Verification

Run `PYTHONPATH=src python -m unittest discover -s tests -v` from the repository root (on PowerShell: `$env:PYTHONPATH='src'; python -m unittest discover -s tests -v`). Tests are deterministic and use generated in-memory WAV bytes only; no corpus or network access is required.
