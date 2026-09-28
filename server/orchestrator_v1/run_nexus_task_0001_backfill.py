#!/usr/bin/env python3
"""NEXUS TASK #0001 - prima task PRODUCTION-LIKE eseguita attraverso
l'Orchestrator V1 (non un acceptance test/pilot manuale di Claude).

Task: backfill temporal_concentration + exit_efficiency per BREAKOUT_ACC e
ORDER_BLOCK (candidato gia' in cima alla Research Priority Queue, Phase
7.26).

Ruolo di Claude qui: SOLO supervisore/harness - crea i TASK_MANIFEST_V1,
li inserisce nella queue, lascia che Router/Ministral/verifier facciano il
lavoro. Riusa gli stessi LocalTaskHandler (prompt/verifica/riferimento
indipendente) gia' validati nel pilot v2 e nell'acceptance test #2 - non
scrive nuova logica di aggregazione. Se un sotto-task fallisce, l'Orchestrator
produce ESCALATION_REQUIRED - Claude NON corregge il contenuto al posto del
worker."""
import json
import os
import subprocess
import sys
import time

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))
SANDBOX_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_28")
PHASE721_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_21")
PHASE722_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_22")

sys.path.insert(0, ORCH_DIR)
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402
from core.orchestrator import Orchestrator, LocalTaskHandler, VerifyResult, ApplyResult  # noqa: E402
from core import ollama_worker  # noqa: E402
from run_pilot_worker_v2 import (_load_breakout_acc_events, _load_order_block_events,  # noqa: E402
                                 _build_prompt_temporal, _build_prompt_exit_efficiency,
                                 _extract_code, _reference_temporal_concentration,
                                 _reference_exit_efficiency)

import math


def _deep_isclose(a, b):
    if isinstance(a, float) and isinstance(b, float):
        return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(_deep_isclose(a[k], b[k]) for k in a)
    return a == b


def _posix(p):
    return os.path.relpath(p, ROOT).replace(os.sep, "/")


class _BackfillHandler(LocalTaskHandler):
    """Generico per entrambe le metriche - la differenza fra
    temporal_concentration ed exit_efficiency e' solo quale prompt/
    riferimento/marker usare, iniettati al costruttore (stessa logica gia'
    validata, non riscritta qui)."""

    def __init__(self, strategy_name, events, metric_name, prompt_builder, marker, fn_call,
                reference_fn):
        self.strategy_name = strategy_name
        self.events = events
        self.metric_name = metric_name
        self.prompt_builder = prompt_builder
        self.marker = marker
        self.fn_call = fn_call
        self.reference_fn = reference_fn

    def build_prompt(self, task_record):
        return self.prompt_builder(self.strategy_name, self.events)

    def verify(self, task_record, response_text):
        code = _extract_code(response_text, self.marker)
        harness = ("import json\n\n" + code + f"\n\nevents = {json.dumps(self.events)}\n"
                  f"print(json.dumps({self.fn_call}))\n")
        os.makedirs(SANDBOX_DIR, exist_ok=True)
        path = os.path.join(SANDBOX_DIR,
                           f"_nexus0001_{self.strategy_name.lower()}_{self.metric_name}.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write(harness)
        try:
            proc = subprocess.run([sys.executable, path], capture_output=True, text=True,
                                 timeout=60, cwd=SANDBOX_DIR)
        except subprocess.TimeoutExpired:
            return VerifyResult(passed=False, errors=["timeout esecuzione sandbox (60s)"])

        expected = self.reference_fn(self.events)
        if proc.returncode != 0:
            return VerifyResult(passed=False, errors=[proc.stderr[-500:]])
        try:
            parsed = json.loads(proc.stdout.strip().splitlines()[-1])
        except (json.JSONDecodeError, IndexError) as e:
            return VerifyResult(passed=False, errors=[f"output non parsabile: {e}"],
                               is_logic_error=True)
        if not _deep_isclose(parsed, expected):
            return VerifyResult(passed=False,
                               errors=["output non corrisponde al riferimento indipendente"],
                               is_logic_error=True)
        return VerifyResult(passed=True, parsed_output={"code_path": path, "result": parsed})

    def apply(self, task_record, vr):
        out_path = os.path.join(SANDBOX_DIR,
                               f"nexus0001_result_{self.strategy_name.lower()}_"
                               f"{self.metric_name}_v1.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(vr.parsed_output["result"], f, indent=2, ensure_ascii=False)
        return ApplyResult(files_changed=[_posix(vr.parsed_output["code_path"]), _posix(out_path)],
                          artifacts_created=[_posix(out_path)], touches_real_repo_files=False)


def _manifest_verify(task_id, strategy_name, dataset_file):
    return {
        "task_id": task_id, "title": f"Verifica artifact di input {strategy_name}",
        "objective": f"Confermare che il dataset {strategy_name} esista prima del backfill.",
        "task_type": "MAINTENANCE", "priority": "NORMAL", "risk_level": "A0",
        "scientific_risk": "NONE", "code_risk": "NONE", "financial_risk": "NONE",
        "required_capabilities": ["registry_updates"], "deterministic_tools_available": True,
        "repo_scope": os.path.dirname(dataset_file), "files_allowed": [os.path.dirname(dataset_file) + "/*"],
        "files_forbidden": [], "dependencies": [], "blockers": [], "expected_artifacts": [],
        "success_criteria": ["il dataset esiste"], "verifier": "deterministic_worker.check_files_exist",
        "estimated_complexity": "TRIVIAL", "estimated_runtime": "10s", "premium_allowed": False,
        "preferred_executor": "TIER0_DETERMINISTIC", "fallback_executors": [],
        "approval_required": "AUTO", "created_by": "nexus_task_0001", "created_at": "2026-09-28T00:00:00Z",
        "tenant_id": "tenant-1", "account_scope_id": None,
    }


def _manifest_backfill(task_id, strategy_name, metric_name, depends_on):
    return {
        "task_id": task_id,
        "title": f"Backfill {metric_name} {strategy_name}",
        "objective": f"Calcolare {metric_name} per {strategy_name} usando il worker locale, "
                    "verificato indipendentemente - Research Priority Queue Phase 7.26, "
                    "candidato BACKFILL_TEMPORAL_AND_EXIT_EFFICIENCY_BREAKOUT_ACC_ORDER_BLOCK.",
        "task_type": "BACKFILL", "priority": "NORMAL", "risk_level": "A1", "scientific_risk": "NONE",
        "code_risk": "LOW", "financial_risk": "NONE",
        "required_capabilities": ["small_python_functions"], "deterministic_tools_available": False,
        "repo_scope": "server/research_scripts/phase7/phase7_28/",
        "files_allowed": ["server/research_scripts/phase7/phase7_28/*"],
        "files_forbidden": ["MQL5/*", "contracts/*", "Product-Platform/*"],
        "dependencies": [depends_on], "blockers": [],
        "expected_artifacts": [f"server/research_scripts/phase7/phase7_28/nexus0001_result_"
                              f"{strategy_name.lower()}_{metric_name}_v1.json"],
        "success_criteria": ["output corrisponde al riferimento indipendente"],
        "verifier": "server/orchestrator_v1/verify_nexus_task_0001.py",
        "estimated_complexity": "SMALL", "estimated_runtime": "2m", "premium_allowed": False,
        "preferred_executor": "TIER2_LOCAL_STRONG", "fallback_executors": ["TIER3_CLAUDE"],
        "approval_required": "AUTO", "created_by": "nexus_task_0001",
        "created_at": "2026-09-28T00:00:00Z", "tenant_id": "tenant-1", "account_scope_id": None,
    }


def main():
    if not ollama_worker.is_ollama_reachable():
        print("Ollama non raggiungibile - impossibile eseguire NEXUS TASK #0001")
        sys.exit(1)

    orch = Orchestrator()
    t0 = time.time()

    breakout_events = _load_breakout_acc_events()
    order_block_events = _load_order_block_events()

    verify_ba_id = "TASK_NEXUS_0001_VERIFY_BREAKOUT_ACC"
    verify_ob_id = "TASK_NEXUS_0001_VERIFY_ORDER_BLOCK"
    orch.submit(_manifest_verify(verify_ba_id, "BREAKOUT_ACC",
                                os.path.join(PHASE721_DIR, "nxs_breakoutacc_dataset_loader.py")),
              action="check_files_exist",
              action_params={"paths": [os.path.relpath(
                  os.path.join(PHASE721_DIR, "nxs_breakoutacc_dataset_loader.py"), ROOT).replace(os.sep, "/")]})
    orch.submit(_manifest_verify(verify_ob_id, "ORDER_BLOCK",
                                os.path.join(PHASE722_DIR, "canonical_economic_dataset_v1.json")),
              action="check_files_exist",
              action_params={"paths": [os.path.relpath(
                  os.path.join(PHASE722_DIR, "canonical_economic_dataset_v1.json"), ROOT).replace(os.sep, "/")]})

    sub_tasks = [
        ("TASK_NEXUS_0001_BREAKOUT_ACC_TEMPORAL", "BREAKOUT_ACC", "temporal", breakout_events,
        verify_ba_id, _build_prompt_temporal, "def compute_temporal_concentration",
        "compute_temporal_concentration(events)", _reference_temporal_concentration),
        ("TASK_NEXUS_0001_BREAKOUT_ACC_EXITFX", "BREAKOUT_ACC", "exitfx", breakout_events,
        verify_ba_id, _build_prompt_exit_efficiency, "def compute_exit_efficiency",
        "compute_exit_efficiency(events)", _reference_exit_efficiency),
        ("TASK_NEXUS_0001_ORDER_BLOCK_TEMPORAL", "ORDER_BLOCK", "temporal", order_block_events,
        verify_ob_id, _build_prompt_temporal, "def compute_temporal_concentration",
        "compute_temporal_concentration(events)", _reference_temporal_concentration),
        ("TASK_NEXUS_0001_ORDER_BLOCK_EXITFX", "ORDER_BLOCK", "exitfx", order_block_events,
        verify_ob_id, _build_prompt_exit_efficiency, "def compute_exit_efficiency",
        "compute_exit_efficiency(events)", _reference_exit_efficiency),
    ]

    for task_id, strategy, metric, events, dep, prompt_builder, marker, fn_call, ref_fn in sub_tasks:
        orch.register_local_handler(task_id, _BackfillHandler(strategy, events, metric,
                                                              prompt_builder, marker, fn_call, ref_fn))
        orch.submit(_manifest_backfill(task_id, strategy, metric, dep), dependencies=[dep],
                  action=task_id, action_params={})

    all_task_ids = [verify_ba_id, verify_ob_id] + [s[0] for s in sub_tasks]
    results = {}
    for task_id in [verify_ba_id, verify_ob_id]:
        results[task_id] = orch.process_task(task_id)
        print(f"{task_id}: {results[task_id]['state']}")

    for task_id, *_ in sub_tasks:
        results[task_id] = orch.process_task(task_id)
        rp = results[task_id].get("result_packet")
        print(f"{task_id}: {results[task_id]['state']} - "
             f"{rp['decision'] if rp else 'N/A'} - confidence={rp['confidence'] if rp else 'N/A'}")

    elapsed = round(time.time() - t0, 2)

    tier_counts = {"TIER0_DETERMINISTIC": 0, "TIER1_LOCAL_CHEAP": 0, "TIER2_LOCAL_STRONG": 0,
                  "ESCALATION_REQUIRED": 0}
    retries_total = 0
    escalations = []
    for task_id in all_task_ids:
        events_for_task = orch.ledger.read_for_task(task_id)
        started = next((e for e in events_for_task if e["event_type"] == "TASK_STARTED"), None)
        if started:
            tier = started["payload"].get("tier")
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
        retries_total += sum(1 for e in events_for_task if e["event_type"] == "RETRY_STARTED")
        if results[task_id]["state"] == "ESCALATION_REQUIRED":
            escalations.append({"task_id": task_id,
                               "target": results[task_id]["escalation"]["target"],
                               "classification": results[task_id]["escalation"]["classification"]})

    summary = {
        "nexus_task": "0001", "title": "Backfill temporal_concentration + exit_efficiency "
                       "BREAKOUT_ACC + ORDER_BLOCK",
        "task_ids": all_task_ids, "elapsed_seconds": elapsed,
        "tier_breakdown": tier_counts, "retries_total": retries_total,
        "escalations": escalations, "escalation_occurred": len(escalations) > 0,
        "premium_tokens_or_cost_used": 0,
        "premium_api_calls_made": 0,
        "per_task_summary": {
            task_id: {
                "state": results[task_id]["state"],
                "executor": results[task_id].get("executor"),
                "result_packet": results[task_id].get("result_packet"),
            } for task_id in all_task_ids
        },
    }

    print(f"\n=== NEXUS TASK #0001 - riepilogo ===")
    print(f"Tempo totale: {elapsed}s")
    print(f"Tier breakdown: {tier_counts}")
    print(f"Retry totali: {retries_total}")
    print(f"Escalation: {escalations if escalations else 'NESSUNA'}")
    print(f"Costo/token premium usati: 0 (nessuna chiamata API Claude/Codex automatica)")

    payload = {"summary": summary, "ledger_events": orch.ledger.read_all()}
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(ORCH_DIR, "nexus_task_0001_result_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path}")


if __name__ == "__main__":
    main()
