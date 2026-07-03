"""Scan a CSV for row-shape corruption.

A stray/unescaped quote earlier in the file can make the csv parser merge
multiple physical rows into one field, or split one row's field into
extras -- either way the row ends up with the wrong column count.
csv.field_size_limit alone won't catch this: a moderately merged row can
still land far under the limit and pass through silently.

Usage:
    python dedup/check_row_shape.py data/output.csv
"""

import argparse
import csv
import gzip

csv.field_size_limit(10_000_000)


def _open_csv(path: str):
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8")
    return open(path, encoding="utf-8", newline="")


def row_shape_error(row: dict) -> str | None:
    """DictReader surfaces a bad row via the `None` key (extra columns,
    restkey) or `None` values (missing columns, restval)."""
    extra = row.get(None)
    if extra is not None:
        return f"{len(extra)} extra column(s): {extra!r}"
    missing = [k for k, v in row.items() if v is None]
    if missing:
        return f"missing column(s): {missing!r}"
    return None


def main():
    parser = argparse.ArgumentParser(description="Check a CSV for row-shape corruption (merged/split rows)")
    parser.add_argument("input", help="Path to a CSV file (.csv or .csv.gz)")
    args = parser.parse_args()

    total = 0
    bad = 0
    with _open_csv(args.input) as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=1):
            total += 1
            error = row_shape_error(row)
            if error:
                bad += 1
                print(f"row {i}: {error}")

    print(f"\n{total:,} rows checked, {bad:,} malformed")


if __name__ == "__main__":
    main()
