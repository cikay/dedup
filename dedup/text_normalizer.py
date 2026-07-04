import unicodedata

from datatrove.pipeline.formatters.base import BaseFormatter


class NFCNormalizer(BaseFormatter):
    # Kurdish sources (kmr_Latn, ckb_Arab) mix precomposed and decomposed
    # Unicode forms for the same visible character (e.g. an accented Latin
    # letter or an Arabic-script letter+diacritic pair). Without canonicalizing
    # to NFC first, exact-dedup hashing and MinHash shingling see visually
    # identical text as different byte sequences and miss matches.
    name = "🔤 NFC Normalize"

    def format(self, text: str) -> str:
        return unicodedata.normalize("NFC", text)
