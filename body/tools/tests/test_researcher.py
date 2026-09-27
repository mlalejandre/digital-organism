#!/usr/bin/env python3
"""Tests del órgano investigador sin llamadas de red."""

from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOLS_DIR))

import researcher  # noqa: E402


def test_slugify() -> bool:
    value = researcher.slugify(
        "Farmacocinética clínica / dosis"
    )
    return bool(value) and " " not in value and "/" not in value


def test_canonical_url() -> bool:
    source = "https://example.org/a/?utm_source=x&b=2#g"
    result = researcher.canonical_url(source)
    return result == "https://example.org/a?b=2"


def test_query_plan() -> bool:
    plan = researcher.build_query_plan(
        "nefrologia",
        "calculo de filtrado glomerular",
    )
    identifiers = {
        item["id"]
        for item in plan
    }
    expected = {
        "scope",
        "path",
        "skills",
        "tools",
        "official",
        "pitfalls",
        "current",
    }
    return expected.issubset(identifiers)


def test_source_score() -> bool:
    source = researcher.make_source(
        title="Official Python API documentation",
        url="https://docs.python.org/3/",
        snippet="Official API documentation",
        source_type="web_search",
        relevance=0.9,
        updated="2026-01-01",
    )
    score = researcher.score_source(
        source,
        "Python official API documentation",
    )
    return score > 0.45


def test_markdown() -> bool:
    report = {
        "meta": {
            "specialty": "demo",
            "mission": "demo mission",
            "generated_at": "2026-01-01T00:00:00Z",
            "query_count": 1,
            "source_count": 0,
        },
        "capabilities": {
            "skills_hints": ["python"],
            "tool_hints": ["github"],
        },
        "open_questions": ["¿Qué falta validar?"],
        "priority_sources": [],
    }
    text = researcher.to_markdown(report)
    return (
        "# Nail-StemCell" in text
        and "demo" in text
        and "python" in text
    )


def main() -> int:
    tests = [
        test_slugify,
        test_canonical_url,
        test_query_plan,
        test_source_score,
        test_markdown,
    ]

    failures = []

    for test in tests:
        try:
            ok = bool(test())
        except Exception as exc:
            ok = False
            failures.append(
                f"{test.__name__}: "
                f"{type(exc).__name__}: {exc}"
            )

        if ok:
            print(f"[OK] {test.__name__}")
        elif not any(
            failure.startswith(test.__name__ + ":")
            for failure in failures
        ):
            failures.append(
                f"{test.__name__}: assertion failed"
            )

    if failures:
        print("\n[FAIL]")
        for failure in failures:
            print(" -", failure)
        return 1

    print("\n[OK] All researcher tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
