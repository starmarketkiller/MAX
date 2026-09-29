#!/usr/bin/env python3
"""NEXUS TASK #0006 punto 11 - genera il testo narrativo (description,
technical_rationale, funding_rationale) per le 13 INITIAL_HYPOTHESIS
attraverso l'Orchestrator + ministral-3:3b - MAI scritto a mano da Claude
(solo i campi STRUTTURATI in initial_hypothesis_inputs.py sono decisi da
Claude, stessa divisione di lavoro gia' validata in NEXUS TASK #0002).

Testa direttamente l'istruzione dell'utente (#0006 punto 14): 'non
escalare automaticamente a Claude - tentare TIER0/Ministral prima'."""
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
from initial_hypothesis_inputs import INITIAL_HYPOTHESES  # noqa: E402

_FORBIDDEN_PHRASES = ["garantito", "sicuramente", "certamente redditizio", "validato dal "
                     "mercato", "domanda confermata", "dati di mercato mostrano",
                     "e' un edge", "ha gia' clienti"]


class HypothesisNarrativeHandler(LocalTaskHandler):
    def __init__(self, spec):
        self.spec = spec
        self.last_result = None

    def build_prompt(self, task_record):
        return f"""Descrivi in italiano questa idea di business, SOLO in base ai fatti
strutturati sotto (non aggiungere nessun dato di mercato, prezzo, cliente o domanda che
non sia gia' scritto qui):

Titolo: {self.spec['title']}
Categoria: {self.spec['category']}
Dimensioni dichiarate: {json.dumps(self.spec['dimensions'], ensure_ascii=False)}
Criteri tecnici dichiarati: {json.dumps(self.spec['technical_criteria'], ensure_ascii=False)}

Rispondi SOLO con un oggetto JSON con ESATTAMENTE queste 3 chiavi:
- "description": 1-2 frasi che spiegano COSA e' questa idea di business (non SE funziona)
- "technical_rationale": 1 frase che spiega perche' i criteri tecnici sopra sono quello
  che sono (riferendoti a infrastructure_leverage in particolare)
- "funding_rationale": 1 frase che spiega perche' le dimensioni sopra portano a quel
  profilo di funding (riferendoti a time_to_cash e capital_required in particolare)

Regole ASSOLUTE: NON inventare prezzi, clienti, domanda di mercato o garanzie di successo -
usa SOLO i valori dichiarati sopra. NON usare markdown, asterischi, cancelletti o backtick
per enfasi o formattazione (es. NON scrivere *parola* o **parola**) - solo testo semplice.
Nessun testo fuori dal JSON."""

    def verify(self, task_record, response_text):
        parsed = ollama_worker.try_parse_json(response_text)
        if parsed is None:
            return VerifyResult(passed=False, errors=["risposta non e' JSON valido"],
                               is_logic_error=True)
        expected_keys = {"description", "technical_rationale", "funding_rationale"}
        if set(parsed.keys()) != expected_keys:
            return VerifyResult(passed=False,
                               errors=[f"chiavi attese {expected_keys}, trovate "
                                      f"{set(parsed.keys())}"], is_logic_error=True)
        combined_text = " ".join(str(v) for v in parsed.values()).lower()
        for phrase in _FORBIDDEN_PHRASES:
            if phrase in combined_text:
                return VerifyResult(passed=False,
                                   errors=[f"testo contiene un'affermazione di mercato non "
                                          f"supportata: '{phrase}'"], is_logic_error=True)
        for k, v in parsed.items():
            if not isinstance(v, str) or len(v.strip()) < 5:
                return VerifyResult(passed=False, errors=[f"'{k}' vuoto o troppo corto"],
                                   is_logic_error=True)
            if len(v) > 500:
                return VerifyResult(passed=False, errors=[f"'{k}' troppo lungo"],
                                   is_logic_error=True)
            if any(c in v for c in ("*", "#", "`")):
                return VerifyResult(passed=False,
                                   errors=[f"'{k}' contiene markdown - non ammesso in un "
                                          "campo testuale semplice"], is_logic_error=True)
        return VerifyResult(passed=True, parsed_output=parsed)

    def apply(self, task_record, vr):
        self.last_result = vr.parsed_output
        return ApplyResult(files_changed=[], artifacts_created=[], touches_real_repo_files=False)


def _manifest(task_id, title):
    return {
        "task_id": task_id, "title": f"Genera narrativa per {title}",
        "objective": f"Scrivere description/technical_rationale/funding_rationale per "
                    f"l'opportunity '{title}' a partire da dimensioni gia' dichiarate",
        "task_type": "DOCUMENTATION", "priority": "NORMAL", "risk_level": "A0",
        "scientific_risk": "NONE", "code_risk": "NONE", "financial_risk": "NONE",
        "required_capabilities": ["json_structured_output", "italian"],
        "deterministic_tools_available": False, "repo_scope": "server/funding_v1/",
        "files_allowed": ["server/funding_v1/*"], "files_forbidden": ["MQL5/*",
                         "Product-Platform/*", "contracts/*"],
        "dependencies": [], "blockers": [], "expected_artifacts": [],
        "success_criteria": ["narrativa verificata, nessuna affermazione di mercato inventata"],
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

    orch = Orchestrator()
    results = {}
    tier_counts = {}
    for spec in INITIAL_HYPOTHESES:
        task_id = f"TASK_NEXUS_0006_NARRATIVE_{spec['id']}_V3"
        handler = HypothesisNarrativeHandler(spec)
        orch.register_local_handler(task_id, handler)
        orch.submit(_manifest(task_id, spec["title"]), action=task_id, action_params={})
        rec = orch.process_task(task_id)
        state = rec["state"]
        started = next((e for e in orch.ledger.read_for_task(task_id)
                       if e["event_type"] == "TASK_STARTED"), None)
        tier = started["payload"]["tier"] if started else "UNKNOWN"
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
        print(f"{spec['id']}: {state} (tier={tier})")
        if state == "COMPLETED":
            results[spec["id"]] = handler.last_result
        else:
            results[spec["id"]] = None
            print(f"  ATTENZIONE: {spec['id']} non completato - resta senza narrativa "
                 "generata, NON inventata da Claude al posto del worker")

    out_path = os.path.join(ORCH_DIR, "nexus_task_0006_narratives_v1.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"results": results, "tier_counts": tier_counts}, f, indent=2,
                 ensure_ascii=False)
    print(f"\nTier breakdown: {tier_counts}")
    print(f"Scritto {out_path}")


if __name__ == "__main__":
    main()
