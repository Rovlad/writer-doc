"""
Text statistics: word counts, POS distribution, top-N per category,
vocabulary richness metrics.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from natasha import Doc

# POS tags we care about for "top N" lists
CONTENT_POS = {"NOUN", "ADJ", "VERB", "ADV", "PROPN"}

# Human-readable POS labels (Russian)
POS_LABELS_RU = {
    "NOUN": "Существительное",
    "ADJ": "Прилагательное",
    "VERB": "Глагол",
    "ADV": "Наречие",
    "PROPN": "Имя собственное",
    "PRON": "Местоимение",
    "DET": "Определитель",
    "ADP": "Предлог",
    "CCONJ": "Союз сочинит.",
    "SCONJ": "Союз подчинит.",
    "PART": "Частица",
    "NUM": "Числительное",
    "PUNCT": "Пунктуация",
    "INTJ": "Междометие",
    "SYM": "Символ",
    "X": "Прочее",
}


def compute_statistics(doc: Doc, top_n: int = 100) -> dict[str, Any]:
    """
    Return a statistics dict:
    {
        "total_tokens":  int,
        "total_words":   int,          # excl. PUNCT / SYM
        "unique_lemmas": int,
        "vocabulary_richness": float,   # unique / total_words
        "avg_word_length": float,
        "pos_distribution": { "NOUN": count, … },
        "pos_labels_ru":    { "NOUN": "Существительное", … },
        "top_nouns":  [ {"lemma": …, "count": …}, … ],
        "top_adj":    [ … ],
        "top_verbs":  [ … ],
        "top_adv":    [ … ],
        "top_propn":  [ … ],
    }
    """
    pos_counter: Counter = Counter()
    lemma_counters: dict[str, Counter] = {pos: Counter() for pos in CONTENT_POS}
    all_lemmas: Counter = Counter()
    total_chars = 0
    word_count = 0

    for token in doc.tokens:
        pos = token.pos
        lemma = (token.lemma or token.text).lower()
        pos_counter[pos] += 1

        if pos in ("PUNCT", "SYM"):
            continue

        word_count += 1
        total_chars += len(token.text)
        all_lemmas[lemma] += 1

        if pos in CONTENT_POS:
            lemma_counters[pos][lemma] += 1

    unique = len(all_lemmas)
    richness = round(unique / word_count * 100, 2) if word_count else 0
    avg_len = round(total_chars / word_count, 2) if word_count else 0

    def _top(pos: str) -> list[dict]:
        return [
            {"lemma": lemma, "count": cnt}
            for lemma, cnt in lemma_counters[pos].most_common(top_n)
        ]

    return {
        "total_tokens": len(doc.tokens),
        "total_words": word_count,
        "unique_lemmas": unique,
        "vocabulary_richness": richness,
        "avg_word_length": avg_len,
        "pos_distribution": dict(pos_counter.most_common()),
        "pos_labels_ru": POS_LABELS_RU,
        "top_nouns": _top("NOUN"),
        "top_adj": _top("ADJ"),
        "top_verbs": _top("VERB"),
        "top_adv": _top("ADV"),
        "top_propn": _top("PROPN"),
    }
