#!/usr/bin/env python3
"""
web_search.py - Capa de descubrimiento multi-fuente.

Mantiene la compatibilidad del proyecto:
    python3 tools/web_search.py "consulta"

Para investigación profunda:
    python3 tools/researcher.py --specialty "..." --mission "..."
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))

import researcher  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print(
            json.dumps(
                {"error": "Falta término"},
                ensure_ascii=False,
            )
        )
        return 1

    query = " ".join(sys.argv[1:]).strip()

    try:
        results = researcher.quick_search(query)
        print(
            json.dumps(
                {
                    "query": query,
                    "results": results,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    except Exception as exc:
        print(
            json.dumps(
                {
                    "query": query,
                    "results": [],
                    "error": f"{type(exc).__name__}: {exc}",
                },
                ensure_ascii=False,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
