#!/usr/bin/env python3
"""Verifica INDIPENDENTE di NEXUS TASK #0002 (Research Safety Net Auto-
Backfill) - non si fida del self-report, ricontrolla dai file grezzi e
dallo stato reale del repository. Fail-closed."""
import json
import os
import re
import subprocess
import sys

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))
PHASE726_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_26")


def _load(fname):
    with open(os.path.join(ORCH_DIR, fname), encoding="utf-8") as f:
        return json.load(f)["payload"]


def verify():
    errors = []
    result = _load("nexus_task_0002_result_v1.json")

    # 1. Il file REALE del repository non deve mai essere stato modificato.
    proc = subprocess.run(["git", "diff", "--stat",
                          "server/research_scripts/phase7/phase7_26/"
                          "cross_strategy_learning_packets_v1.json"],
                         capture_output=True, text=True, cwd=ROOT)
    if proc.stdout.strip():
        errors.append("il file REALE cross_strategy_learning_packets_v1.json risulta "
                     f"modificato nel working tree: {proc.stdout}")

    # 2. Il task finale deve essere WAITING_APPROVAL (mai COMPLETED - tocca un file reale).
    if result["final_task_state"] != "WAITING_APPROVAL":
        errors.append(f"stato finale atteso WAITING_APPROVAL, trovato "
                     f"{result['final_task_state']}")

    # 3. Il file proposto e la provenance map devono esistere.
    proposed_path = os.path.join(ORCH_DIR, "proposed_patches",
                                "cross_strategy_learning_packets_v1_PROPOSED_UPDATE.json")
    prov_path = os.path.join(ORCH_DIR, "proposed_patches",
                            "safety_net_backfill_provenance_map_v1.json")
    if not os.path.exists(proposed_path):
        errors.append("manca il file proposto del Learning Packet")
    if not os.path.exists(prov_path):
        errors.append("manca la provenance map")

    # 4. Nessun campo fuori scope modificato nel file proposto (solo i 5 attesi).
    if os.path.exists(proposed_path):
        with open(proposed_path, encoding="utf-8") as f:
            proposed = json.load(f)["payload"]
        original = _load_original_packet()
        expected_changed = {("BREAKOUT_ACC", "temporal_concentration"),
                           ("BREAKOUT_ACC", "exit_efficiency"),
                           ("BREAKOUT_ACC", "execution_degradation"),
                           ("BREAKOUT_ACC", "favorable_before_loss"),
                           ("BREAKOUT_ACC", "adverse_before_win"),
                           ("ORDER_BLOCK", "temporal_concentration"),
                           ("ORDER_BLOCK", "exit_efficiency")}
        actually_changed = set()
        for strat in original["packets"]:
            for field in original["packets"][strat]:
                if field == "provenance":
                    continue
                if original["packets"][strat][field] != proposed["packets"][strat][field]:
                    actually_changed.add((strat, field))
        unexpected = actually_changed - expected_changed
        if unexpected:
            errors.append(f"campi modificati FUORI dallo scope dichiarato: {unexpected}")

        # 5. Nessun 'verdict'/hypothesis/holdout field toccato (controllo esplicito sui nomi
        # di campo piu' sensibili, anche se gia' coperto sopra).
        sensitive_fields = {"failure_modes", "candidate_hypotheses", "confidence", "fidelity",
                           "strategy_identity", "mechanism"}
        for strat in original["packets"]:
            for field in sensitive_fields:
                if field in original["packets"][strat] and \
                   original["packets"][strat][field] != proposed["packets"][strat].get(field):
                    errors.append(f"campo sensibile '{field}' modificato per {strat} - "
                                 "MAI permesso in un backfill di completamento")

        # 6. Ri-verifica indipendente dei valori numerici DERIVABLE_NOW (non solo lettura).
        errors += _reverify_derivable_now_values(proposed)

        # 7. Anti-allucinazione: nessuna percentuale nelle narrative deve essere ingiustificata.
        for strat, field in [("BREAKOUT_ACC", "temporal_concentration"),
                            ("ORDER_BLOCK", "temporal_concentration")]:
            text = proposed["packets"][strat][field]
            percentages = [float(m.replace(",", ".")) for m in
                         re.findall(r"(\d+(?:[.,]\d+)?)\s*%", text)]
            if percentages:
                # ricalcolo diretto dal file NEXUS_TASK_0001 corrispondente
                src = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_28",
                                  f"nexus0001_result_{strat.lower()}_temporal_v1.json")
                with open(src, encoding="utf-8") as f:
                    raw = json.load(f)
                plausible = [0.0, 100.0]
                if raw["years_total_with_at_least_1_trade"]:
                    plausible.append(round(raw["years_with_positive_net"] /
                                          raw["years_total_with_at_least_1_trade"] * 100, 2))
                for p in percentages:
                    if not any(abs(p - q) < 1.5 for q in plausible):
                        errors.append(f"{strat}.{field}: percentuale '{p}%' non giustificata "
                                    f"dai dati grezzi (plausibili: {plausible})")

    # 8. Data Exposure Registry non deve mai essere stato toccato.
    de_path = os.path.join(PHASE726_DIR, "data_exposure_registry_v1.json")
    proc2 = subprocess.run(["git", "diff", "--stat", de_path], capture_output=True, text=True,
                          cwd=ROOT)
    if proc2.stdout.strip():
        errors.append(f"data_exposure_registry_v1.json risulta modificato: {proc2.stdout}")

    # 9. Suite di test deve passare.
    proc3 = subprocess.run([sys.executable, "-m", "pytest",
                          "server/tests/test_nexus_task_0002.py", "-q"],
                         capture_output=True, text=True, cwd=ROOT, timeout=120)
    if proc3.returncode != 0:
        errors.append(f"test_nexus_task_0002.py non passa: {proc3.stdout[-1000:]}")

    if not errors:
        print("VERIFY PASSED - NEXUS TASK #0002 coerente con i dati grezzi e con lo stato repo")
        return True
    print("VERIFY FAILED:")
    for e in errors:
        print(f"  - {e}")
    return False


def _load_original_packet():
    path = os.path.join(PHASE726_DIR, "cross_strategy_learning_packets_v1.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)["payload"]


def _reverify_derivable_now_values(proposed):
    errors = []
    sys.path.insert(0, ORCH_DIR)
    from core.deterministic_worker import execute as det_execute

    funnel = det_execute("compute_percentage_rates", {
        "counts_path": "server/research_scripts/phase7/phase7_21/execution_realism_v1.json",
        "counts_key": ["funnel_counts"],
        "numerator_paths": {
            "pct_generated_that_get_blocked": ["blocked_by_execution_gates_11"],
            "pct_generated_that_get_rejected": ["order_sent_47_plus_rejected_9", "sent_rejected"],
            "pct_generated_that_open_per_certificate": ["opened_with_real_pnl_47"],
        }, "denominator_path": ["live_trace_generated_67"]})
    if proposed["packets"]["BREAKOUT_ACC"]["execution_degradation"] != funnel["output"]["rates"]:
        errors.append("BREAKOUT_ACC.execution_degradation nel file proposto non corrisponde "
                     "al ricalcolo indipendente")

    for field, excursion, outcome in [("favorable_before_loss", "v2_mfe", "loss"),
                                      ("adverse_before_win", "v2_mae", "win")]:
        r = det_execute("join_breakout_acc_path_anatomy_outcome_conditional_excursion", {
            "path_anatomy_artifact": "server/research_scripts/phase7/phase7_9k/"
                                    "breakout_acc_path_anatomy_v2.json",
            "events_loader_module": "server/research_scripts/phase7/phase7_21",
            "excursion_field": excursion, "outcome_condition": outcome})
        if proposed["packets"]["BREAKOUT_ACC"][field] != r["output"]:
            errors.append(f"BREAKOUT_ACC.{field} nel file proposto non corrisponde al "
                         "ricalcolo indipendente")
    return errors


if __name__ == "__main__":
    ok = verify()
    sys.exit(0 if ok else 1)
