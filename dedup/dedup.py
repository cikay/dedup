"""Near-dedup pipeline mirroring datatrove's fineweb.py MinHash example, run
entirely on a single machine (LocalPipelineExecutor) against a small sample
(see sample_test_data.py).

Usage (run from the repo root):
    pipenv run python -m dedup.dedup --input data/test_sample.csv --output-dir data/datatrove_test
"""

import argparse
import csv

# datatrove's CsvReader uses the stdlib csv module without raising this limit;
# large articles otherwise trip "_csv.Error: field larger than field limit".
csv.field_size_limit(472_327)  # detected by check_max_field_length.py

from datatrove.executor.local import LocalPipelineExecutor
from datatrove.pipeline.dedup.minhash import (
    MinhashConfig,
    MinhashDedupBuckets,
    MinhashDedupCluster,
    MinhashDedupFilter,
    MinhashDedupSignature,
)
from datatrove.pipeline.filters.lambda_filter import LambdaFilter
from datatrove.pipeline.readers.csv import CsvReader
from datatrove.pipeline.writers.jsonl import JsonlWriter
from datatrove.utils.hashing import HashConfig

from dedup.tokenizer import WhitespaceWordTokenizer

CSV_COLUMNS = [
    "lang",
    "lang_score",
    "publish_date",
    "publisher",
    "source_type",
    "text",
    "title",
    "url",
    "word_count",
]


def is_valid_data_row(doc) -> bool:
    fields = {"text": doc.text, "url": doc.id, **doc.metadata}
    return not all(fields.get(col) == col for col in CSV_COLUMNS)


def get_reader(data_folder, glob_pattern):
    # Same reader config must be reused for both the signature stage and the
    # final filter stage: MinhashDedupFilter matches removals by (rank, doc
    # index within that rank), not by content, so the two reads must line up.
    return CsvReader(
        data_folder=data_folder,
        glob_pattern=glob_pattern,
        text_key="text",
        id_key="url",
    )


def get_corrupted_row_filter(exclusion_writer=None):
    # Must run identically right after get_reader() in both the signature and
    # filter stages, same reason as get_reader() above: it's a deterministic
    # function of row content, so both reads drop the same rows in the same
    # order and stay aligned.
    return LambdaFilter(is_valid_data_row, exclusion_writer=exclusion_writer)


def main():
    parser = argparse.ArgumentParser(description="datatrove MinHash near-dedup test pipeline")
    parser.add_argument("--input", default="data/test_sample.csv")
    parser.add_argument("--output-dir", default="data/datatrove_test")
    args = parser.parse_args()

    input_folder, glob_pattern = args.input.rsplit("/", 1)
    base = args.output_dir

    # datatrove's own fineweb.py example (b=14, r=8, shingle_size=5).
    minhash_config = MinhashConfig(
        n_grams=5,
        num_buckets=14,
        hashes_per_bucket=8,
        hash_config=HashConfig(precision=64),
    )
    tokenizer = WhitespaceWordTokenizer()

    stage1 = LocalPipelineExecutor(
        pipeline=[
            get_reader(input_folder, glob_pattern),
            get_corrupted_row_filter(exclusion_writer=JsonlWriter(f"{base}/removed_corrupted")),
            MinhashDedupSignature(
                output_folder=f"{base}/signatures",
                config=minhash_config,
                language=tokenizer,
            ),
        ],
        tasks=1,
        logging_dir=f"{base}/logs/signatures",
    )

    stage2 = LocalPipelineExecutor(
        pipeline=[
            MinhashDedupBuckets(
                input_folder=f"{base}/signatures",
                output_folder=f"{base}/buckets",
                config=minhash_config,
            ),
        ],
        tasks=minhash_config.num_buckets,
        logging_dir=f"{base}/logs/buckets",
        depends=stage1,
    )

    stage3 = LocalPipelineExecutor(
        pipeline=[
            MinhashDedupCluster(
                input_folder=f"{base}/buckets",
                output_folder=f"{base}/remove_ids",
                config=minhash_config,
                save_cluster_size=True,
            ),
        ],
        tasks=1,
        logging_dir=f"{base}/logs/cluster",
        depends=stage2,
    )

    stage4 = LocalPipelineExecutor(
        pipeline=[
            get_reader(input_folder, glob_pattern),
            get_corrupted_row_filter(),
            MinhashDedupFilter(
                input_folder=f"{base}/remove_ids",
                exclusion_writer=JsonlWriter(f"{base}/removed"),
                load_cluster_sizes=True,
            ),
            JsonlWriter(f"{base}/deduped"),
        ],
        tasks=1,
        logging_dir=f"{base}/logs/filter",
        depends=stage3,
    )

    stage4.run()
    print(f"\n[datatrove] Kept articles:   {base}/deduped/")
    print(f"[datatrove] Removed dupes:   {base}/removed/")
    print(f"[datatrove] Cluster metadata: {base}/remove_ids/")


if __name__ == "__main__":
    main()
