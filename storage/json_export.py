"""
JSON export — serialises the analysis result to a downloadable JSON file.
"""

from __future__ import annotations

import json
from typing import Any


def export_json(analysis: dict[str, Any], pretty: bool = True) -> str:
    """Return analysis dict as a JSON string (UTF-8, Russian-safe)."""
    return json.dumps(
        analysis,
        ensure_ascii=False,
        indent=2 if pretty else None,
        default=str,
    )
