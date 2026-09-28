#!/usr/bin/env python3
"""NEXUS Orchestrator V1 Core - Acceptance Test #1 (Fase 12 del task).

Bug reale: server/tests/test_research_control_plane_v2.py asserisce
`experiment_count == 8` e `hypothesis_count == 8`, ma Phase 7.27 ha
aggiunto legittimamente una 9a hypothesis e un 9o experiment ai registry -
un'asserzione con conteggio hardcoded che diventa fragile quando il
registry cresce (esattamente lo scopo dichiarato della Safety Net).

Passi ESEGUITI DAL SISTEMA (mai da Claude manualmente):
1. crea il task (TASK_MANIFEST_V1);
2. classifica il rischio (A1, code_risk LOW, scientific_risk NONE);
3. il Router sceglie deterministic/local (qui: locale, non c'e' un
   workflow deterministico per 'scrivi un'assertion corretta');
4. il worker locale (ministral-3:3b) diagnostica il test fragile e propone
   la patch minimale;
5-7. la patch viene verificata IN SANDBOX (mai sul file reale), eseguendo
   pytest sulla copia sandboxed;
8. tutto registrato nel Ledger, RESULT_PACKET prodotto.

Passi fatti da Claude (TIER0, deterministico, dichiarati esplicitamente):
- leggere il file di test reale e i registry reali per ottenere i FATTI
  (conteggi attuali) da passare al prompt - MAI decidere la correzione.

Approval boundary: la modifica di un file REALE del repository e'
REVIEW_REQUIRED (Fase 14) - il task termina in WAITING_APPROVAL con la
patch verificata ma NON applicata al file tracciato, per costruzione."""
import os
import re
import subprocess
import sys

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))
TEST_FILE_REAL = os.path.join(ROOT, "server", "tests", "test_research_control_plane_v2.py")
SANDBOX_DIR = os.path.join(ROOT, "server", "tests")
PATCH_ARTIFACT_DIR = os.path.join(ORCH_DIR, "proposed_patches")

sys.path.insert(0, ORCH_DIR)
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402
from core.orchestrator import Orchestrator, LocalTaskHandler, VerifyResult, ApplyResult  # noqa: E402
from core import ollama_worker  # noqa: E402


def _diagnose_real_facts():
    """TIER0 - Claude/harness raccoglie SOLO i fatti, non decide la fix."""
    with open(TEST_FILE_REAL, encoding="utf-8") as f:
        lines = f.readlines()
    line9 = lines[8].rstrip("\n")   # assert ... experiment_count == 8
    line10 = lines[9].rstrip("\n")  # assert ... hypothesis_count == 8

    sys.path.insert(0, os.path.join(ROOT, "server"))
    import research_control_plane as rcp  # noqa: E402
    model = rcp.CONTROL_PLANE.build()
    real_experiment_count = model["overview"]["experiment_count"]
    real_hypothesis_count = model["overview"]["hypothesis_count"]

    return {
        "line9_current": line9, "line10_current": line10,
        "real_experiment_count": real_experiment_count,
        "real_hypothesis_count": real_hypothesis_count,
        "test_run_stdout": _run_original_test(),
    }


def _run_original_test():
    proc = subprocess.run(
        [sys.executable, "-m", "pytest",
        "tests/test_research_control_plane_v2.py::test_safety_net_registries_are_projected_without_reinterpretation",
        "-q"], capture_output=True, text=True, cwd=os.path.join(ROOT, "server"), timeout=60)
    return (proc.stdout + proc.stderr)[-800:]


class HypothesisCountFixHandler(LocalTaskHandler):
    def __init__(self, facts):
        self.facts = facts

    def build_prompt(self, task_record):
        f = self.facts
        return f"""In un test pytest ci sono queste due righe (numerate 9 e 10 nel file):

Riga 9:  {f['line9_current']}
Riga 10: {f['line10_current']}

Queste righe ora FALLISCONO all'esecuzione perche' il registry sottostante
e' legittimamente cresciuto nel tempo (la Safety Net del progetto e'
DISEGNATA per crescere - aggiungere nuove hypothesis/experiment nel tempo
e' il comportamento atteso, non un bug dei dati):
- experiment_count REALE oggi: {f['real_experiment_count']} (la riga 9 si aspetta 8)
- hypothesis_count REALE oggi: {f['real_hypothesis_count']} (la riga 10 si aspetta 8)

Il test deve continuare a essere un controllo di sanita' significativo (non
deve diventare un no-op tipo 'assert True'), ma non deve piu' rompersi ogni
volta che il registry cresce legittimamente in futuro.

Scrivi SOLO le due righe Python corrette che dovrebbero sostituire la riga 9
e la riga 10 (stessa indentazione, nessuna spiegazione, nessun markdown
fence, esattamente 2 righe in output)."""

    def verify(self, task_record, response_text):
        lines = [ln for ln in response_text.strip().splitlines() if ln.strip()]
        proposed = [ln for ln in lines if "experiment_count" in ln or "hypothesis_count" in ln]
        if len(proposed) < 2:
            return VerifyResult(passed=False, errors=[f"attese 2 righe con experiment_count/"
                               f"hypothesis_count, trovate {len(proposed)}: {lines}"],
                               is_logic_error=True)
        new_line9 = next((ln for ln in proposed if "experiment_count" in ln), None)
        new_line10 = next((ln for ln in proposed if "hypothesis_count" in ln), None)
        if not new_line9 or not new_line10:
            return VerifyResult(passed=False, errors=["mancante una delle due righe attese"],
                               is_logic_error=True)

        # verifica indipendente 1: non deve essere un no-op degenere (deve avere un
        # operatore di confronto reale, non solo 'assert True'/nessun confronto)
        if not re.search(r"(==|>=|<=|>|<)", new_line9) or not re.search(r"(==|>=|<=|>|<)", new_line10):
            return VerifyResult(passed=False,
                               errors=["la patch proposta non contiene un vero operatore di "
                                      "confronto - possibile no-op degenere"],
                               is_logic_error=True)

        # verifica indipendente 2: la patch applicata DEVE far passare il test reale
        # (eseguita in SANDBOX - copia del file, mai il file tracciato)
        os.makedirs(PATCH_ARTIFACT_DIR, exist_ok=True)
        sandbox_path = os.path.join(SANDBOX_DIR,
                                   "_orchestrator_sandbox_hypothesis_count_patch_v1.py")
        with open(TEST_FILE_REAL, encoding="utf-8") as f:
            original_lines = f.readlines()
        # preserva l'indentazione originale della riga 9/10 - il modello propone solo il
        # CONTENUTO della riga, l'indentazione e' meccanica/deterministica (harness), non
        # qualcosa che il modello deve indovinare correttamente da solo.
        indent9 = original_lines[8][:len(original_lines[8]) - len(original_lines[8].lstrip())]
        indent10 = original_lines[9][:len(original_lines[9]) - len(original_lines[9].lstrip())]
        patched_lines = list(original_lines)
        patched_lines[8] = indent9 + new_line9.strip() + "\n"
        patched_lines[9] = indent10 + new_line10.strip() + "\n"
        with open(sandbox_path, "w", encoding="utf-8") as f:
            f.writelines(patched_lines)

        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pytest",
                "tests/_orchestrator_sandbox_hypothesis_count_patch_v1.py::"
                "test_safety_net_registries_are_projected_without_reinterpretation", "-q"],
                capture_output=True, text=True, cwd=os.path.join(ROOT, "server"), timeout=60)
        except subprocess.TimeoutExpired:
            return VerifyResult(passed=False, errors=["timeout eseguendo il test sandboxato"])
        finally:
            # artifact di verifica EFFIMERO - solo la patch proposta (.diff) va preservata,
            # non questa copia sandboxata usata solo per l'esecuzione di pytest.
            if os.path.exists(sandbox_path):
                os.remove(sandbox_path)

        sandbox_passed = proc.returncode == 0
        if not sandbox_passed:
            return VerifyResult(passed=False,
                               errors=[f"il test sandboxato con la patch proposta NON passa: "
                                      f"{proc.stdout[-500:]}"], is_logic_error=True)

        return VerifyResult(passed=True, parsed_output={"new_line9": new_line9.strip(),
                           "new_line10": new_line10.strip(), "sandbox_test_stdout": proc.stdout[-500:]})

    def apply(self, task_record, vr):
        diff_content = (
            f"--- a/server/tests/test_research_control_plane_v2.py\n"
            f"+++ b/server/tests/test_research_control_plane_v2.py (PROPOSTA - non applicata)\n"
            f"@@ linea 9-10 @@\n"
            f"-{self.facts['line9_current'].strip()}\n"
            f"-{self.facts['line10_current'].strip()}\n"
            f"+{vr.parsed_output['new_line9']}\n"
            f"+{vr.parsed_output['new_line10']}\n"
        )
        diff_path = os.path.join(PATCH_ARTIFACT_DIR, "hypothesis_count_fix_v1.diff")
        with open(diff_path, "w", encoding="utf-8") as f:
            f.write(diff_content)
        return ApplyResult(files_changed=[], artifacts_created=[os.path.relpath(diff_path, ROOT)],
                          touches_real_repo_files=True, proposal_only=True)


def build_manifest(task_id):
    return {
        "task_id": task_id, "title": "Fix test fragile hypothesis_count/experiment_count == 8",
        "objective": "Correggere l'asserzione hardcoded in "
                    "test_research_control_plane_v2.py che fallisce perche' il registry e' "
                    "legittimamente cresciuto da 8 a 9 (sia experiments che hypotheses).",
        "task_type": "CODE", "priority": "NORMAL", "risk_level": "A1", "scientific_risk": "NONE",
        "code_risk": "LOW", "financial_risk": "NONE",
        "required_capabilities": ["small_python_functions"],
        "deterministic_tools_available": False, "repo_scope": "server/tests/",
        "files_allowed": ["server/tests/test_research_control_plane_v2.py"],
        "files_forbidden": ["MQL5/*", "Product-Platform/*", "contracts/*"],
        "dependencies": [], "blockers": [],
        "expected_artifacts": ["server/orchestrator_v1/proposed_patches/hypothesis_count_fix_v1.diff"],
        "success_criteria": ["il test sandboxato con la patch proposta passa"],
        "verifier": "server/orchestrator_v1/verify_acceptance_test_1.py",
        "estimated_complexity": "TRIVIAL", "estimated_runtime": "2m", "premium_allowed": False,
        "preferred_executor": "TIER2_LOCAL_STRONG", "fallback_executors": ["TIER3_CLAUDE"],
        "approval_required": "REVIEW_REQUIRED", "created_by": "orchestrator_v1_acceptance_test_1",
        "created_at": "2026-09-28T00:00:00Z", "tenant_id": "tenant-1", "account_scope_id": None,
    }


def main():
    if not ollama_worker.is_ollama_reachable():
        print("Ollama non raggiungibile - impossibile eseguire l'acceptance test #1")
        sys.exit(1)

    facts = _diagnose_real_facts()
    print(f"Fatti diagnosticati (TIER0): experiment_count reale={facts['real_experiment_count']}, "
         f"hypothesis_count reale={facts['real_hypothesis_count']}")

    orch = Orchestrator()
    orch.register_local_handler("fix_hypothesis_count_test", HypothesisCountFixHandler(facts))

    task_id = "TASK_ACCEPT1_HYPOTHESIS_COUNT"
    manifest = build_manifest(task_id)
    orch.submit(manifest, action="fix_hypothesis_count_test", action_params={})
    record = orch.process_task(task_id)

    print(f"\nStato finale: {record['state']}")
    print(f"Decisione RESULT_PACKET: {record['result_packet']['decision']}")
    print(f"Confidence: {record['result_packet']['confidence']}")

    payload = {"facts": facts, "final_task_record": record,
              "ledger_events": orch.ledger.read_for_task(task_id)}
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(ORCH_DIR, "acceptance_test_1_result_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path}")


if __name__ == "__main__":
    main()
