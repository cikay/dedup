"""Run from the repo root:
    pipenv run pytest tests/test_tokenizer.py
"""

import pytest

from dedup.tokenizer import WhitespaceWordTokenizer


@pytest.fixture
def tokenizer():
    return WhitespaceWordTokenizer()


def test_splits_on_whitespace(tokenizer):
    assert tokenizer.word_tokenize("ez hatim") == ["ez", "hatim"]


def test_splits_on_any_whitespace_run(tokenizer):
    assert tokenizer.word_tokenize("ez   îro\n\tdiçim") == ["ez", "îro", "diçim"]


def test_lowercases(tokenizer):
    assert tokenizer.word_tokenize("EZ DIXWAZIM BÊM") == ["ez", "dixwazim", "bêm"]


def test_strips_punctuation_from_kurmanji_latin_text(tokenizer):
    assert tokenizer.word_tokenize("Silav, tu çawa yî?") == ["silav", "tu", "çawa", "yî"]


def test_strips_punctuation_from_sorani_arabic_script_text(tokenizer):
    # ، and ؟ are Arabic-script comma/question mark; \w matches Arabic
    # letters, so they're stripped the same way Latin punctuation is.
    assert tokenizer.word_tokenize("سڵاو، چۆنیت؟") == ["سڵاو", "چۆنیت"]


def test_empty_string_returns_no_tokens(tokenizer):
    assert tokenizer.word_tokenize("") == []


def test_punctuation_only_string_returns_no_tokens(tokenizer):
    assert tokenizer.word_tokenize("... !? ,,,") == []


def test_sent_tokenize_not_implemented(tokenizer):
    with pytest.raises(NotImplementedError):
        tokenizer.sent_tokenize("Some text.")


def test_span_tokenize_not_implemented(tokenizer):
    with pytest.raises(NotImplementedError):
        tokenizer.span_tokenize("Some text.")
