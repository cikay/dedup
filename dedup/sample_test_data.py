import argparse
import csv
import random
import sys
from collections import defaultdict

csv.field_size_limit(472_327)

DEFAULT_TARGETS = {
    "kmr_Latn": 800,
    "ckb_Arab": 800,
    "diq_Latn": 200,
}

# The real corpus has ~55 rows where every column's value equals its own
# column name -- leftover header rows from concatenating scrape output files
# (see dedup.dedup.is_valid_data_row). Injecting a few into the test sample
# keeps that corruption reproducible in a small file instead of only ever
# showing up in the full corpus.
NUM_HEADER_ROWS = 3


def make_header_row(fieldnames):
    return {col: col for col in fieldnames}


def collect_reservoirs(input_path, targets, rng):
    """Single streaming pass. Keeps a per-(lang, publisher) reservoir capped at
    the language's target count, so no single dominant outlet (e.g.
    jinhaagency.com at ~52% of kmr_Latn) fills the reservoir before smaller
    outlets get a chance."""
    reservoirs = {lang: defaultdict(list) for lang in targets}
    seen = {lang: defaultdict(int) for lang in targets}

    with open(input_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            lang = row.get("lang")
            if lang not in targets:
                continue
            pub = row.get("publisher", "")
            cap = targets[lang]

            seen[lang][pub] += 1
            k = seen[lang][pub]
            res = reservoirs[lang][pub]
            if len(res) < cap:
                res.append(row)
            else:
                j = rng.randint(0, k - 1)
                if j < cap:
                    res[j] = row

            if (i + 1) % 1_000_000 == 0:
                print(f"  scanned {i + 1:,} rows...", file=sys.stderr)

    return reservoirs


def round_robin_select(publisher_rows, target_count, rng):
    """Cycle through publishers one row at a time so the sample spreads across
    outlets instead of being proportional to (and dominated by) raw volume."""
    pools = {pub: list(rows) for pub, rows in publisher_rows.items()}
    for rows in pools.values():
        rng.shuffle(rows)

    pubs = list(pools.keys())
    rng.shuffle(pubs)

    selected = []
    idx = 0
    while len(selected) < target_count and pubs:
        pub = pubs[idx % len(pubs)]
        if pools[pub]:
            selected.append(pools[pub].pop())
            idx += 1
        else:
            pubs.remove(pub)
            # don't advance idx: same slot now holds the next publisher

    return selected


def main():
    targets = dict(DEFAULT_TARGETS)

    rng = random.Random(42)
    input = "data/scrapy_final_data.csv"
    output = "data/test_sample.csv"

    print(f"[sample] Scanning {input} for {targets}...")
    reservoirs = collect_reservoirs(input, targets, rng)

    fieldnames = None
    all_selected = []
    for lang, count in targets.items():
        publisher_rows = reservoirs[lang]
        n_publishers = len(publisher_rows)
        available = sum(len(rows) for rows in publisher_rows.values())
        selected = round_robin_select(publisher_rows, count, rng)
        used_publishers = len({row["publisher"] for row in selected})
        print(
            f"[sample] {lang}: {len(selected)}/{count} rows from "
            f"{used_publishers}/{n_publishers} publishers (pool={available:,})"
        )
        if selected and fieldnames is None:
            fieldnames = list(selected[0].keys())
        all_selected.extend(selected)

    all_selected.extend(make_header_row(fieldnames) for _ in range(NUM_HEADER_ROWS))
    print(f"[sample] Injected {NUM_HEADER_ROWS} duplicated-header rows")

    rng.shuffle(all_selected)

    with open(output, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_selected)

    print(f"[sample] Wrote {len(all_selected)} rows to {output}")


if __name__ == "__main__":
    main()
