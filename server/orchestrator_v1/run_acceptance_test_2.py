#!/usr/bin/env python3
"""NEXUS Orchestrator V1 Core - Acceptance Test #2 (Fase 13 del task).

Dimostra la pipeline COMPLETA attraverso l'Orchestrator (non uno script
standalone come il pilot v2 della fase precedente):

    TASK A (TIER0, deterministico): verifica che l'artifact di input
      (dataset BREAKOUT_ACC, Phase 7.21) esista e sia ben formato
     -> TASK B (TIER2 locale, DIPENDE da A): backfill di
      temporal_concentration via ministral-3:3b, verificato
      indipendentemente, risultato scritto come NUOVO artifact (sandbox,
      non un file tracciato esistente - AUTO per l'approval boundary)

Riusa la logica GIA' validata in run_pilot_worker_v2.py (stesso caricamento
dati, stesso prompt, stessa formula) - non la riscrive da zero, solo la fa
passare attraverso Task Queue/Router/Ledger invece che come script
standalone."""
import json
import os
import subprocess
import sys

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))
PHASE721_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_21")
PHASE721_DATASET_ARTIFACT = "server/research_scripts/phase7/phase7_21"
SANDBOX_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_28")

sys.path.insert(0, ORCH_DIR)
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402
from core.orchestrator import Orchestrator, LocalTaskHandler, VerifyResult, ApplyResult  # noqa: E402
from core import ollama_worker  # noqa: E402
from run_pilot_worker_v2 import (_load_breakout_acc_events, _build_prompt_temporal,  # noqa: E402
                                 _extract_code, _reference_temporal_concentration)


def _load_events_via_deterministic_check():
    """Il caricamento vero e proprio E' un'azione deterministica (nessun
    LLM necessario) - eseguita direttamente qui perche' TASK A del
    pipeline la esegue tramite deterministic_worker.check_files_exist su
    file GIA' presenti, poi questo helper fa il parsing (stesso pattern
    gia' stabilito: leggere/normalizzare dati e' TIER0, non richiede
    Ministral)."""
    return _load_breakout_acc_events()


class BackfillTemporalConcentrationHandler(LocalTaskHandler):
    def __init__(self, strategy_name, events):
        self.strategy_name = strategy_name
        self.events = events

    def build_prompt(self, task_record):
        return _build_prompt_temporal(self.strategy_name, self.events)

    def verify(self, task_record, response_text):
        code = _extract_code(response_text, "def compute_temporal_concentration")
        harness = ("import json\n\n" + code +
                  f"\n\nevents = {json.dumps(self.events)}\n"
                  "print(json.dumps(compute_temporal_concentration(events)))\n")
        os.makedirs(SANDBOX_DIR, exist_ok=True)
        path = os.path.join(SANDBOX_DIR, f"_acceptance2_{self.strategy_name.lower()}_temporal.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write(harness)
        try:
            proc = subprocess.run([sys.executable, path], capture_output=True, text=True,
                                 timeout=60, cwd=SANDBOX_DIR)
        except subprocess.TimeoutExpired:
            return VerifyResult(passed=False, errors=["timeout esecuzione sandbox (60s)"])

        expected = _reference_temporal_concentration(self.events)
        if proc.returncode != 0:
            return VerifyResult(passed=False, errors=[proc.stderr[-500:]])
        try:
            parsed = json.loads(proc.stdout.strip().splitlines()[-1])
        except (json.JSONDecodeError, IndexError) as e:
            return VerifyResult(passed=False, errors=[f"output non parsabile: {e}"],
                               is_logic_error=True)

        import math
        def deep_isclose(a, b):
            if isinstance(a, float) and isinstance(b, float):
                return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)
            if isinstance(a, dict) and isinstance(b, dict):
                return set(a) == set(b) and all(deep_isclose(a[k], b[k]) for k in a)
            return a == b

        matches = deep_isclose(parsed, expected)
        if not matches:
            return VerifyResult(passed=False,
                               errors=[f"output non corrisponde al riferimento indipendente"],
                               is_logic_error=True)
        return VerifyResult(passed=True, parsed_output={"code_path": path, "result": parsed})

    def apply(self, task_record, vr):
        out_path = os.path.join(SANDBOX_DIR,
                               f"acceptance2_result_{self.strategy_name.lower()}_temporal_v1.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(vr.parsed_output["result"], f, indent=2, ensure_ascii=False)
        # os.path.relpath usa il separatore nativo (\\ su Windows) - normalizzato a '/' per
        # confrontarsi correttamente coi path dichiarati (sempre POSIX-style) in
        # expected_artifacts del manifest, altrimenti il confidence model vede un falso
        # mismatch (bug di normalizzazione trovato durante l'acceptance test #2).
        def _posix(p):
            return os.path.relpath(p, ROOT).replace(os.sep, "/")
        return ApplyResult(
            files_changed=[_posix(vr.parsed_output["code_path"]), _posix(out_path)],
            artifacts_created=[_posix(out_path)],
            touches_real_repo_files=False)  # solo file NUOVI in sandbox, mai un tracked esistente


def build_manifest_taskA():
    return {
        "task_id": "TASK_ACCEPT2_VERIFY_INPUT", "title": "Verifica artifact di input BREAKOUT_ACC",
        "objective": "Confermare che il dataset BREAKOUT_ACC (Phase 7.21) esista prima di "
                    "usarlo per il backfill.",
        "task_type": "MAINTENANCE", "priority": "NORMAL", "risk_level": "A0",
        "scientific_risk": "NONE", "code_risk": "NONE", "financial_risk": "NONE",
        "required_capabilities": ["registry_updates"], "deterministic_tools_available": True,
        "repo_scope": "server/research_scripts/phase7/phase7_21/",
        "files_allowed": ["server/research_scripts/phase7/phase7_21/*"], "files_forbidden": [],
        "dependencies": [], "blockers": [],
        "expected_artifacts": [], "success_criteria": ["il file dataset loader esiste"],
        "verifier": "deterministic_worker.check_files_exist", "estimated_complexity": "TRIVIAL",
        "estimated_runtime": "10s", "premium_allowed": False,
        "preferred_executor": "TIER0_DETERMINISTIC", "fallback_executors": [],
        "approval_required": "AUTO", "created_by": "orchestrator_v1_acceptance_test_2",
        "created_at": "2026-09-28T00:00:00Z", "tenant_id": "tenant-1", "account_scope_id": None,
    }


def build_manifest_taskB():
    return {
        "task_id": "TASK_ACCEPT2_BACKFILL_TEMPORAL", "title": "Backfill temporal_concentration "
                  "BREAKOUT_ACC via worker locale",
        "objective": "Calcolare temporal_concentration per BREAKOUT_ACC usando ministral-3:3b, "
                    "verificato indipendentemente contro un riferimento scritto separatamente.",
        "task_type": "BACKFILL", "priority": "NORMAL", "risk_level": "A1",
        "scientific_risk": "NONE", "code_risk": "LOW", "financial_risk": "NONE",
        "required_capabilities": ["small_python_functions"], "deterministic_tools_available": False,
        "repo_scope": "server/research_scripts/phase7/phase7_28/",
        "files_allowed": ["server/research_scripts/phase7/phase7_28/*"],
        "files_forbidden": ["MQL5/*", "contracts/*"],
        "dependencies": ["TASK_ACCEPT2_VERIFY_INPUT"], "blockers": [],
        "expected_artifacts": ["server/research_scripts/phase7/phase7_28/"
                              "acceptance2_result_breakout_acc_temporal_v1.json"],
        "success_criteria": ["output corrisponde al riferimento indipendente"],
        "verifier": "server/orchestrator_v1/verify_acceptance_test_2.py",
        "estimated_complexity": "SMALL", "estimated_runtime": "2m", "premium_allowed": False,
        "preferred_executor": "TIER2_LOCAL_STRONG", "fallback_executors": ["TIER3_CLAUDE"],
        "approval_required": "AUTO", "created_by": "orchestrator_v1_acceptance_test_2",
        "created_at": "2026-09-28T00:00:00Z", "tenant_id": "tenant-1", "account_scope_id": None,
    }


def main():
    if not ollama_worker.is_ollama_reachable():
        print("Ollama non raggiungibile - impossibile eseguire l'acceptance test #2")
        sys.exit(1)

    orch = Orchestrator()

    task_a_id = "TASK_ACCEPT2_VERIFY_INPUT"
    orch.submit(build_manifest_taskA(), action="check_files_exist",
              action_params={"paths": [os.path.join(PHASE721_DATASET_ARTIFACT,
                                                    "nxs_breakoutacc_dataset_loader.py")]})
    rec_a = orch.process_task(task_a_id)
    print(f"TASK A ({task_a_id}): {rec_a['state']} - {rec_a['result_packet']['decision']}")

    events = _load_events_via_deterministic_check()
    task_b_id = "TASK_ACCEPT2_BACKFILL_TEMPORAL"
    orch.register_local_handler("backfill_temporal_breakout_acc",
                               BackfillTemporalConcentrationHandler("BREAKOUT_ACC", events))
    orch.submit(build_manifest_taskB(), dependencies=[task_a_id],
              action="backfill_temporal_breakout_acc", action_params={})

    rec_b_check = orch.queue.get(task_b_id)
    print(f"TASK B stato dopo submit (dipendenza {task_a_id} gia' COMPLETED?): "
         f"{rec_b_check['state']}")
    if rec_b_check["state"] == "QUEUED":
        rec_b = orch.process_task(task_b_id)
    else:
        print("TASK B bloccato su dipendenza non soddisfatta - non dovrebbe accadere se A e' "
             "COMPLETED")
        rec_b = rec_b_check

    print(f"TASK B ({task_b_id}): {rec_b['state']} - "
         f"{rec_b['result_packet']['decision'] if rec_b['result_packet'] else 'N/A'} - "
         f"confidence={rec_b['result_packet']['confidence'] if rec_b['result_packet'] else 'N/A'}")

    payload = {"task_a": rec_a, "task_b": rec_b,
              "ledger_events": orch.ledger.read_all()}
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(ORCH_DIR, "acceptance_test_2_result_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path}")


if __name__ == "__main__":
    main()
