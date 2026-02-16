"""
Supabase storage client.

Saves the full analysis JSON to a Supabase table.  Requires the
following environment variables (set in .env):

    SUPABASE_URL=https://xxxx.supabase.co
    SUPABASE_KEY=eyJhbGci...

Table schema (run this SQL in Supabase SQL Editor):

    CREATE TABLE text_analyses (
        id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        created_at  TIMESTAMPTZ DEFAULT now(),
        filename    TEXT,
        char_count  INTEGER,
        word_count  INTEGER,
        processing_time FLOAT,
        dictionary  JSONB,
        statistics  JSONB,
        collocations JSONB
    );

    -- Optional: index for fast lookups
    CREATE INDEX idx_analyses_created ON text_analyses (created_at DESC);
"""

from __future__ import annotations

from typing import Any

from config import Config


def _get_client():
    """Lazy import + init so the app starts even without supabase creds."""
    if not Config.SUPABASE_URL or not Config.SUPABASE_KEY:
        raise RuntimeError(
            "Supabase credentials not configured.  "
            "Set SUPABASE_URL and SUPABASE_KEY in your .env file."
        )
    from supabase import create_client

    return create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)


def save_to_supabase(
    analysis: dict[str, Any],
    filename: str = "untitled.txt",
) -> dict:
    """
    Insert a row into the text_analyses table and return the inserted record.
    """
    client = _get_client()

    row = {
        "filename": filename,
        "char_count": analysis["meta"]["char_count"],
        "word_count": analysis["statistics"]["total_words"],
        "processing_time": analysis["meta"]["processing_time_sec"],
        "dictionary": analysis["dictionary"],
        "statistics": analysis["statistics"],
        "collocations": analysis["collocations"],
    }

    result = (
        client.table(Config.SUPABASE_TABLE)
        .insert(row)
        .execute()
    )
    return result.data[0] if result.data else {}


def list_saved_analyses(limit: int = 20) -> list[dict]:
    """Return recent saved analyses (metadata only)."""
    client = _get_client()
    result = (
        client.table(Config.SUPABASE_TABLE)
        .select("id, created_at, filename, char_count, word_count, processing_time")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


def load_analysis(analysis_id: str) -> dict | None:
    """Load a full analysis by its UUID."""
    client = _get_client()
    result = (
        client.table(Config.SUPABASE_TABLE)
        .select("*")
        .eq("id", analysis_id)
        .single()
        .execute()
    )
    return result.data


def delete_analysis(analysis_id: str) -> bool:
    """Delete an analysis by its UUID. Returns True if deleted."""
    client = _get_client()
    result = (
        client.table(Config.SUPABASE_TABLE)
        .delete()
        .eq("id", analysis_id)
        .execute()
    )
    return True
