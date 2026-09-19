#!/usr/bin/env python3
"""Phase 7.3 sec.19 - phase7_3_engine_readiness_gate_v1.json: cancello
binario gate per gate (nessuna media pesata), stesso pattern usato in
Phase 7.0B/7.2B. READY_FOR_FIRST_SEQUENCE_DISCOVERY=true SOLO se TUTTI
i 12 gate sono veri."""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
PHASE73_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def path_exists(*parts):
    return os.path.exists(os.path.join(PHASE73_DIR, *parts))


def main():
    # Gate 1: eligible_sequence_inventory_built
    elig = load(os.path.join(PHASE73_DIR, "phase7_3_eligible_sequence_families_v1.json"))
    elig_payload = elig.get("payload", elig)
    n_eligible = elig_payload.get("n_eligible") or len(elig_payload.get("eligible_sequences", []))
    eligible_sequence_inventory_built = path_exists("phase7_3_eligible_sequence_families_v1.json") and n_eligible >= 1

    # Gate 2: detector_contract_pass
    contract = load(os.path.join(PHASE73_DIR, "sequence_detector_contract_v1.json"))
    detector_contract_pass = path_exists("sequence_detector_contract_v1.json") and \
        len(contract.get("hard_requirements", [])) >= 5

    # Gate 3: temporal_causality_guard_pass - eseguito realmente, non solo presenza del file.
    causality_module = os.path.join(PHASE73_DIR, "engine", "sequence_causality_guard.py")
    import subprocess
    result_causality = subprocess.run([sys.executable, causality_module], capture_output=True, text=True)
    temporal_causality_guard_pass = result_causality.returncode == 0 and \
        "Tutti i casi del causality guard verificati" in result_causality.stdout

    # Gate 4: episode_first_architecture_pass - eseguito realmente.
    episode_module = os.path.join(PHASE73_DIR, "engine", "sequence_episode_engine.py")
    result_episode = subprocess.run([sys.executable, episode_module], capture_output=True, text=True)
    episode_first_architecture_pass = result_episode.returncode == 0

    # Gate 5: baseline_v4_adapter_pass - eseguito realmente.
    baseline_module = os.path.join(PHASE73_DIR, "sequence_baseline_adapter_v1.py")
    result_baseline = subprocess.run([sys.executable, baseline_module], capture_output=True, text=True)
    baseline_v4_adapter_pass = result_baseline.returncode == 0

    # Gate 6: outcome_surface_v3_contract_pass - eseguito realmente.
    outcome_module = os.path.join(PHASE73_DIR, "outcome_surface_v3.py")
    result_outcome = subprocess.run([sys.executable, outcome_module], capture_output=True, text=True)
    outcome_surface_v3_contract_pass = result_outcome.returncode == 0

    # Gate 7: preregistration_guard_integrated + Gate 8: lifecycle_integrated
    # (stesso modulo li integra entrambi - eseguito realmente).
    governance_module = os.path.join(PHASE73_DIR, "engine", "sequence_engine_governance.py")
    result_governance = subprocess.run([sys.executable, governance_module], capture_output=True, text=True)
    governance_pass = result_governance.returncode == 0 and "verificata" in result_governance.stdout
    preregistration_guard_integrated = governance_pass
    lifecycle_integrated = governance_pass

    # Gate 9: failure_memory_integrated - stesso governance module copre
    # anche enforce_failure_memory_gate; verificato dai casi 2/3 del suo demo.
    failure_memory_integrated = governance_pass and "DIRECT_REPEAT" in result_governance.stdout

    # Gate 10: synthetic_e2e_pass - eseguito realmente, tutti i 12 check devono passare.
    suite_module = os.path.join(PHASE73_DIR, "test_phase7_3_synthetic_suite.py")
    result_suite = subprocess.run([sys.executable, suite_module], capture_output=True, text=True)
    synthetic_e2e_pass = result_suite.returncode == 0 and "0 FAIL" in result_suite.stdout

    # Gate 11: red_team_pass - eseguito realmente, 0 blocker residui.
    redteam_module = os.path.join(PHASE73_DIR, "phase7_3_red_team.py")
    result_redteam = subprocess.run([sys.executable, redteam_module], capture_output=True, text=True)
    red_team_pass = result_redteam.returncode == 0 and "0 blocker residui" in result_redteam.stdout

    # Gate 12: no_real_outcome_edge_discovery_performed - scansione strutturale:
    # nessuno script di Phase 7.3 importa/legge path di dataset NEXUS reali
    # (market_state/outcomes/validation/holdout) ne' calcola un delta_p su
    # dati reali. Auto-esclusione del proprio file per evitare il falso
    # positivo da self-reference (stesso pattern di Phase 7.2B).
    forbidden_tokens = ["market_state_dataset", "outcomes_holdout", "data_cache_new_period",
                        "phase7_1_run_results", "phase7_1_frozen_discovery_spec",
                        "final_holdout_seal", "locked_validation_dataset", "real_discovery_run"]
    self_name = os.path.basename(os.path.abspath(__file__))
    offenders = []
    for dirpath, _dirnames, filenames in os.walk(PHASE73_DIR):
        if "__pycache__" in dirpath:
            continue
        for fname in filenames:
            if not (fname.endswith(".py") or fname.endswith(".json") or fname.endswith(".jsonl")):
                continue
            if fname == self_name:
                continue
            fpath = os.path.join(dirpath, fname)
            with open(fpath, encoding="utf-8") as f:
                content = f.read()
            for tok in forbidden_tokens:
                if tok in content:
                    offenders.append((os.path.relpath(fpath, PHASE73_DIR), tok))
    # Ulteriore verifica positiva: il red-team artifact prodotto deve
    # confermare 0 attacchi con ΔP/edge reale calcolato.
    redteam_artifact = load(os.path.join(PHASE73_DIR, "phase7_3_red_team_v1.json"))
    no_delta_p_in_redteam = "delta_p" not in json.dumps(redteam_artifact)
    no_real_outcome_edge_discovery_performed = len(offenders) == 0 and no_delta_p_in_redteam

    gates = {
        "eligible_sequence_inventory_built": eligible_sequence_inventory_built,
        "detector_contract_pass": detector_contract_pass,
        "temporal_causality_guard_pass": temporal_causality_guard_pass,
        "episode_first_architecture_pass": episode_first_architecture_pass,
        "baseline_v4_adapter_pass": baseline_v4_adapter_pass,
        "outcome_surface_v3_contract_pass": outcome_surface_v3_contract_pass,
        "preregistration_guard_integrated": preregistration_guard_integrated,
        "lifecycle_integrated": lifecycle_integrated,
        "failure_memory_integrated": failure_memory_integrated,
        "synthetic_e2e_pass": synthetic_e2e_pass,
        "red_team_pass": red_team_pass,
        "no_real_outcome_edge_discovery_performed": no_real_outcome_edge_discovery_performed,
    }
    unresolved_blockers = [name for name, ok in gates.items() if not ok]
    ready = len(unresolved_blockers) == 0

    payload = dict(gates)
    payload.update({
        "n_eligible_sequences": n_eligible,
        "eligible_sequence_ids": elig_payload.get("eligible_sequences", elig_payload.get("eligible_sequence_ids", [])),
        "nexus_data_scan_offenders": offenders,
        "unresolved_blockers": unresolved_blockers,
        "READY_FOR_FIRST_SEQUENCE_DISCOVERY": ready,
        "rule": "READY_FOR_FIRST_SEQUENCE_DISCOVERY=true SOLO se tutte le 12 gate sopra sono vere - nessuna media pesata, nessun punteggio.",
        "explicit_confirmation": "NO REAL NEXUS EDGE DISCOVERY PERFORMED IN PHASE 7.3",
    })
    save_json(os.path.join(PHASE73_DIR, "phase7_3_engine_readiness_gate_v1.json"),
              wrap_with_provenance(payload, "phase7/phase7_3/build_phase7_3_engine_readiness_gate.py"))
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return ready


if __name__ == "__main__":
    ready = main()
    sys.exit(0 if ready else 1)
