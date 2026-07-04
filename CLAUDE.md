# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

See [README.md](README.md) for what this project is, setup, and usage commands.

## Commands

Run the near-dedup pipeline:
```
pipenv run python -m dedup.dedup --input data/test_sample.csv --output-dir data/datatrove_test
```
Must be invoked as `python -m dedup.dedup`, not `python dedup/dedup.py` — running it as a direct script path puts `dedup/` on `sys.path[0]`, and since the script itself is named `dedup.py`, that shadows the `dedup` package and breaks its own `from dedup.tokenizer import ...` import.

Run a single test:
```
pipenv run pytest tests/test_tokenizer.py::test_lowercases
```

## Architecture

**`dedup/dedup.py`** is the core pipeline. It first drops exact-duplicate rows cheaply with datatrove's `ExactDedup*` stages, then runs datatrove's MinHash near-dedup algorithm — six sequential `LocalPipelineExecutor` stages total, each depending on the previous:

1. `ExactDedupSignature` — hash each document's full text (`exact_dedup_config`, `content_getter=get_doc_content`)
2. `ExactFindDedups` — single-worker pass over those hashes, records which doc IDs are exact duplicates
3. `MinhashDedupSignature` — re-read the input, drop stage-2's exact dupes (`get_exact_dedup_filter`), compute MinHash signatures per remaining document
4. `MinhashDedupBuckets` — bucket documents by signature (`tasks=minhash_config.num_buckets`)
5. `MinhashDedupCluster` — cluster near-duplicate buckets, records which doc IDs to remove
6. `MinhashDedupFilter` — re-read the input again, drop the same exact dupes, and split into `deduped/` and `removed/` based on stage 5's output

`MinhashConfig` params (`n_grams=5, num_buckets=14, hashes_per_bucket=8`) mirror datatrove's own `fineweb.py` MinHash example, kept deliberately identical for comparability.

Important invariant: `get_reader()` + `get_corrupted_row_filter()` + `get_exact_dedup_filter()` must be reapplied identically (same order, same args modulo `exclusion_writer`) on every re-read of the input — stage 3 (minhash signature) and stage 6 (minhash filter) both re-read the raw CSV from scratch, and `MinhashDedupFilter` matches removals by `(rank, doc index within that rank)`, not by content, so all reads have to line up exactly. The exact-dedup signatures (stage 1) are likewise computed over the `get_reader()` + `get_corrupted_row_filter()` stream, so `get_exact_dedup_filter()`'s doc indices only make sense applied right after that same pair, in that same order, in stages 3 and 6.

**`dedup/tokenizer.py`** — `WhitespaceWordTokenizer`, a custom `datatrove.utils.word_tokenizers.WordTokenizer` implementation. Needed because datatrove's tokenizer registry has no entry for `kmr_Latn` / `ckb_Arab` / `diq_Latn`. All three are whitespace-delimited scripts, so a plain whitespace split (after lowercasing and stripping punctuation via `\w`/`\s` matching, which works across both Latin and Arabic script) is sufficient for MinHash word-shingling. Only `word_tokenize` is implemented; `sent_tokenize`/`span_tokenize` raise `NotImplementedError` since sentence splitting isn't used by the dedup stages, and only exist to satisfy the abstract base class.

**`dedup/sample_test_data.py`** — builds a small, publisher-diverse test sample from a full corpus CSV via per-`(lang, publisher)` reservoir sampling followed by round-robin selection across publishers. This exists because raw sampling would be dominated by a single high-volume outlet per language (e.g. one publisher was ~52% of all `kmr_Latn` rows).

**`dedup/check_max_field_length.py`** / **`dedup/check_row_shape.py`** — standalone CSV diagnostics for a specific failure mode: an unescaped/stray quote in the source CSV can cause the parser to merge multiple physical rows into one field or split one row into extras. `check_row_shape.py` detects the resulting wrong column counts directly; `check_max_field_length.py` is a plausibility check (an outlier-large `text` field is a hint that rows got merged). Both scripts raise `csv.field_size_limit` before parsing since stdlib's default limit is too low for full article bodies.

All scripts (`dedup.py`, `sample_test_data.py`) that read the raw corpus CSV set `csv.field_size_limit(472_327)`, a value determined by running `check_max_field_length.py` against the actual corpus — don't lower it without re-checking against current data.

## Datatrove dependency extras

`datatrove` ships most of its actual functionality behind optional extras rather than as base dependencies. This pipeline needs `datatrove[processing,io]` (see `Pipfile`) — `processing` for `regex`/`tokenizers`/`xxhash` (used by the MinHash stages and tokenizer), `io` for `orjson` and the CSV/JSONL reader/writer backends. Don't install plain `datatrove` or `datatrove[all]`: the former is missing required transitive deps and fails at import/runtime with `ModuleNotFoundError`/`ImportError`; the latter pulls in extras with native deps that can fail to build.
