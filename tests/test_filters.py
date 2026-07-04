"""Run from the repo root:
    pipenv run pytest tests/test_filters.py
"""

from dataclasses import dataclass, field

from dedup.dedup import is_valid_data_row


@dataclass
class FakeDoc:
    text: str = ""
    id: str = ""
    metadata: dict = field(default_factory=dict)


def real_row(**overrides):
    doc = FakeDoc(
        text="Ev nûçeyek e li ser bûyereke girîng.",
        id="https://example.com/article-1",
        metadata={
            "lang": "kmr_Latn",
            "lang_score": "0.98",
            "publish_date": "2024-01-01",
            "publisher": "example.com",
            "source_type": "news",
            "title": "Serenav",
            "word_count": "120",
        },
    )
    for key, value in overrides.items():
        if key in ("text", "id"):
            setattr(doc, key, value)
        else:
            doc.metadata[key] = value
    return doc


def header_row():
    return FakeDoc(
        text="text",
        id="url",
        metadata={
            "lang": "lang",
            "lang_score": "lang_score",
            "publish_date": "publish_date",
            "publisher": "publisher",
            "source_type": "source_type",
            "title": "title",
            "word_count": "word_count",
        },
    )


def test_keeps_a_real_row():
    assert is_valid_data_row(real_row()) is True


def test_rejects_a_duplicated_header_row():
    assert is_valid_data_row(header_row()) is False


def test_keeps_a_row_where_only_one_column_coincidentally_matches_its_name():
    # text=="text" alone shouldn't be enough to flag a row -- it's the *whole*
    # row matching its own header that identifies real corruption.
    assert is_valid_data_row(real_row(text="text")) is True


def test_rejects_even_if_metadata_has_extra_keys():
    # BaseDiskReader injects a "file_path" key into metadata that isn't a CSV
    # column; it shouldn't stop a genuine header row from being detected.
    doc = header_row()
    doc.metadata["file_path"] = "scrapy_final_data.csv"
    assert is_valid_data_row(doc) is False
