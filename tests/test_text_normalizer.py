"""Run from the repo root:
    pipenv run pytest tests/test_text_normalizer.py
"""

import unicodedata

import pytest

from dedup.text_normalizer import NFCNormalizer

# The 10 Kurmanji Latin (kmr_Latn) letters beyond the plain ASCII alphabet.
# Each has a canonical NFD decomposition (base letter + combining diacritic),
# so a source that typed the combining-mark form needs NFC to match one that
# typed the single precomposed codepoint.
KURMANJI_LATIN_LETTERS = "ÇçÊêÎîŞşÛû"

# Kurdish-specific Sorani (ckb_Arab) letters. Unlike the Kurmanji ones above,
# these are atomic codepoints with no canonical decomposition -- NFC is a
# no-op for them, but they must still pass through unnormalized.
SORANI_ARABIC_LETTERS = "ڕڵۆێگچپژکی"


@pytest.fixture
def normalizer():
    return NFCNormalizer()


def test_leaves_already_nfc_text_unchanged(normalizer):
    assert normalizer.format("Ez hatim") == "Ez hatim"


@pytest.mark.parametrize("letter", list(KURMANJI_LATIN_LETTERS))
def test_composes_decomposed_kurmanji_latin_letter(normalizer, letter):
    decomposed = unicodedata.normalize("NFD", letter)
    assert decomposed != letter
    assert normalizer.format(decomposed) == letter


@pytest.mark.parametrize("letter", list(SORANI_ARABIC_LETTERS))
def test_leaves_sorani_arabic_letter_unchanged(normalizer, letter):
    assert normalizer.format(letter) == letter


def test_composes_decomposed_kurmanji_word(normalizer):
    # "şêr" (lion) with ş and ê typed as base letter + combining diacritic.
    decomposed = "s\N{COMBINING CEDILLA}e\N{COMBINING CIRCUMFLEX ACCENT}r"
    assert decomposed != "şêr"
    assert normalizer.format(decomposed) == "şêr"


def test_decomposed_and_precomposed_variants_match_after_normalizing(normalizer):
    decomposed = "e" + "\N{COMBINING ACUTE ACCENT}"
    precomposed = "é"
    assert normalizer.format(decomposed) == normalizer.format(precomposed)


def test_empty_string_returns_empty_string(normalizer):
    assert normalizer.format("") == ""
