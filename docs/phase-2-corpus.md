# Phase 2 corpus status

`data/manifests/corpus.jsonl` is deliberately an empty JSONL file. At the
time of this audit the repository contains no audio files, acquisition records,
or dataset licences. No manifest rows were invented from dataset descriptions
or URLs; consequently there is no usable training or evaluation corpus yet.

## Required source records before adding samples

For every source, retain its immutable source ID, download/provenance record,
licence and permitted use, language annotation method, and (for generated
audio) the actual generator ID. Add only files that are present locally and
validate cleanly. Human samples use `generator: "human"`; synthetic samples
must name their actual generator. The committed held-out generator identifiers
are Phase 1 placeholders, not real generator data and must not be used as
provenance.

The target language categories are Hindi (`hi`), Tamil (`ta`), and Hinglish
(`hi-en`). The currently available counts for all three are zero. The target
degradation categories are `clean` and legitimately generated or licensed
telecom-degraded audio; current counts are zero. No synthetic generator,
including a held-out generator, is currently available.

## Validation and splits

Run:

```powershell
$env:PYTHONPATH='src'; python scripts/validate_corpus.py
```

The command loads the strict schema, rejects duplicate IDs and ambiguous paths,
checks leakage and held-out-generator constraints, and validates every local
audio reference. The dependency-free validator accepts PCM WAV only and
reports missing paths, path escapes, unsupported/corrupt files, empty or
near-empty audio, invalid sample rates/channels, and manifest/file metadata
mismatches. Splits are assigned with `assign_splits`, never manually, using
the connected source/speaker grouping defined in Phase 1.

Known gap: a licensed, locally available corpus covering real and synthetic
Hindi, Tamil, Hinglish, clean, telecom-degraded, and real held-out-generator
audio has not been supplied to this repository.
