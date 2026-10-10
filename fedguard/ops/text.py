"""Text features that need no model."""
from __future__ import annotations



def split_words(text: str) -> list[str]:
    """Whitespace-separated words, punctuation attached."""
    return text.split()


def leave_one_out(words: list[str]) -> list[str]:
    """The n texts obtained by deleting one word each."""
    return [" ".join(words[:i] + words[i + 1:]) for i in range(len(words))]


def outlier_words(base: float, without: list[float], bar: float = 0.0) -> list[int]:
    """ONION's rule on perplexities: word i is suspicious when deleting it lowers the perplexity by
    more than `bar` (f_i = base - without_i > bar). Returns the indices."""
    return [i for i, p in enumerate(without) if base - p > bar]
