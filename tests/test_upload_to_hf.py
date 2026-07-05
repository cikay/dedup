"""Run from the repo root:
    pipenv run pytest tests/test_upload_to_hf.py
"""

from dedup.upload_to_hf import FEATURES, flatten


def record(text="Ev nûçeyek e li ser bûyereke girîng.", **metadata_overrides):
    metadata = {
        "lang": "kmr_Latn",
        "lang_score": "0.98",
        "publish_date": "2024-01-01",
        "publisher": "example.com",
        "source_type": "news",
        "title": "Serenav",
        "word_count": "120",
        "duplicate_count": 0,
        "minhash_cluster_size": 1,
        "file_path": "data/scrapy_final_data.csv",
    }
    metadata.update(metadata_overrides)
    return {
        "text": text,
        "id": "https://example.com/article-1",
        "metadata": metadata,
    }


def test_flattens_metadata_to_top_level_columns():
    row = flatten(record())
    assert row["url"] == "https://example.com/article-1"
    assert row["text"] == "Ev nûçeyek e li ser bûyereke girîng."
    assert row["lang"] == "kmr_Latn"
    assert row["lang_score"] == "0.98"
    assert row["publish_date"] == "2024-01-01"
    assert row["publisher"] == "example.com"
    assert row["title"] == "Serenav"


def test_word_count_is_computed_from_the_actual_text_not_metadata():
    row = flatten(record(text="one two three"))
    assert row["word_count"] == 3


def test_returns_exactly_the_features_columns():
    row = flatten(record())
    assert set(row.keys()) == set(FEATURES.keys())
