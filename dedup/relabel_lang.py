"""Re-run language ID against an already-produced deduped/ output, refreshing
`lang`/`lang_score` in place with fresh model predictions.

The corpus's `lang`/`lang_score` fields are normally assigned once, at scrape
time, in the sibling sorjin_scrapy project (see extractor/text_extractor.py
and lang_model.py there). The dedup pipeline itself never touches them --
this script mirrors that same GlotLID model/logic so labels can be refreshed
after near-dedup without re-scraping.

Usage:
    pipenv run python -m dedup.relabel_lang data/dedep_test/deduped
"""

import argparse
import gzip
import json
import os
from glob import glob

import fasttext
from huggingface_hub import hf_hub_download

model_path = hf_hub_download(repo_id="cis-lmu/glotlid", filename="model_v3.bin")
language_model = fasttext.load_model(model_path)


def predict_lang(text: str) -> tuple[str, float]:
    labels, probs = language_model.predict(text.replace("\n", " "))
    lang = labels[0].replace("__label__", "")
    lang_score = round(probs[0], 3)
    return lang, lang_score


def relabel_file(path: str) -> None:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        records = [json.loads(line) for line in f]

    changed = 0
    for record in records:
        old_lang = record["metadata"].get("lang")
        lang, lang_score = predict_lang(record["text"])
        record["metadata"]["lang"] = lang
        record["metadata"]["lang_score"] = str(lang_score)
        if lang != old_lang:
            changed += 1

    tmp_path = f"{path}.tmp"
    with gzip.open(tmp_path, "wt", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    os.replace(tmp_path, path)

    print(f"{path}: {len(records)} rows processed, {changed} lang values changed")


def main():
    parser = argparse.ArgumentParser(description="Re-run language ID on a deduped/ directory")
    parser.add_argument("deduped_dir", help="Path to a deduped/ directory (e.g. data/dedep_test/deduped)")
    args = parser.parse_args()

    paths = sorted(glob(os.path.join(args.deduped_dir, "*.jsonl.gz")))
    if not paths:
        print(f"No *.jsonl.gz files found in {args.deduped_dir}")
        return

    for path in paths:
        relabel_file(path)


if __name__ == "__main__":
    main()
