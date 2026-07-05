"""Push a deduped/ output straight to the Hugging Face Hub, one language
config at a time, via datasets.Dataset.push_to_hub().

Reads and flattens data/dedep_final/deduped directly -- push_to_hub() builds
and uploads its own Parquet shards (capped at 500MB each by default)
internally, so nothing needs to be pre-staged on local disk first. This only
ever holds one Dataset.from_generator's worth of Arrow cache on disk at a
time (in HF's own cache dir), not a full extra copy of the corpus under
data/.

Does NOT touch the dataset card -- the card is written by hand.

Needs a token, either from `pipenv run hf auth login` (cached locally, no flag
needed), the HF_TOKEN environment variable, or --token below.

Usage:
    pipenv run python -m dedup.upload_to_hf --repo-id <your-username>/<dataset-name>
    pipenv run python -m dedup.upload_to_hf --repo-id <your-username>/<dataset-name> --private
    pipenv run python -m dedup.upload_to_hf --repo-id <your-username>/<dataset-name> --token hf_...
"""

import argparse
import gzip
import json
from glob import glob

from datasets import Dataset, Features, Value

# The three Kurdish varieties this whole pipeline targets (same set as
# dedup/tokenizer.py's script support and sample_test_data.py's DEFAULT_TARGETS).
LANGUAGES = ("kmr_Latn", "ckb_Arab", "diq_Latn")

FEATURES = Features(
    {
        "url": Value("string"),
        "text": Value("string"),
        "lang": Value("string"),
        "lang_score": Value("float32"),
        "publish_date": Value("string"),
        "publisher": Value("string"),
        "title": Value("string"),
        "word_count": Value("int32"),
    }
)


def flatten(record: dict) -> dict:
    md = record["metadata"]
    text = record["text"]
    return {
        "url": record["id"],
        "text": text,
        "lang": md.get("lang"),
        "lang_score": md.get("lang_score"),
        "publish_date": md.get("publish_date") or None,
        "publisher": md.get("publisher"),
        "title": md.get("title"),
        "word_count": len(text.split()) if text else None,
    }


def records_for_lang(input_dir, lang):
    for path in sorted(glob(f"{input_dir}/*.jsonl.gz")):
        with gzip.open(path, "rt", encoding="utf-8") as f:
            for line in f:
                row = flatten(json.loads(line))
                if row["lang"] == lang:
                    yield row


def main():
    parser = argparse.ArgumentParser(description="Push a deduped/ output to the Hugging Face Hub via datasets.push_to_hub")
    parser.add_argument("--repo-id", required=True, help="e.g. your-username/kurdish-web")
    parser.add_argument("--input", default="data/dedep_final/deduped")
    parser.add_argument("--split", required=True)
    parser.add_argument("--private", action="store_true")
    parser.add_argument(
        "--token",
        default=None,
        help="Defaults to the token from `hf auth login` or the HF_TOKEN env var if omitted",
    )
    args = parser.parse_args()

    for lang in LANGUAGES:
        print(f"building {lang} ...")
        ds = Dataset.from_generator(
            records_for_lang,
            gen_kwargs={"input_dir": args.input, "lang": lang},
            features=FEATURES,
        )
        if len(ds) == 0:
            print(f"skipping {lang}: no rows")
            continue
        print(f"pushing {lang} ({len(ds):,} rows) -> {args.repo_id}")
        ds.push_to_hub(args.repo_id, config_name=lang, split=args.split, private=args.private, token=args.token)

    print(f"done -> https://huggingface.co/datasets/{args.repo_id}")


if __name__ == "__main__":
    main()
