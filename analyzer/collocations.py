"""
Noun–adjective collocation extractor.

Two strategies are combined for robust coverage:

1. **Dependency-based** (primary)  
   Natasha's syntax parser annotates each token with `head_id` and `rel`.
   We look for `rel == "amod"` (adjectival modifier) where the head is a NOUN
   and the dependent is ADJ or VERB (participles like «запертый» are often
   tagged as VERB but function as adjectives in amod position).

2. **Window-based** (fallback)  
   For poetry and highly elliptical prose the dependency parser may miss
   relations.  We scan a ±2-token window around every NOUN for ADJ
   tokens only.  (VERB/participles are excluded here to avoid false
   positives like «листья вдоль запертых окон» where «запертых» modifies
   «окон», not «листья».)

Both strategies store pairs as (noun_lemma, adj_lemma).  Duplicates are
merged and counts accumulated.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from natasha import Doc

# POS tags for adjective-like modifiers (ADJ + participles tagged as VERB)
ADJ_LIKE_POS = ("ADJ", "VERB")


def extract_noun_adj_pairs(doc: Doc) -> dict[str, Any]:
    """
    Return:
    {
        "noun_adj_index": {
            noun_lemma: [
                {"adj": adj_lemma, "count": int, "examples": [str, …]},
                …  (sorted by count desc)
            ]
        },
        "adj_noun_index": {
            adj_lemma: [
                {"noun": noun_lemma, "count": int},
                …
            ]
        },
        "pair_list": [
            {"noun": …, "adj": …, "count": …, "examples": […]},
            …  (sorted by count desc)
        ],
        "total_pairs": int,
        "unique_pairs": int,
    }
    """

    # ── pair_counter[(noun_lemma, adj_lemma)] → count ─────────────
    pair_counter: Counter = Counter()
    # Keep a few example surface-form phrases per pair
    pair_examples: dict[tuple[str, str], list[str]] = defaultdict(list)

    # ── Strategy 1: dependency-based ──────────────────────────────
    for sent in doc.sents:
        # Build token-id → token map for this sentence
        id_to_token = {t.id: t for t in sent.tokens}

        for token in sent.tokens:
            if token.rel == "amod" and token.pos in ADJ_LIKE_POS:
                head = id_to_token.get(token.head_id)
                if head and head.pos in ("NOUN", "PROPN"):
                    noun_lemma = (head.lemma or head.text).lower()
                    adj_lemma = (token.lemma or token.text).lower()
                    pair = (noun_lemma, adj_lemma)
                    pair_counter[pair] += 1
                    if len(pair_examples[pair]) < 3:
                        # Reconstruct a small surface phrase
                        tokens_sorted = sorted(
                            [head, token], key=lambda t: t.start if hasattr(t, 'start') and t.start else 0
                        )
                        phrase = " ".join(t.text for t in tokens_sorted)
                        if phrase not in pair_examples[pair]:
                            pair_examples[pair].append(phrase)

    # ── Strategy 2: window-based (±2 tokens) ─────────────────────
    tokens = list(doc.tokens)
    for i, token in enumerate(tokens):
        if token.pos not in ("NOUN", "PROPN"):
            continue
        noun_lemma = (token.lemma or token.text).lower()

        # Look in window [i-2 .. i+2]
        start = max(0, i - 2)
        end = min(len(tokens), i + 3)
        for j in range(start, end):
            if j == i:
                continue
            other = tokens[j]
            # Only ADJ in window (not VERB) to avoid false positives when
            # a participle modifies a different noun nearby, e.g. «листья вдоль запертых окон»
            if other.pos != "ADJ":
                continue
            adj_lemma = (other.lemma or other.text).lower()
            pair = (noun_lemma, adj_lemma)
            # Only add if not already found by dependency method
            if pair not in pair_counter:
                pair_counter[pair] += 1
                if len(pair_examples[pair]) < 3:
                    lo, hi = min(i, j), max(i, j)
                    phrase = " ".join(t.text for t in tokens[lo : hi + 1])
                    if phrase not in pair_examples[pair]:
                        pair_examples[pair].append(phrase)

    # ── Build output structures ───────────────────────────────────
    noun_adj_index: dict[str, list[dict]] = defaultdict(list)
    adj_noun_index: dict[str, list[dict]] = defaultdict(list)
    pair_list = []

    for (noun, adj), count in pair_counter.most_common():
        examples = pair_examples.get((noun, adj), [])
        pair_list.append(
            {"noun": noun, "adj": adj, "count": count, "examples": examples}
        )
        noun_adj_index[noun].append(
            {"adj": adj, "count": count, "examples": examples}
        )
        adj_noun_index[adj].append({"noun": noun, "count": count})

    # Sort each noun's adjectives by count descending
    for noun in noun_adj_index:
        noun_adj_index[noun].sort(key=lambda x: x["count"], reverse=True)
    for adj in adj_noun_index:
        adj_noun_index[adj].sort(key=lambda x: x["count"], reverse=True)

    return {
        "noun_adj_index": dict(noun_adj_index),
        "adj_noun_index": dict(adj_noun_index),
        "pair_list": pair_list,
        "total_pairs": sum(pair_counter.values()),
        "unique_pairs": len(pair_counter),
    }


def search_adjectives_for_noun(
    noun_adj_index: dict[str, list[dict]], query: str, limit: int = 20
) -> list[dict]:
    """
    Given a user query (a noun), return its top adjectives.
    Tries exact match first, then prefix match.
    """
    query_lower = query.strip().lower()
    if query_lower in noun_adj_index:
        return noun_adj_index[query_lower][:limit]

    # Fuzzy: prefix match
    matches = []
    for noun, adjs in noun_adj_index.items():
        if noun.startswith(query_lower):
            matches.extend(adjs)
    # Deduplicate & sort
    seen = set()
    result = []
    for item in sorted(matches, key=lambda x: x["count"], reverse=True):
        if item["adj"] not in seen:
            seen.add(item["adj"])
            result.append(item)
        if len(result) >= limit:
            break
    return result
