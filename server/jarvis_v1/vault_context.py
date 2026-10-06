"""NEXUS_LOCAL_OPERATOR_BOOTSTRAP_V1 Phase 4 - bounded, read-only vault
context for TELEGRAM_MISTRAL_DIRECT_MODE_V1.

Deliberately simple per the spec ("retrieval semplice prima di introdurre
vector DB... non introdurre Qdrant/Chroma se non strettamente necessario"):
plain keyword scoring over real markdown files already in vault/ and
.claude/skills/, no embeddings, no new storage. Read-only - this module
never writes to the vault.

Namespaces are grounded in the REAL directory layout found in this
session's census (vault/00-Inbox, 01-Trading{/Decisions,/TODO},
02-Business{/Opportunity-Funding}, 03-Social, 04-System), not invented:
TRADING/DECISIONS/TASKS map onto 01-Trading and its two real subfolders,
REVENUE onto 02-Business, SYSTEM onto 04-System. SKILLS has no vault
folder at all - skills live in .claude/skills/, so that namespace points
there instead of forcing a non-existent vault path.

The model NEVER receives the whole vault - only the top_k highest-scoring
snippets within the single best-matching namespace (or none, if nothing
scores above zero). Snippets are vault DATA, never instructions - the
caller (service.py) must frame them as reference material in the prompt,
consistent with the project's standing rule that content from outside the
user's own message is never treated as a command.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List, Optional

SERVER = Path(__file__).resolve().parents[1]
ROOT = SERVER.parent

NAMESPACE_VAULT_DIRS = {
    "TRADING": ["01-Trading"],
    "DECISIONS": ["01-Trading/Decisions"],
    "TASKS": ["01-Trading/TODO"],
    "REVENUE": ["02-Business"],
    "SYSTEM": ["04-System"],
}
SKILLS_NAMESPACE = "SKILLS"  # resolved against repo root, not vault root - see module docstring

DEFAULT_TOP_K = 3
SNIPPET_CHARS = 400
MIN_TERM_LENGTH = 3

# Senza questi, una parola funzionale generica ("quali", "sono", "cosa")
# domina il punteggio per pura frequenza in qualunque documento lungo,
# indipendentemente dal contenuto - scoperto concretamente in questa sessione
# (una query su "funding" sceglieva il namespace sbagliato finche' "quali"/
# "sono"/"recenti" non sono stati esclusi). Lista minima, non esaustiva.
_STOPWORDS = {
    "quali", "quale", "sono", "essere", "che", "cosa", "come", "dice", "questo", "questa",
    "per", "con", "una", "uno", "del", "della", "dei", "delle", "nel", "nella", "sul", "sulla",
    "the", "and", "for", "with", "that", "this", "what", "how", "does", "are", "esistono", "recenti",
}


def vault_root() -> Path:
    return Path(os.environ.get("NEXUS_KNOWLEDGE_ROOT", ROOT)) / "vault"


def _namespace_dirs(namespace: str) -> List[Path]:
    if namespace == SKILLS_NAMESPACE:
        return [ROOT / ".claude" / "skills"]
    return [vault_root() / rel for rel in NAMESPACE_VAULT_DIRS.get(namespace, [])]


def _query_terms(query: str) -> List[str]:
    return [t for t in (tok.lower() for tok in re.findall(r"\w+", query or ""))
           if len(t) >= MIN_TERM_LENGTH and t not in _STOPWORDS]


def _score_file(path: Path, terms: List[str]) -> int:
    """Number of DISTINCT query terms present, not raw occurrence count -
    a single frequent word must never dominate over several distinct
    on-topic terms (see _STOPWORDS docstring for the concrete bug this
    fixes)."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
    except OSError:
        return 0
    return sum(1 for term in terms if term in text)


def select_namespace(query: str) -> Optional[str]:
    """Picks the namespace containing the single highest-scoring file -
    None if nothing scores above zero (no forced, irrelevant context).

    Deliberately the MAX single-file score, not the sum across a namespace:
    a namespace with many large, loosely-related files would otherwise
    always outscore a namespace with one small, exactly-on-topic file
    (verified concretely in this session: a query mentioning "funding"
    summed higher in the much larger 01-Trading folder, which never
    mentions funding at all, than in 02-Business/Opportunity-Funding,
    where every file does - fixed before this was ever wired into a
    prompt)."""
    terms = _query_terms(query)
    if not terms:
        return None
    best_namespace, best_score = None, 0
    for namespace in (*NAMESPACE_VAULT_DIRS, SKILLS_NAMESPACE):
        for directory in _namespace_dirs(namespace):
            if not directory.is_dir():
                continue
            for path in directory.glob("**/*.md"):
                score = _score_file(path, terms)
                if score > best_score:
                    best_namespace, best_score = namespace, score
    return best_namespace


def search_namespace(namespace: str, query: str, *, top_k: int = DEFAULT_TOP_K) -> List[dict]:
    """Top-k {title, source, snippet} within one namespace - never the
    whole namespace, never the whole vault."""
    terms = _query_terms(query)
    if not terms:
        return []
    scored = []
    for directory in _namespace_dirs(namespace):
        if not directory.is_dir():
            continue
        for path in directory.glob("**/*.md"):
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            lower = text.lower()
            score = sum(1 for term in terms if term in lower)
            if score <= 0:
                continue
            idx = next((lower.find(term) for term in terms if lower.find(term) != -1), 0)
            start = max(0, idx - 80)
            snippet = text[start:start + SNIPPET_CHARS].strip()
            root_for_rel = ROOT if namespace == SKILLS_NAMESPACE else vault_root()
            scored.append((score, path, snippet, root_for_rel))
    scored.sort(key=lambda item: -item[0])
    return [{"title": path.stem, "source": str(path.relative_to(root_for_rel)).replace("\\", "/"),
            "snippet": snippet}
           for _, path, snippet, root_for_rel in scored[:top_k]]


def build_context_pack(query: str, *, top_k: int = DEFAULT_TOP_K) -> dict:
    """Returns {"namespace": str|None, "notes": [...]} - notes is empty and
    namespace is None when nothing in the vault/skills matched the query.
    Pure read, bounded, never the full vault."""
    namespace = select_namespace(query)
    if namespace is None:
        return {"namespace": None, "notes": []}
    return {"namespace": namespace, "notes": search_namespace(namespace, query, top_k=top_k)}
