"""Read-only index for the versioned NEXUS knowledge corpus.

Only fixed, repository-relative roots are scanned. Clients address entries by
opaque IDs; a client-provided filesystem path is never opened.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

MAX_DOCUMENT_BYTES = 1_000_000
ALLOWED_ROOTS = (
    ("vault", Path("vault/01-Trading")),
    ("docs", Path("docs")),
    ("knowledge", Path("knowledge")),
)
ALLOWED_MARKDOWN_SUFFIXES = {".md", ".markdown"}

CATEGORY_RULES = (
    ("Decision Card", ("decision", "dec -")),
    ("Migration", ("migration", "roadmap")),
    ("Protocol", ("protocol", "contract", "schema")),
    ("Architecture", ("architecture", "architettura", "engine design")),
    ("Audit", ("audit", "censimento", "remediation")),
    ("Validation", ("validation", "validity", "verifica", "riverifica", "walk-forward", "walkforward")),
    ("Risk", ("risk", "rischio", "drawdown", "esl", "dpt")),
    ("Execution", ("execution", "esecuzione", "trade lifecycle")),
    ("Research", ("research", "ricerca", "backtest", "test ", "sweep", "ottimizzazione")),
    ("Strategy", ("strateg", "setup ")),
)


def _corpus_base() -> Path:
    configured = os.environ.get("NEXUS_KNOWLEDGE_ROOT")
    return Path(configured).resolve() if configured else Path(__file__).resolve().parents[1]


def _safe_roots() -> list[tuple[str, Path]]:
    base = _corpus_base()
    return [(name, (base / relative).resolve()) for name, relative in ALLOWED_ROOTS]


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _logical_id(kind: str, source: str) -> str:
    digest = hashlib.sha256(f"{kind}:{source}".encode("utf-8")).hexdigest()[:20]
    return f"{kind}-{digest}"


def _title(text: str, fallback: str) -> str:
    match = re.search(r"^#\s+(.+?)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else fallback


def _category(title: str, source: str) -> str:
    haystack = f"{title} {source}".lower()
    for category, needles in CATEGORY_RULES:
        if any(needle in haystack for needle in needles):
            return category
    return "UNCLASSIFIED"


def _date(text: str, source: str) -> str | None:
    frontmatter = re.search(r"(?im)^date:\s*[\"']?(\d{4}-\d{2}-\d{2})", text[:4000])
    if frontmatter:
        return frontmatter.group(1)
    filename = re.search(r"\((\d{2})-(\d{2})-(\d{4})\)", source)
    return f"{filename.group(3)}-{filename.group(2)}-{filename.group(1)}" if filename else None


def _phase(title: str) -> str | None:
    match = re.search(r"(?i)\b(?:phase|fase)\s+([0-9]+[A-Z]?|[A-Z])\b", title)
    return match.group(1).upper() if match else None


def _verdict(text: str) -> str | None:
    match = re.search(
        r"(?im)^(?:\s*[-*]\s*)?(?:verdict|verdetto|esito)\s*[:|]\s*\*{0,2}(PASS_WITH_WARNINGS|PASS|FAIL|VALID|INVALID)\b",
        text[:16000],
    )
    return match.group(1).upper() if match else None


def _snippet(text: str) -> str | None:
    clean = re.sub(r"```.*?```", " ", text[:12000], flags=re.DOTALL)
    clean = re.sub(r"!\[[^]]*\]\([^)]*\)|\[([^]]+)\]\([^)]*\)", r"\1", clean)
    clean = re.sub(r"(?m)^\s*(?:#{1,6}|[-*>]+|\|).*?$", " ", clean)
    clean = re.sub(r"[`*_~]", "", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean[:280] or None


def _strategy_names(base: Path) -> list[str]:
    path = base / "knowledge" / "strategy_database.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return [str(row["nome"]) for row in data.get("strategie", []) if row.get("nome")]
    except (OSError, ValueError, TypeError):
        return []


def _strategy(title: str, names: list[str]) -> str | None:
    normalized = re.sub(r"[^A-Z0-9]+", "_", title.upper())
    matches = [name for name in names if re.search(rf"(?:^|_){re.escape(name.upper())}(?:_|$)", normalized)]
    return matches[0] if len(matches) == 1 else None


def _document_metadata(path: Path, root: Path, root_name: str, names: list[str]) -> dict[str, Any] | None:
    resolved = path.resolve()
    if path.suffix.lower() not in ALLOWED_MARKDOWN_SUFFIXES or not _is_within(resolved, root):
        return None
    try:
        # The list endpoint only needs enough text for conservative metadata
        # and a short snippet. Full content is loaded by get_entry on demand.
        with resolved.open("r", encoding="utf-8", errors="replace") as handle:
            text = handle.read(64_000)
    except OSError:
        return None
    source = f"{root_name}/{resolved.relative_to(root).as_posix()}"
    title = _title(text, path.stem)
    category = _category(title, source)
    provenance = "RESEARCH" if category in {"Research", "Validation"} else "DERIVED"
    return {
        "id": _logical_id("doc", source), "kind": "document", "title": title,
        "source": source, "category": category, "strategy": _strategy(title, names),
        "phase": _phase(title), "verdict": _verdict(text), "date": _date(text, source),
        "source_path": source, "snippet": _snippet(text), "provenance": provenance,
    }


def _load_strategy_database(base: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    path = (base / "knowledge" / "strategy_database.json").resolve()
    root = (base / "knowledge").resolve()
    if not _is_within(path, root):
        return {}, []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}, []
    rows = []
    for item in payload.get("strategie", []):
        name = item.get("nome")
        if not name:
            continue
        source = f"knowledge/strategy_database.json#{name}"
        sweep = item.get("ultimo_sweep") or {}
        rows.append({
            "id": _logical_id("strategy", source), "kind": "strategy", "title": name,
            "source": source, "source_path": "knowledge/strategy_database.json",
            "category": "Strategy", "strategy": name, "phase": None, "verdict": None,
            "date": payload.get("generato"), "snippet": item.get("decisione_corrente") or item.get("note"),
            "provenance": "RESEARCH", "status": item.get("stato"),
            "evidence_level": item.get("affidabilita_dati"),
            "metrics": {
                "profit_factor": sweep.get("profit_factor", item.get("PF")),
                "win_rate_pct": sweep.get("winrate_pct", item.get("WR_pct")),
                "expectancy_r": sweep.get("expectancy_R", item.get("expectancy_R")),
                "trades": sweep.get("trade_eseguiti", item.get("trade")),
            },
        })
    return payload, rows


@lru_cache(maxsize=1)
def build_index() -> dict[str, Any]:
    base = _corpus_base()
    names = _strategy_names(base)
    documents = []
    for root_name, root in _safe_roots():
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            metadata = _document_metadata(path, root, root_name, names)
            if metadata:
                documents.append(metadata)
    strategy_payload, strategies = _load_strategy_database(base)
    documents.extend(strategies)
    documents.sort(key=lambda row: ((row.get("date") or ""), row["title"]), reverse=True)
    return {
        "documents": documents,
        "strategy_database": {
            "available": bool(strategies), "generated": strategy_payload.get("generato"),
            "warning": strategy_payload.get("avvertenza"), "count": len(strategies),
        },
        "provenance": "CACHED",
    }


def list_entries() -> dict[str, Any]:
    index = build_index()
    return {**index, "count": len(index["documents"])}


def get_entry(entry_id: str) -> dict[str, Any] | None:
    index = build_index()
    metadata = next((row for row in index["documents"] if row["id"] == entry_id), None)
    if metadata is None:
        return None
    if metadata["kind"] == "strategy":
        payload, _ = _load_strategy_database(_corpus_base())
        item = next((row for row in payload.get("strategie", []) if row.get("nome") == metadata["strategy"]), None)
        return {**metadata, "content_type": "strategy", "strategy_data": item, "content": None, "truncated": False}
    source = metadata["source"]
    root_name, relative = source.split("/", 1)
    root = next((root for name, root in _safe_roots() if name == root_name), None)
    if root is None:
        return None
    path = (root / relative).resolve()
    if not _is_within(path, root) or path.suffix.lower() not in ALLOWED_MARKDOWN_SUFFIXES or not path.is_file():
        return None
    with path.open("rb") as handle:
        raw = handle.read(MAX_DOCUMENT_BYTES + 1)
    truncated = len(raw) > MAX_DOCUMENT_BYTES
    content = raw[:MAX_DOCUMENT_BYTES].decode("utf-8", errors="replace")
    return {**metadata, "content_type": "markdown", "content": content, "strategy_data": None, "truncated": truncated}
