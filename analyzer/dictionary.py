"""
Dictionary builder — for every unique lemma in the text, records:
  • lemma (base form)
  • POS tag
  • count (total frequency)
  • surface_forms — set of original word-forms found
  • example — a text snippet where the word appears
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from natasha import Doc

# POS tags to include in the dictionary (skip punctuation, symbols)
INCLUDE_POS = {"NOUN", "ADJ", "VERB", "ADV", "PROPN", "PRON", "NUM", "DET", "INTJ"}


def build_dictionary(doc: Doc) -> list[dict[str, Any]]:
    """
    Return a list of dictionary entries sorted by frequency (desc):
    [
        {
            "lemma": str,
            "pos":   str,   # UD tag
            "count": int,
            "surface_forms": [str, …],
            "example": str  # short context snippet
        },
        …
    ]
    """
    # (lemma, pos) → data
    entries: dict[tuple[str, str], dict] = {}
    form_sets: dict[tuple[str, str], set] = defaultdict(set)
    freq: Counter = Counter()

    for token in doc.tokens:
        if token.pos not in INCLUDE_POS:
            continue
        lemma = (token.lemma or token.text).lower()
        pos = token.pos
        key = (lemma, pos)
        freq[key] += 1
        form_sets[key].add(token.text.lower())

        # Store first occurrence's context as example
        if key not in entries:
            example = _extract_context(doc, token, window=6)
            entries[key] = {
                "lemma": lemma,
                "pos": pos,
                "count": 0,
                "surface_forms": [],
                "example": example,
            }

    # Merge counts and forms
    result = []
    for key, cnt in freq.most_common():
        entry = entries[key]
        entry["count"] = cnt
        entry["surface_forms"] = sorted(form_sets[key])
        result.append(entry)

    return result


def _extract_context(doc: Doc, target_token, window: int = 6) -> str:
    """Return a small snippet of text around *target_token*."""
    tokens = doc.tokens
    # Find index of target token
    idx = None
    for i, t in enumerate(tokens):
        if t is target_token:
            idx = i
            break
    if idx is None:
        return target_token.text

    start = max(0, idx - window)
    end = min(len(tokens), idx + window + 1)
    words = [t.text for t in tokens[start:end]]
    return " ".join(words)
