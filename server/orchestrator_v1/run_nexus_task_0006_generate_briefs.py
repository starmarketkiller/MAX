#!/usr/bin/env python3
"""NEXUS TASK #0006 punto 10 - genera OPPORTUNITY_BRIEF_V1 per ogni
opportunity nel dataset combinato. Tutti i campi sono assemblaggio
deterministico (opportunity_brief_builder.py) TRANNE short_voice_summary,
generato da ministral-3:3b attraverso l'Orchestrator - deve restare
leggibile ad alta voce senza modifiche (niente markdown/simboli)."""
import json
import os
import sys

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))
FUNDING_DIR = os.path.join(ROOT, "server", "funding_v1")

sys.path.insert(0, ORCH_DIR)
sys.path.insert(0, FUNDING_DIR)
from core.orchestrator import Orchestrator, LocalTaskHandler, VerifyResult, ApplyResult  # noqa: E402
from core import ollama_worker  # noqa: E402
from opportunity_brief_builder import build_brief_skeleton  # noqa: E402
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import load_json  # noqa: E402

_FORBIDDEN_PHRASES = ["garantito", "sicuramente", "certamente", "validato dal mercato",
                     "e' un edge", "ha gia' clienti"]


class VoiceSummaryHandler(LocalTaskHandler):
    def __init__(self, skeleton):
        self.skeleton = skeleton
        self.last_text = None

    def build_prompt(self, task_record):
        s = self.skeleton
        return f"""Riassumi in UNA frase parlabile ad alta voce (max 40 parole, NESSUN
markdown, NESSUN simbolo, solo testo semplice in italiano) questa opportunity di business,
usando SOLO questi fatti (non aggiungerne altri):

Titolo: {s['title']}
Funding priority: {s['funding_priority']}/100
Technical priority: {s['technical_priority']}/100
Livello di evidenza: {s['evidence_confidence']}
Stato: {s['priority_status']}
Gate attuale: {'nessun blocco' if not s['main_blocker'] else s['main_blocker']}
Prossimo test piu' economico: {s['next_cheapest_test']}

Rispondi SOLO con la frase, nessun testo prima o dopo."""

    def verify(self, task_record, response_text):
        text = response_text.strip().strip('"')
        text_low = text.lower()
        for phrase in _FORBIDDEN_PHRASES:
            if phrase in text_low:
                return VerifyResult(passed=False,
                                   errors=[f"contiene affermazione non supportata: '{phrase}'"],
                                   is_logic_error=True)
        if any(c in text for c in ("#", "*", "`", "[", "]")):
            return VerifyResult(passed=False, errors=["contiene markdown/simboli"],
                               is_logic_error=True)
        if len(text) > 400 or len(text) < 10:
            return VerifyResult(passed=False, errors=["lunghezza fuori range"],
                               is_logic_error=True)
        return VerifyResult(passed=True, parsed_output={"text": text})

    def apply(self, task_record, vr):
        self.last_text = vr.parsed_output["text"]
        return ApplyResult(files_changed=[], artifacts_created=[], touches_real_repo_files=False)


def _manifest(task_id, title):
    return {
        "task_id": task_id, "title": f"Genera voice summary per {title}",
        "objective": f"Riassumere l'opportunity '{title}' in una frase parlabile ad alta voce",
        "task_type": "DOCUMENTATION", "priority": "NORMAL", "risk_level": "A0",
        "scientific_risk": "NONE", "code_risk": "NONE", "financial_risk": "NONE",
        "required_capabilities": ["italian"], "deterministic_tools_available": False,
        "repo_scope": "server/funding_v1/", "files_allowed": ["server/funding_v1/*"],
        "files_forbidden": ["MQL5/*", "Product-Platform/*", "contracts/*"],
        "dependencies": [], "blockers": [], "expected_artifacts": [],
        "success_criteria": ["voice summary verificato"],
        "verifier": "server/orchestrator_v1/verify_nexus_task_0006.py",
        "estimated_complexity": "TRIVIAL", "estimated_runtime": "1m", "premium_allowed": False,
        "preferred_executor": "TIER1_LOCAL_CHEAP", "fallback_executors": ["TIER2_LOCAL_STRONG"],
        "approval_required": "AUTO", "created_by": "nexus_task_0006",
        "created_at": "2026-09-29T00:00:00Z", "tenant_id": "tenant-1", "account_scope_id": None,
    }


def main():
    if not ollama_worker.is_ollama_reachable():
        print("Ollama non raggiungibile")
        sys.exit(1)

    doc = load_json(os.path.join(FUNDING_DIR, "example_instances", "opportunities_v1.json"))
    opportunities = doc["payload"]["opportunities"]
    source_artifact = "server/funding_v1/example_instances/opportunities_v1.json"
    canonical_sha256 = doc["canonical_sha256"]

    orch = Orchestrator()
    briefs = []
    tier_counts = {}
    for opp in opportunities:
        skeleton = build_brief_skeleton(opp, source_artifact, canonical_sha256)
        task_id = f"TASK_NEXUS_0006_BRIEF_{opp['opportunity_id']}"
        handler = VoiceSummaryHandler(skeleton)
        orch.register_local_handler(task_id, handler)
        orch.submit(_manifest(task_id, opp["title"]), action=task_id, action_params={})
        rec = orch.process_task(task_id)
        started = next((e for e in orch.ledger.read_for_task(task_id)
                       if e["event_type"] == "TASK_STARTED"), None)
        tier = started["payload"]["tier"] if started else "UNKNOWN"
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
        print(f"{opp['opportunity_id']}: {rec['state']} (tier={tier})")
        if rec["state"] == "COMPLETED":
            skeleton["short_voice_summary"] = handler.last_text
            briefs.append(skeleton)
        else:
            print(f"  ATTENZIONE: brief non completato per {opp['opportunity_id']}")

    out_path = os.path.join(FUNDING_DIR, "opportunity_briefs_v1.json")
    sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
    from canonical_utils import wrap_with_provenance, save_json
    save_json(out_path, wrap_with_provenance({"schema_version": 1, "briefs": briefs},
                                            script=os.path.abspath(__file__)))
    print(f"\nTier breakdown: {tier_counts}")
    print(f"Scritto {out_path} ({len(briefs)} briefs)")


if __name__ == "__main__":
    main()
