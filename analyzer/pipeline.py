"""
Main analysis pipeline.

Call  analyze_text(raw_text)  →  returns a complete result dict ready for
the Flask views and JSON export.
"""

from __future__ import annotations

import time
from typing import Any

from .nlp_engine import process_text
from .dictionary import build_dictionary
from .statistics import compute_statistics
from .collocations import extract_noun_adj_pairs


def analyze_text(text: str, top_n: int = 100) -> dict[str, Any]:
    """
    Full analysis pipeline.

    Returns
    -------
    {
        "meta": {
            "char_count": int,
            "processing_time_sec": float,
        },
        "dictionary": [ {lemma, pos, count, surface_forms, example}, … ],
        "statistics": { … },
        "collocations": {
            "noun_adj_index": { noun: [{adj, count, examples}] },
            "adj_noun_index": { adj: [{noun, count}] },
            "pair_list":      [ {noun, adj, count, examples} ],
            "total_pairs": int,
            "unique_pairs": int,
        },
    }
    """
    t0 = time.perf_counter()

    # 1. Run NLP pipeline
    doc = process_text(text)

    # 2. Build dictionary
    dictionary = build_dictionary(doc)

    # 3. Compute statistics
    stats = compute_statistics(doc, top_n=top_n)

    # 4. Extract noun-adjective collocations
    collocations = extract_noun_adj_pairs(doc)

    elapsed = round(time.perf_counter() - t0, 2)

    return {
        "meta": {
            "char_count": len(text),
            "processing_time_sec": elapsed,
        },
        "dictionary": dictionary,
        "statistics": stats,
        "collocations": collocations,
    }
