#!/usr/bin/env python3
"""NEXUS_MASTERPLAN_V4/V4.1 - non-invasive consistency check for the
canonical documentation set (docs/NEXUS_MASTERPLAN_V4*.md plus the V4.1
infrastructure/workflow docs it links to).

This is NOT a code test - the parent task was documentation-first and
explicitly forbids touching the executor/dispatcher/bridge/CI. What this
checks instead: that the full document set stays internally consistent
over time (no broken cross-links, no invented status word slipping past
the IMPLEMENTED/PARTIAL/PLANNED/BLOCKED legend, every document actually
present). Read-only, exits non-zero on any failure, safe to wire into CI
later if desired - not done here (out of this task's documentation-first
scope).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

REQUIRED_DOCS_V4 = [
    "NEXUS_MASTERPLAN_V4.md",
    "NEXUS_MASTERPLAN_V4_TRADING.md",
    "NEXUS_MASTERPLAN_V4_REVENUE.md",
    "NEXUS_MASTERPLAN_V4_AI_FASHION_AGENCY.md",
    "NEXUS_MASTERPLAN_V4_SOCIAL_CONTENT.md",
    "NEXUS_MASTERPLAN_V4_SYSTEM_DEVELOPMENT.md",
    "NEXUS_MASTERPLAN_V4_FINANCE_COST.md",
    "NEXUS_MASTERPLAN_V4_JARVIS_AUTOMATION.md",
    "NEXUS_MASTERPLAN_V4_SELF_IMPROVEMENT_AND_COUNCIL.md",
    "NEXUS_MASTERPLAN_V4_INDEPENDENT_REVIEWER_MODEL.md",
    "NEXUS_MASTERPLAN_V4_RESPONSABILE_COORDINATION_MODEL.md",
    "NEXUS_MASTERPLAN_V4_ARCHITECTURE_REVIEW.md",
    "NEXUS_MASTERPLAN_V4_GAP_ANALYSIS.md",
]

REQUIRED_DOCS_V4_1 = [
    "NEXUS_MASTERPLAN_V4_1.md",
    "NEXUS_WEBSITE_ARCHITECTURE_AUDIT.md",
    "NEXUS_BACKEND_MODULE_MAP.md",
    "NEXUS_RENDER_INFRASTRUCTURE_PLAN.md",
    "NEXUS_GITHUB_CICD_GOVERNANCE.md",
    "NEXUS_VISUAL_OPERATIONS_SITE_INTEGRATION.md",
    "NEXUS_WORKFLOW_CONTRACTS_V1.md",
    "NEXUS_DEPARTMENT_TEAMS_V1.md",
    "NEXUS_DISTRIBUTED_SELF_IMPROVEMENT_V1.md",
    "NEXUS_INDEPENDENT_REVIEW_V1.md",
    "NEXUS_JARVIS_DELIVERY_ARCHITECTURE_V1.md",
    "NEXUS_ARCHITECTURE_GAP_ANALYSIS_V4_1.md",
    "NEXUS_IMPLEMENTATION_ROADMAP_V4_1.md",
]

REQUIRED_DOCS = REQUIRED_DOCS_V4 + REQUIRED_DOCS_V4_1

ALLOWED_STATUS_WORDS = {"IMPLEMENTED", "PARTIAL", "PLANNED", "BLOCKED"}
# Parole status-simili usate altrove nel repo/ecosistema software che NON
# sono nel vocabolario di questo set - se compaiono in una cella che sembra
# una colonna di stato, è probabile un refuso di un termine non canonico.
# COMPLETED/PENDING deliberatamente esclusi da questa lista: sono valori enum
# legittimi di un vocabolario DIVERSO (stato runtime di un nodo/notifica -
# visual_state, delivery_status - già definiti nei contratti V4.1 stessi),
# non refusi del vocabolario di stato-documentazione IMPLEMENTED/PARTIAL/
# PLANNED/BLOCKED che questo check protegge.
SUSPECT_STATUS_WORDS = {"DONE", "TODO", "WIP", "COMPLETE", "IN_PROGRESS", "NOT_STARTED", "DEPRECATED"}

MD_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+\.md)(#[^)]*)?\)")


def check_all_docs_present() -> list[str]:
    errors = []
    for name in REQUIRED_DOCS:
        if not (DOCS / name).is_file():
            errors.append(f"MISSING_DOC: {name}")
    return errors


def check_internal_links(text: str, source_name: str) -> list[str]:
    errors = []
    for match in MD_LINK_RE.finditer(text):
        target = match.group(1)
        if target.startswith("http://") or target.startswith("https://"):
            continue
        target_path = DOCS / target
        if not target_path.is_file():
            errors.append(f"BROKEN_LINK: {source_name} -> {target}")
    return errors


def check_suspect_status_words(text: str, source_name: str) -> list[str]:
    errors = []
    for word in SUSPECT_STATUS_WORDS:
        if re.search(rf"\b{word}\b", text):
            errors.append(f"SUSPECT_STATUS_WORD: {source_name} contains '{word}' "
                          f"(not in the canonical {sorted(ALLOWED_STATUS_WORDS)} vocabulary)")
    return errors


FINAL_MARKERS = {
    "NEXUS_MASTERPLAN_V4.md": "NEXUS_MASTERPLAN_V4_CANONICAL_DOCUMENTED",
    "NEXUS_MASTERPLAN_V4_1.md": "NEXUS_MASTERPLAN_V4_1_COMPLETE_ARCHITECTURE_CANONICAL_DOCUMENTED",
}


def check_final_marker_present(text: str, source_name: str) -> list[str]:
    marker = FINAL_MARKERS.get(source_name)
    if marker is None:
        return []
    if marker not in text:
        return [f"MISSING_FINAL_MARKER: {source_name} does not mention {marker}"]
    return []


REQUIRED_CONTRACTS_V4_1 = [
    "nexus-workflow-definition-v1.schema.json",
    "nexus-workflow-run-state-v1.schema.json",
    "nexus-department-result-packet-v1.schema.json",
    "nexus-visual-workflow-state-v1.schema.json",
    "nexus-independent-review-v1.schema.json",
]


def check_contracts_present() -> list[str]:
    errors = []
    for name in REQUIRED_CONTRACTS_V4_1:
        if not (ROOT / "contracts" / name).is_file():
            errors.append(f"MISSING_CONTRACT: contracts/{name}")
    return errors


def main() -> int:
    errors: list[str] = []
    errors.extend(check_all_docs_present())
    errors.extend(check_contracts_present())

    for name in REQUIRED_DOCS:
        path = DOCS / name
        if not path.is_file():
            continue  # already reported above
        text = path.read_text(encoding="utf-8")
        errors.extend(check_internal_links(text, name))
        errors.extend(check_suspect_status_words(text, name))
        errors.extend(check_final_marker_present(text, name))

    if errors:
        print(f"NEXUS_MASTERPLAN_V4 doc consistency check: {len(errors)} problem(s)")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(f"NEXUS_MASTERPLAN_V4 doc consistency check: OK "
         f"({len(REQUIRED_DOCS)} documents, all links resolve, status vocabulary clean)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
