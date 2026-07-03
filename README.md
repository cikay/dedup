# dedup

A near-duplicate detection pipeline for a multilingual news-article text corpus (Kurmanji Kurdish `kmr_Latn`, Sorani Kurdish `ckb_Arab`, Zazaki `diq_Latn`), built on top of [datatrove](https://github.com/huggingface/datatrove)'s MinHash implementation. The corpus itself (CSV files with `url`/`text`/`lang`/`publisher` columns) lives outside this repo under `data/`.

## Setup

```
pipenv install
```

## Usage

Run the near-dedup pipeline:
```
pipenv run python -m dedup.dedup --input data/test_sample.csv --output-dir data/datatrove_test
```

Build a small, outlet-diverse test sample from a full corpus dump:
```
pipenv run python dedup/sample_test_data.py --input data/output.csv --output data/test_sample.csv
```

CSV data-quality checks:
```
pipenv run python dedup/check_max_field_length.py data/output.csv
pipenv run python dedup/check_row_shape.py data/output.csv
```

Run tests:
```
pipenv run pytest
```
