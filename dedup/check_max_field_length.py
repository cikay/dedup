"""Report the maximum field length (in characters) per CSV column.

Useful as a plausibility check alongside csv.field_size_limit: if the
`text` column's max is in the hundreds of KB or more, that row is worth
opening manually -- a real single news article rarely gets that large, so
an outlier that big may be several rows merged together rather than one
long article (see check_row_shape.py for the corruption check itself).

Usage:
    python dedup/check_max_field_length.py data/output.csv
"""

import argparse
import csv
import gzip

csv.field_size_limit(10_000_000)


def _open_csv(path: str):
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8")
    return open(path, encoding="utf-8", newline="")


def main():
    parser = argparse.ArgumentParser(description="Report the max field length per CSV column")
    parser.add_argument("input", help="Path to a CSV file (.csv or .csv.gz)")
    parser.add_argument(
        "--id-key",
        default="url",
        help="Column used to identify the row that had the max length (default: url)",
    )
    args = parser.parse_args()

    max_len = {}
    max_row = {}
    total = 0

    with _open_csv(args.input) as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            for key, value in row.items():
                if key is None or value is None:
                    continue
                length = len(value)
                if length > max_len.get(key, -1):
                    max_len[key] = length
                    max_row[key] = row.get(args.id_key, "?")

    print(f"{total:,} rows checked\n")
    for key in sorted(max_len, key=lambda k: -max_len[k]):
        print(f"{key:15s} max_len={max_len[key]:>10,}  ({args.id_key}={max_row[key]!r})")


if __name__ == "__main__":
    main()
