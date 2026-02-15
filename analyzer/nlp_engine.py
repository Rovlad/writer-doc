"""
Natasha NLP engine — singleton that loads models once and provides
a processed Doc object with morphology, lemmas, and syntax.

Natasha gives us:
  - Segmenter        → sentence / token segmentation
  - NewsMorphTagger   → POS tags + grammatical features (Universal Dependencies)
  - NewsSyntaxParser  → dependency relations (head_id, rel)
  - MorphVocab        → lemmatisation
  - NewsEmbedding     → word vectors used internally by tagger & parser

POS tags follow Universal Dependencies v2:
  NOUN, VERB, ADJ, ADV, PROPN, DET, ADP, PRON, CCONJ, SCONJ, PART, NUM, PUNCT, SYM, X, INTJ
"""

from natasha import (
    Segmenter,
    MorphVocab,
    NewsEmbedding,
    NewsMorphTagger,
    NewsSyntaxParser,
    Doc,
)

# ── Singleton models ──────────────────────────────────────────────
_segmenter: Segmenter | None = None
_morph_vocab: MorphVocab | None = None
_emb: NewsEmbedding | None = None
_morph_tagger: NewsMorphTagger | None = None
_syntax_parser: NewsSyntaxParser | None = None


def _ensure_loaded():
    """Lazy-load heavy models on first call."""
    global _segmenter, _morph_vocab, _emb, _morph_tagger, _syntax_parser
    if _segmenter is not None:
        return
    print("[nlp_engine] Loading Natasha models …")
    _segmenter = Segmenter()
    _morph_vocab = MorphVocab()
    _emb = NewsEmbedding()
    _morph_tagger = NewsMorphTagger(_emb)
    _syntax_parser = NewsSyntaxParser(_emb)
    print("[nlp_engine] Models ready.")


def process_text(text: str) -> Doc:
    """
    Run the full Natasha pipeline on *text* and return a Doc whose
    tokens carry: text, pos, feats, lemma, id, head_id, rel.
    """
    _ensure_loaded()
    doc = Doc(text)
    doc.segment(_segmenter)
    doc.tag_morph(_morph_tagger)

    # Lemmatise each token using MorphVocab
    for token in doc.tokens:
        token.lemmatize(_morph_vocab)

    doc.parse_syntax(_syntax_parser)
    return doc
