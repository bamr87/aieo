"""Common helpers used by lightweight analyzers."""

from __future__ import annotations

import re
from typing import List


WORD_RE = re.compile(r"\b[\w'-]+\b")
SENTENCE_RE = re.compile(r"[^.!?]+[.!?]?")


def words(text: str) -> List[str]:
    return WORD_RE.findall(text.lower())


def word_count(text: str) -> int:
    return len(words(text))


def sentence_count(text: str) -> int:
    return max(1, len([s for s in SENTENCE_RE.findall(text) if s.strip()]))


def avg_sentence_length(text: str) -> float:
    wc = word_count(text)
    sc = sentence_count(text)
    return (wc / sc) if sc else 0.0


def top_terms(text: str, min_len: int = 4, limit: int = 20) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for token in words(text):
        if len(token) < min_len:
            continue
        counts[token] = counts.get(token, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    return ranked[:limit]
