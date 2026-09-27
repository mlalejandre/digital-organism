#!/usr/bin/env python3
"""
researcher.py - Órgano investigador de Nail-StemCell.

Función:
    Reducir progresivamente la incertidumbre de una misión de especialización.

No decide por sí mismo la arquitectura final ni crea un orquestador.
Su salida sirve al agente autogenerativo para decidir:
    - qué aprender;
    - qué leer;
    - qué herramientas construir o adoptar;
    - qué riesgos controlar;
    - qué pruebas deben demostrar competencia.

Fuentes públicas sin API key obligatoria:
    - DuckDuckGo HTML
    - PubMed E-utilities
    - OpenAlex
    - Crossref
    - GitHub REST

Artefactos persistentes:
    memory/research/latest.json
    memory/research/latest.md
    memory/research/<timestamp>_<specialty>.json
    memory/research/<timestamp>_<specialty>.md
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
MEMORY = ROOT / "memory"
RESEARCH = MEMORY / "research"

LATEST_JSON = RESEARCH / "latest.json"
LATEST_MD = RESEARCH / "latest.md"

USER_AGENT = (
    "Nail-StemCell-Researcher/3.0 "
    "(autonomous-domain-research; no-api-key-mode)"
)
TIMEOUT = 18


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def slugify(text: str, limit: int = 80) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^a-z0-9áéíóúüñ._-]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:limit] or "research"


def clean_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def truncate(text: str, limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit - 3] + "..."


def canonical_url(url: str) -> str:
    try:
        parsed = urllib.parse.urlsplit(url)
        pairs = urllib.parse.parse_qsl(
            parsed.query,
            keep_blank_values=True,
        )
        pairs = [
            (key, value)
            for key, value in pairs
            if not key.lower().startswith(
                ("utm_", "fbclid", "gclid", "mc_cid", "mc_eid")
            )
        ]
        query = urllib.parse.urlencode(pairs)
        path = re.sub(r"/+$", "", parsed.path or "")
        return urllib.parse.urlunsplit(
            (
                (parsed.scheme or "https").lower(),
                (parsed.hostname or "").lower(),
                path,
                query,
                "",
            )
        )
    except Exception:
        return url.strip()


def domain_of(url: str) -> str:
    try:
        return (urllib.parse.urlsplit(url).hostname or "").lower()
    except Exception:
        return ""


def http_get(url: str, accept: str, extra_headers: dict[str, str] | None = None) -> bytes:
    # [PARCHE-FIXES-V1:gh_token]
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": accept,
    }
    if extra_headers:
        headers.update(extra_headers)
    request = urllib.request.Request(
        url,
        headers=headers,
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.read()


def get_json(url: str, extra_headers: dict[str, str] | None = None) -> Any:
    body = http_get(url, "application/json", extra_headers=extra_headers)
    return json.loads(body.decode("utf-8", errors="replace"))


def source_quality(source_type: str, domain: str) -> str:
    if source_type == "github":
        return "tool_repository"

    official_suffixes = (
        ".gov",
        ".edu",
        ".int",
        "who.int",
        "fda.gov",
        "ema.europa.eu",
        "ec.europa.eu",
        "nist.gov",
        "iso.org",
        "python.org",
        "docs.python.org",
        "docs.docker.com",
        "kubernetes.io",
        "developer.mozilla.org",
        "ncbi.nlm.nih.gov",
    )

    if any(
        domain == item or domain.endswith(item)
        for item in official_suffixes
    ):
        return "official"

    if source_type in {"pubmed", "openalex", "crossref"}:
        return "primary"

    return "secondary"


def make_source(
    *,
    title: str,
    url: str,
    snippet: str = "",
    source_type: str = "web",
    published: str | None = None,
    updated: str | None = None,
    relevance: float = 0.5,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    url = canonical_url(url)
    domain = domain_of(url)
    return {
        "id": hashlib.sha1(url.encode("utf-8")).hexdigest()[:14],
        "title": truncate(clean_html(title), 260),
        "url": url,
        "domain": domain,
        "snippet": truncate(clean_html(snippet), 1400),
        "source_type": source_type,
        "source_quality": source_quality(source_type, domain),
        "published": published,
        "updated": updated,
        "relevance": round(float(relevance), 4),
        "evidence": evidence or {},
    }


def duckduckgo(query: str, limit: int = 8) -> list[dict[str, Any]]:
    url = (
        "https://html.duckduckgo.com/html/?q="
        + urllib.parse.quote_plus(query)
    )
    try:
        page = http_get(
            url,
            "text/html,application/xhtml+xml",
        ).decode("utf-8", errors="replace")
    except Exception:
        return []

    titles = re.findall(
        r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
        page,
        flags=re.I | re.S,
    )
    snippets = re.findall(
        r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
        page,
        flags=re.I | re.S,
    )

    out: list[dict[str, Any]] = []
    for i, (raw_url, raw_title) in enumerate(titles[:limit]):
        parsed = urllib.parse.urlparse(raw_url)
        if "duckduckgo.com" in (parsed.hostname or ""):
            values = urllib.parse.parse_qs(parsed.query)
            raw_url = values.get("uddg", [raw_url])[0]

        out.append(
            make_source(
                title=raw_title,
                url=raw_url,
                snippet=snippets[i] if i < len(snippets) else "",
                source_type="web_search",
                relevance=max(0.35, 0.78 - i * 0.045),
            )
        )

    return out


def pubmed(query: str, limit: int = 7) -> list[dict[str, Any]]:
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    search_url = (
        f"{base}esearch.fcgi?"
        f"db=pubmed&"
        f"term={urllib.parse.quote(query)}&"
        f"retmode=json&"
        f"retmax={max(1, min(limit, 20))}&"
        f"sort=date"
    )

    try:
        data = get_json(search_url)
    except Exception:
        return []

    ids = data.get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []

    summary_url = (
        f"{base}esummary.fcgi?"
        f"db=pubmed&"
        f"id={','.join(ids)}&"
        f"retmode=json"
    )

    try:
        summary = get_json(summary_url)
    except Exception:
        summary = {"result": {}}

    out: list[dict[str, Any]] = []
    for i, pmid in enumerate(ids):
        item = summary.get("result", {}).get(str(pmid), {})
        title = item.get("title") or f"PubMed PMID {pmid}"
        pubdate = item.get("pubdate")
        journal = item.get("fulljournalname") or ""
        out.append(
            make_source(
                title=title,
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                snippet=(
                    f"PMID={pmid}; journal={journal}; "
                    f"pubdate={pubdate or 'n/d'}"
                ),
                source_type="pubmed",
                published=pubdate,
                relevance=max(0.45, 0.94 - i * 0.045),
                evidence={"pmid": str(pmid)},
            )
        )
    return out


def openalex(query: str, limit: int = 7) -> list[dict[str, Any]]:
    params = {
        "search": query,
        "per-page": str(max(1, min(limit, 20))),
        "sort": "relevance_score:desc",
        "select": (
            "id,display_name,doi,publication_year,publication_date,"
            "primary_location,cited_by_count,is_retracted,type"
        ),
    }
    url = (
        "https://api.openalex.org/works?"
        + urllib.parse.urlencode(params)
    )

    try:
        data = get_json(url)
    except Exception:
        return []

    out: list[dict[str, Any]] = []
    for i, item in enumerate(data.get("results", [])):
        location = item.get("primary_location") or {}
        landing = (
            location.get("landing_page_url")
            or item.get("doi")
            or item.get("id")
        )
        if not landing:
            continue

        out.append(
            make_source(
                title=item.get("display_name") or "OpenAlex work",
                url=landing,
                snippet=(
                    f"year={item.get('publication_year')}; "
                    f"citations={item.get('cited_by_count', 0)}; "
                    f"type={item.get('type')}; "
                    f"retracted={item.get('is_retracted')}"
                ),
                source_type="openalex",
                published=item.get("publication_date"),
                relevance=max(0.42, 0.88 - i * 0.04),
                evidence={
                    "openalex_id": item.get("id"),
                    "doi": item.get("doi"),
                    "citations": item.get("cited_by_count", 0),
                    "is_retracted": item.get("is_retracted"),
                },
            )
        )
    return out


def crossref(query: str, limit: int = 7) -> list[dict[str, Any]]:
    params = {
        "query.bibliographic": query,
        "rows": str(max(1, min(limit, 20))),
        "select": (
            "DOI,title,URL,published,created,container-title,"
            "is-referenced-by-count,type"
        ),
    }
    url = (
        "https://api.crossref.org/works?"
        + urllib.parse.urlencode(params)
    )

    try:
        data = get_json(url)
    except Exception:
        return []

    out: list[dict[str, Any]] = []
    for i, item in enumerate(
        data.get("message", {}).get("items", [])
    ):
        titles = item.get("title") or []
        title = titles[0] if titles else item.get("DOI", "Crossref work")
        landing = item.get("URL")
        if not landing and item.get("DOI"):
            landing = f"https://doi.org/{item['DOI']}"
        if not landing:
            continue

        date_parts = (
            (item.get("published") or {}).get("date-parts")
            or (item.get("created") or {}).get("date-parts")
            or []
        )
        published = None
        if date_parts and date_parts[0]:
            published = "-".join(str(x) for x in date_parts[0])

        container = (item.get("container-title") or [""])[0]
        out.append(
            make_source(
                title=title,
                url=landing,
                snippet=(
                    f"DOI={item.get('DOI')}; container={container}; "
                    f"citations={item.get('is-referenced-by-count', 0)}"
                ),
                source_type="crossref",
                published=published,
                relevance=max(0.40, 0.83 - i * 0.04),
                evidence={
                    "doi": item.get("DOI"),
                    "type": item.get("type"),
                    "citations": item.get("is-referenced-by-count", 0),
                },
            )
        )
    return out


def github(query: str, limit: int = 7) -> list[dict[str, Any]]:
    params = {
        "q": query,
        "sort": "updated",
        "order": "desc",
        "per_page": str(max(1, min(limit, 20))),
    }
    url = (
        "https://api.github.com/search/repositories?"
        + urllib.parse.urlencode(params)
    )

    import os
    gh_headers = {}
    gh_token = os.environ.get("GITHUB_TOKEN", "").strip()
    if gh_token:
        # Sin token, GitHub limita a 60 req/hora; con el plan de queries de
        # researcher.py eso se agota en una sola ejecución de run().
        gh_headers["Authorization"] = f"Bearer {gh_token}"

    try:
        data = get_json(url, extra_headers=gh_headers)
    except Exception:
        return []

    out: list[dict[str, Any]] = []
    for i, item in enumerate(data.get("items", [])):
        repo_url = item.get("html_url")
        if not repo_url:
            continue
        out.append(
            make_source(
                title=(
                    item.get("full_name")
                    or item.get("name")
                    or "GitHub repository"
                ),
                url=repo_url,
                snippet=(
                    f"{item.get('description') or ''}; "
                    f"stars={item.get('stargazers_count', 0)}; "
                    f"forks={item.get('forks_count', 0)}; "
                    f"updated={item.get('updated_at') or ''}; "
                    f"archived={item.get('archived', False)}; "
                    f"language={item.get('language') or ''}"
                ),
                source_type="github",
                updated=item.get("updated_at"),
                relevance=max(0.40, 0.86 - i * 0.04),
                evidence={
                    "stars": item.get("stargazers_count", 0),
                    "forks": item.get("forks_count", 0),
                    "open_issues": item.get("open_issues_count", 0),
                    "archived": item.get("archived", False),
                    "license": (
                        (item.get("license") or {}).get("spdx_id")
                    ),
                },
            )
        )
    return out


def quick_search(query: str) -> list[dict[str, Any]]:
    """Búsqueda rápida compatible con web_search.py."""
    results: list[dict[str, Any]] = []

    for function in (
        duckduckgo,
        pubmed,
        openalex,
        crossref,
        github,
    ):
        try:
            results.extend(function(query, limit=5))
        except Exception:
            pass

    return deduplicate(results)


def deduplicate(
    sources: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_url: dict[str, dict[str, Any]] = {}

    for source in sources:
        url = canonical_url(source.get("url", ""))
        if not url:
            continue

        source["url"] = url

        if url not in by_url:
            by_url[url] = source
            continue

        current = by_url[url]
        current["relevance"] = max(
            float(current.get("relevance", 0)),
            float(source.get("relevance", 0)),
        )
        if len(source.get("snippet", "")) > len(
            current.get("snippet", "")
        ):
            current["snippet"] = source["snippet"]
        current.setdefault("evidence", {}).update(
            source.get("evidence", {})
        )

    return list(by_url.values())


def is_biomedical(text: str) -> bool:
    terms = (
        "medical", "medicine", "health", "clinical", "patient",
        "disease", "drug", "pharmac", "nephro", "cardio",
        "oncology", "genom", "protein", "cell", "stem", "fda",
        "ema", "pubmed", "biomedical",
    )
    lower = text.lower()
    return any(term in lower for term in terms)


def build_query_plan(
    specialty: str,
    mission: str,
) -> list[dict[str, Any]]:
    year = str(dt.datetime.now().year)
    base = f"{specialty} {mission}".strip()

    return [
        {
            "id": "scope",
            "objective": (
                "Definir conceptos, terminología, subdominios y "
                "conocimientos fundamentales."
            ),
            "queries": [
                base,
                f"{specialty} fundamentals concepts taxonomy",
                f"{specialty} terminology glossary reference",
            ],
            "engines": ["web", "openalex", "crossref"],
        },
        {
            "id": "path",
            "objective": (
                "Descubrir el camino operativo y metodológico para "
                "cumplir la misión."
            ),
            "queries": [
                f"{base} workflow methodology",
                f"{specialty} implementation process best practices {year}",
                f"{specialty} expert workflow guide",
            ],
            "engines": ["web", "openalex", "crossref"],
        },
        {
            "id": "skills",
            "objective": (
                "Identificar habilidades, competencias y prerrequisitos."
            ),
            "queries": [
                f"{specialty} expert required skills competencies",
                f"{specialty} skills tools tasks",
                f"{specialty} benchmark evaluation dataset",
            ],
            "engines": ["web", "openalex", "crossref"],
        },
        {
            "id": "tools",
            "objective": (
                "Localizar herramientas, librerías, APIs, SDKs y "
                "repositorios actuales."
            ),
            "queries": [
                f"{specialty} software tools libraries {year}",
                f"{specialty} API SDK open source {year}",
                f"{specialty} automation toolkit GitHub",
            ],
            "engines": ["web", "github", "openalex"],
        },
        {
            "id": "official",
            "objective": (
                "Encontrar documentación oficial, estándares, "
                "especificaciones y guías."
            ),
            "queries": [
                f"{specialty} official documentation",
                f"{specialty} standard specification guideline",
                f"{specialty} reference manual official",
            ],
            "engines": ["web", "github"],
        },
        {
            "id": "pitfalls",
            "objective": (
                "Encontrar errores, límites, fallos, condiciones de "
                "borde y problemas de reproducibilidad."
            ),
            "queries": [
                f"{specialty} common errors pitfalls failure modes",
                f"{specialty} limitations caveats validation",
                f"{specialty} reproducibility quality control",
            ],
            "engines": ["web", "openalex", "crossref"],
        },
        {
            "id": "current",
            "objective": (
                "Detectar cambios recientes, obsolescencia, deprecaciones "
                "y migraciones."
            ),
            "queries": [
                f"{specialty} latest tools releases {year}",
                f"{specialty} deprecated obsolete migration",
                f"{specialty} changelog breaking changes",
            ],
            "engines": ["web", "github"],
        },
    ]


def year_from(value: Any) -> int | None:
    match = re.search(r"(20\d{2})", str(value or ""))
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def score_source(
    source: dict[str, Any],
    query: str,
) -> float:
    text = (
        f"{source.get('title', '')} "
        f"{source.get('snippet', '')} "
        f"{source.get('domain', '')}"
    ).lower()

    terms = [
        item
        for item in re.findall(
            r"[a-z0-9áéíóúüñ]{4,}",
            query.lower(),
        )
        if item not in {
            "with", "from", "this", "that", "and", "the",
            "para", "sobre", "como", "esta", "este",
        }
    ]

    overlap = 0.0
    if terms:
        overlap = sum(
            1
            for item in terms
            if item in text
        ) / len(terms)

    quality_weight = {
        "official": 1.00,
        "primary": 0.96,
        "tool_repository": 0.90,
        "secondary": 0.62,
    }.get(
        source.get("source_quality"),
        0.50,
    )

    freshness = 0.0
    year = year_from(
        source.get("updated")
        or source.get("published")
    )
    if year:
        age = max(0, dt.datetime.now().year - year)
        freshness = max(0.0, 1.0 - age / 8.0)

    domain = source.get("domain", "")
    bonus = 0.0
    if domain.endswith(".gov"):
        bonus += 0.08
    if domain.endswith(".edu"):
        bonus += 0.05
    if domain == "pubmed.ncbi.nlm.nih.gov":
        bonus += 0.04

    return round(
        0.40 * float(source.get("relevance", 0.5))
        + 0.28 * overlap
        + 0.19 * quality_weight
        + 0.10 * freshness
        + bonus,
        6,
    )


def infer_capabilities(
    sources: list[dict[str, Any]],
) -> dict[str, list[str]]:
    skill_terms = (
        "python", "sql", "statistics", "simulation", "visualization",
        "data analysis", "machine learning", "validation", "testing",
        "benchmark", "optimization", "documentation", "api", "docker",
        "git", "literature review", "reproducibility", "quality control",
    )
    tool_terms = (
        "python", "pandas", "numpy", "scipy", "pytorch", "tensorflow",
        "scikit-learn", "jupyter", "docker", "kubernetes", "git",
        "github", "api", "r", "matlab", "mathematica",
    )

    skills: set[str] = set()
    tools: set[str] = set()

    for source in sources:
        text = (
            f"{source.get('title', '')} "
            f"{source.get('snippet', '')}"
        ).lower()
        for term in skill_terms:
            if term in text:
                skills.add(term)
        for term in tool_terms:
            if term in text:
                tools.add(term)

    return {
        "skills_hints": sorted(skills),
        "tool_hints": sorted(tools),
    }


def research_questions(
    specialty: str,
    mission: str,
    sources: list[dict[str, Any]],
) -> list[str]:
    questions = [
        (
            "¿Qué afirmaciones nucleares deben verificarse en fuente "
            "primaria u oficial antes de entrar en memoria permanente?"
        ),
        (
            "¿Qué herramientas aparecen repetidamente y cuáles presentan "
            "señales de abandono, deprecación o migración?"
        ),
        (
            "¿Qué tareas concretas demostrarían que el agente domina "
            "la misión y no sólo conoce su terminología?"
        ),
        (
            "¿Qué casos límite pueden provocar respuestas incorrectas "
            "o peligrosas?"
        ),
        (
            "¿Qué partes de la misión pueden implementarse con "
            "herramientas deterministas verificables?"
        ),
    ]

    if not sources:
        questions.insert(
            0,
            (
                f"No hubo resultados fiables para '{specialty}'. "
                f"Reformula la investigación antes de modificar la "
                f"especialización: {mission}"
            ),
        )

    return questions


def collect(
    specialty: str,
    mission: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    plan = build_query_plan(
        specialty,
        mission,
    )
    all_sources: list[dict[str, Any]] = []
    executed: list[dict[str, Any]] = []
    biomedical = is_biomedical(
        f"{specialty} {mission}"
    )

    for stage in plan:
        for query in stage["queries"]:
            engines = stage["engines"]
            executed.append(
                {
                    "stage": stage["id"],
                    "objective": stage["objective"],
                    "query": query,
                    "engines": list(engines),
                }
            )

            if "web" in engines:
                all_sources.extend(
                    duckduckgo(query, limit=7)
                )

            if "openalex" in engines:
                all_sources.extend(
                    openalex(query, limit=5)
                )

            if "crossref" in engines:
                all_sources.extend(
                    crossref(query, limit=5)
                )

            if "github" in engines:
                all_sources.extend(
                    github(query, limit=6)
                )

            if (
                biomedical
                and stage["id"] in {
                    "scope",
                    "path",
                    "skills",
                    "pitfalls",
                }
            ):
                all_sources.extend(
                    pubmed(query, limit=6)
                )

            time.sleep(0.08)

    return deduplicate(all_sources), executed


def build_report(
    specialty: str,
    mission: str,
) -> dict[str, Any]:
    plan = build_query_plan(
        specialty,
        mission,
    )

    sources, executed = collect(
        specialty,
        mission,
    )

    for source in sources:
        source["score"] = score_source(
            source,
            f"{specialty} {mission}",
        )

    sources.sort(
        key=lambda item: (
            float(item.get("score", 0.0)),
            float(item.get("relevance", 0.0)),
        ),
        reverse=True,
    )

    return {
        "schema_version": "3.0",
        "meta": {
            "generated_at": now_iso(),
            "specialty": specialty,
            "mission": mission,
            "biomedical_mode": is_biomedical(
                f"{specialty} {mission}"
            ),
            "query_count": len(executed),
            "source_count": len(sources),
        },
        "research_plan": plan,
        "executed_queries": executed,
        "capabilities": infer_capabilities(sources),
        "open_questions": research_questions(
            specialty,
            mission,
            sources,
        ),
        "priority_sources": sources[:20],
        "all_sources": sources,
        "source_policy": {
            "priority": [
                "official",
                "primary",
                "tool_repository",
                "secondary",
            ],
            "warning": (
                "Search results are evidence to inspect, not facts to "
                "memorize automatically."
            ),
        },
    }


def to_markdown(
    report: dict[str, Any],
) -> str:
    meta = report["meta"]
    capabilities = report["capabilities"]

    lines = [
        "# Nail-StemCell — Research Dossier",
        "",
        f"**Especialidad:** `{meta['specialty']}`",
        "",
        f"**Misión:** {meta['mission']}",
        "",
        f"**Generado:** `{meta['generated_at']}`",
        "",
        f"**Consultas:** `{meta['query_count']}`",
        "",
        f"**Fuentes únicas:** `{meta['source_count']}`",
        "",
        "## Propósito",
        "",
        (
            "Dossier de investigación para orientar la especialización. "
            "No declara competencia por sí mismo. Las afirmaciones críticas "
            "deben verificarse leyendo sus fuentes."
        ),
        "",
        "## Habilidades detectadas",
        "",
    ]

    skills = capabilities.get("skills_hints", [])
    lines.extend(
        f"- {item}" for item in skills
    ) if skills else lines.append("- Sin pistas suficientes.")

    lines += [
        "",
        "## Herramientas / tecnologías detectadas",
        "",
    ]

    tools = capabilities.get("tool_hints", [])
    lines.extend(
        f"- {item}" for item in tools
    ) if tools else lines.append("- Sin pistas suficientes.")

    lines += [
        "",
        "## Preguntas abiertas",
        "",
    ]

    lines.extend(
        f"- {question}"
        for question in report["open_questions"]
    )

    lines += [
        "",
        "## Fuentes prioritarias",
        "",
    ]

    for i, source in enumerate(
        report["priority_sources"],
        start=1,
    ):
        lines += [
            f"### {i}. {source['title']}",
            "",
            f"- Calidad: `{source['source_quality']}`",
            f"- Tipo: `{source['source_type']}`",
            f"- Dominio: `{source['domain']}`",
            f"- Score: `{source['score']:.3f}`",
            f"- Publicación: `{source.get('published') or 'n/d'}`",
            f"- Actualización: `{source.get('updated') or 'n/d'}`",
            f"- URL: {source['url']}",
            f"- Metadata/evidencia: {source.get('snippet') or 'n/d'}",
            "",
        ]

    lines += [
        "## Próximo ciclo",
        "",
        "1. Leer las fuentes oficiales/primarias prioritarias.",
        "2. Separar hechos confirmados de hipótesis.",
        "3. Guardar procedencia de afirmaciones críticas.",
        "4. Construir herramientas deterministas cuando aporten valor.",
        "5. Crear tests y benchmarks de dominio.",
        "6. Repetir la investigación cuando cambien herramientas o guías.",
        "",
    ]

    return "\n".join(lines)


def persist(
    report: dict[str, Any],
) -> dict[str, str]:
    RESEARCH.mkdir(
        parents=True,
        exist_ok=True,
    )

    stamp = dt.datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )
    slug = slugify(
        report["meta"]["specialty"]
    )

    json_path = RESEARCH / (
        f"{stamp}_{slug}.json"
    )
    md_path = RESEARCH / (
        f"{stamp}_{slug}.md"
    )

    json_text = json.dumps(
        report,
        indent=2,
        ensure_ascii=False,
    )
    md_text = to_markdown(
        report
    )

    json_path.write_text(
        json_text,
        encoding="utf-8",
    )
    md_path.write_text(
        md_text,
        encoding="utf-8",
    )
    LATEST_JSON.write_text(
        json_text,
        encoding="utf-8",
    )
    LATEST_MD.write_text(
        md_text,
        encoding="utf-8",
    )

    return {
        "json": str(
            json_path.relative_to(ROOT)
        ),
        "markdown": str(
            md_path.relative_to(ROOT)
        ),
        "latest_json": str(
            LATEST_JSON.relative_to(ROOT)
        ),
        "latest_markdown": str(
            LATEST_MD.relative_to(ROOT)
        ),
    }


def run(
    specialty: str,
    mission: str,
) -> dict[str, Any]:
    report = build_report(
        specialty,
        mission,
    )
    artifacts = persist(
        report
    )

    return {
        "success": True,
        "meta": report["meta"],
        "capabilities": report["capabilities"],
        "open_questions": report["open_questions"],
        "priority_sources": report["priority_sources"][:10],
        "artifacts": artifacts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Investigador multi-fuente persistente para Nail-StemCell."
        )
    )
    parser.add_argument(
        "--specialty",
        default="general",
        help="Especialidad objetivo.",
    )
    parser.add_argument(
        "--mission",
        required=True,
        help="Misión concreta.",
    )
    args = parser.parse_args()

    result = run(
        specialty=args.specialty.strip(),
        mission=args.mission.strip(),
    )
    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print(
            json.dumps(
                {"success": False, "error": "interrupted"},
                ensure_ascii=False,
            )
        )
        raise SystemExit(130)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "success": False,
                    "error": type(exc).__name__,
                    "message": str(exc),
                },
                ensure_ascii=False,
            )
        )
        raise SystemExit(1)
