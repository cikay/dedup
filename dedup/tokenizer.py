import re

from datatrove.utils.word_tokenizers import WordTokenizer

# datatrove's tokenizer registry (tokenizer_assignment.csv) has no entry for
# kmr_Latn / ckb_Arab / diq_Latn. All three are whitespace-delimited scripts
# (Latin and Arabic-script Sorani both separate words with spaces), so a
# plain whitespace splitter is sufficient for MinHash word-shingling; sentence
# splitting is only required to satisfy the abstract base class and isn't
# used by the dedup stages.
_PUNCTUATION = re.compile(r"[^\w\s]", re.UNICODE)


class WhitespaceWordTokenizer(WordTokenizer):
    def word_tokenize(self, text: str) -> list[str]:
        return _PUNCTUATION.sub("", text.lower()).split()

    def sent_tokenize(self, text: str) -> list[str]:
        raise NotImplementedError("Sentence splitting is not implemented for this custom tokenizer")

    def span_tokenize(self, text: str) -> list[tuple[int, int]]:
        raise NotImplementedError("Span tokenization is not implemented for this custom tokenizer")
