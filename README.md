# Словарь Писателя (Writer's Dictionary)

A Python/Flask tool for analysing Russian literary texts — extracts a full dictionary, word statistics, noun–adjective collocations, and provides an interactive search interface.

## Features

1. **Upload** a `.txt` file (UTF-8 or Windows-1251)
2. **Text dictionary** — every unique lemma with POS, frequency, surface forms, and context
3. **Statistics** — top-100 most frequent nouns, adjectives, verbs, adverbs; POS distribution; vocabulary richness
4. **Noun → Adjective index** — for every noun, lists all adjectives found near it (via dependency parsing + window)
5. **Interactive search** — type any noun and get its adjectives ranked by frequency
6. **Export** results as JSON **or save to Supabase**

## Tech Stack

| Layer      | Technology                                |
|------------|-------------------------------------------|
| NLP Engine | **Natasha** (tokenisation, morphology, syntax parsing, lemmatisation) |
| Backend    | **Flask** (Python 3.10+)                  |
| Frontend   | Jinja2 templates + vanilla JS + CSS       |
| Database   | **Supabase** (PostgreSQL) — optional       |

### Why Natasha?

Natasha is purpose-built for Russian NLP. It provides:
- **POS tagging** using Universal Dependencies tags (NOUN, ADJ, VERB, …)
- **Lemmatisation** via MorphVocab
- **Dependency parsing** — the `amod` relation links adjectives to their head nouns *syntactically*, which is far more accurate than simple window-based co-occurrence

Models are compact (~27 MB), run on CPU, and require no GPU.

## Project Structure

```
writer-dict/
├── app.py                      # Flask application & routes
├── config.py                   # Configuration (env vars)
├── requirements.txt
├── .env.example                # Template for environment variables
│
├── analyzer/
│   ├── __init__.py
│   ├── nlp_engine.py           # Natasha model singleton
│   ├── dictionary.py           # Lemma dictionary builder
│   ├── statistics.py           # Frequency & POS statistics
│   ├── collocations.py         # Noun–adjective pair extraction
│   └── pipeline.py             # Orchestrator: text → full result
│
├── storage/
│   ├── __init__.py
│   ├── json_export.py          # JSON serialisation
│   └── supabase_client.py      # Supabase CRUD
│
├── templates/
│   ├── base.html               # Layout with nav
│   ├── index.html              # Upload page
│   ├── results.html            # Analysis dashboard (4 tabs)
│   └── history.html            # Saved analyses list
│
├── static/
│   ├── css/style.css
│   └── js/app.js
│
└── uploads/                    # Temporary file storage
```

## Quick Start

### 1. Clone & install

```bash
cd writer-dict
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env — at minimum set SECRET_KEY
# For Supabase: set SUPABASE_URL and SUPABASE_KEY
```

### 3. (Optional) Set up Supabase table

Run this SQL in your Supabase SQL Editor:

```sql
CREATE TABLE text_analyses (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at      TIMESTAMPTZ DEFAULT now(),
    filename        TEXT,
    char_count      INTEGER,
    word_count      INTEGER,
    processing_time FLOAT,
    dictionary      JSONB,
    statistics      JSONB,
    collocations    JSONB
);

CREATE INDEX idx_analyses_created ON text_analyses (created_at DESC);
```

### 4. Run

```bash
python app.py
```

Open **http://localhost:5000** in your browser.

## API Endpoints

| Method | Path                | Description                           |
|--------|---------------------|---------------------------------------|
| GET    | `/`                 | Upload page                           |
| POST   | `/analyze`          | Upload file & run analysis            |
| GET    | `/results`          | Results dashboard                     |
| GET    | `/api/search?noun=` | Search adjectives for a noun (JSON)   |
| GET    | `/api/export`       | Download full analysis as JSON        |
| POST   | `/api/save`         | Save current analysis to Supabase     |
| GET    | `/history`          | List saved analyses                   |
| GET    | `/history/<id>`     | Load a saved analysis                 |

## How Noun–Adjective Extraction Works

Two strategies are combined:

1. **Dependency parsing** (primary) — Natasha's syntax parser marks `amod` (adjectival modifier) relations. If token B has `rel="amod"` and its `head_id` points to token A where A is a NOUN, we record the pair `(A.lemma, B.lemma)`.

2. **Window-based** (fallback) — for poetry where syntax parsing may miss relations, we scan ±2 tokens around every NOUN for ADJ tokens.

Both strategies are deduplicated and merged by lemma pair.

## Performance Notes

- **First request** takes ~3–5 seconds to load Natasha models into memory
- **Subsequent analyses** are fast: ~1–5 seconds for typical texts (10k–100k characters)
- For very large texts (500k+ chars) processing may take 30–60 seconds
- Models use ~200 MB RAM
