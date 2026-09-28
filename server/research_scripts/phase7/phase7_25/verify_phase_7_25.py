#!/usr/bin/env python3
"""Phase 7.25 - verificatore indipendente. Ri-deriva ogni artifact dai
builder; controllo ancorato (evento uscito a SL -> |net_pnl| ~= risk_r);
verifica che Phase 7.21/7.22/7.23/7.24 non siano state toccate; verifica
che nessun file MQL5/Product-Platform/contracts sia stato modificato;
verifica la decisione finale e i flag di non-deploy."""
import os
import subprocess
import sys

PHASE725_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE725_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE725_DIR)
import build_liq_sweep_data_exposure_map as exposure_builder  # noqa: E402
import build_liq_sweep_baseline_economics as baseline_builder  # noqa: E402
import build_liq_sweep_concentration_analysis as concentration_builder  # noqa: E402
import build_liq_sweep_statistical_uncertainty as stats_builder  # noqa: E402
import build_liq_sweep_cost_stress as cost_builder  # noqa: E402
import build_liq_sweep_execution_realism as execn_builder  # noqa: E402
import build_liq_sweep_temporal_robustness as temporal_builder  # noqa: E402
import build_liq_sweep_visual_audit as visual_builder  # noqa: E402
import build_liq_sweep_path_anatomy as path_builder  # noqa: E402
import build_liq_sweep_oos_forward_analysis as oos_builder  # noqa: E402
import build_liq_sweep_minimum_viable_capital as mvc_builder  # noqa: E402
import build_liq_sweep_comparison_with_prior_strategies as comparison_builder  # noqa: E402
import build_liq_sweep_edge_decision_card as decision_builder  # noqa: E402
from nxs_liq_sweep_edge_dataset_loader import load_closed_events, net_pnl, risk_r  # noqa: E402

ARTIFACTS = [
    ("data_exposure_map_v1.json", exposure_builder.build),
    ("baseline_economics_v1.json", baseline_builder.build),
    ("concentration_analysis_v1.json", concentration_builder.build),
    ("statistical_uncertainty_v1.json", stats_builder.build),
    ("cost_stress_v1.json", cost_builder.build),
    ("execution_realism_v1.json", execn_builder.build),
    ("temporal_robustness_v1.json", temporal_builder.build),
    ("visual_audit_sample_v1.json", visual_builder.build),
    ("path_anatomy_v1.json", path_builder.build),
    ("oos_forward_analysis_v1.json", oos_builder.build),
    ("minimum_viable_capital_v1.json", mvc_builder.build),
    ("comparison_with_prior_strategies_v1.json", comparison_builder.build),
    ("decision_card_v1.json", decision_builder.build),
]

ALLOWED_DECISIONS = {"EDGE_VALIDATED_PRELIMINARY", "EDGE_CANDIDATE_REQUIRES_OOS",
                     "EDGE_CANDIDATE_REQUIRES_FORWARD_VALIDATION", "EDGE_NOT_SUPPORTED",
                     "INSUFFICIENT_EVIDENCE"}

FROZEN_PHASE_DIRS = ["phase7_21", "phase7_22", "phase7_23", "phase7_24"]


def verify():
    errors = []

    for fname, build_fn in ARTIFACTS:
        path = os.path.join(PHASE725_DIR, fname)
        if not os.path.exists(path):
            errors.append(f"{fname}: file mancante")
            continue
        saved = load_json(path)
        fresh = build_fn()
        if canonical_sha256(fresh) != canonical_sha256(saved["payload"]):
            errors.append(f"{fname}: ricostruzione indipendente differisce dal file salvato")

    # --- controllo ancorato: evento uscito a SL -> |net_pnl| ~= risk_r
    # (stesso principio di Phase 7.21/7.22). ---
    events = load_closed_events()
    sl_events = [e for e in events if "sl" in (e["exit"]["exit_reason"] or "").lower()]
    if events and not sl_events:
        errors.append("nessun evento con exit_reason 'sl' trovato - controllo ancorato impossibile")
    for e in sl_events[:5]:
        diff = abs(abs(net_pnl(e)) - risk_r(e))
        if diff > max(20.0, 0.5 * risk_r(e)):
            errors.append(f"controllo ancorato: evento {e['event_id']} uscito a SL ha "
                          f"|net_pnl-risk_r| = {diff:.2f}, oltre la tolleranza attesa")

    # --- nessun lotto anomalo residuo (bug gia' noto e corretto in Phase 7.22,
    # verificato qui non essere ricomparso nel dataset LIQ_SWEEP). ---
    zero_lot = [e for e in events if e.get("lots") is not None and e["lots"] <= 0]
    if zero_lot:
        errors.append(f"{len(zero_lot)} eventi CLOSED con lots<=0 (atteso 0.01 fisso)")

    # --- Phase 7.21/7.22/7.23/7.24 non toccate. ---
    for phase_dir in FROZEN_PHASE_DIRS:
        result = subprocess.run(["git", "diff", "--name-only", "--",
                                f"server/research_scripts/phase7/{phase_dir}"],
                               cwd=ROOT, capture_output=True, text=True)
        if result.stdout.strip():
            errors.append(f"{phase_dir} risulta modificato in una fase che deve lasciarlo congelato: "
                          f"{result.stdout.strip()}")

    # --- nessuna modifica a MQL5/Product-Platform/contracts. ---
    result = subprocess.run(["git", "status", "--porcelain", "--", "MQL5/", "Product-Platform/",
                            "contracts/"], cwd=ROOT, capture_output=True, text=True)
    modified = [l for l in result.stdout.strip().splitlines() if l.strip()]
    if modified:
        errors.append(f"file MQL5/Product-Platform/contracts risultano modificati: {modified}")

    # --- cost stress: costi strettamente crescenti. ---
    cost = load_json(os.path.join(PHASE725_DIR, "cost_stress_v1.json"))["payload"]
    costs_in_order = [cost["scenarios"][k]["extra_roundtrip_cost_assumed_price_units"]
                      for k in ("COST_BASE", "COST_MODERATE", "COST_STRESS")]
    if costs_in_order != sorted(costs_in_order) or len(set(costs_in_order)) != 3:
        errors.append("cost_stress: i 3 scenari non hanno costo strettamente crescente")

    # --- decisione ammessa + non-deploy. ---
    decision = load_json(os.path.join(PHASE725_DIR, "decision_card_v1.json"))["payload"]
    if decision["decision"] not in ALLOWED_DECISIONS:
        errors.append(f"decisione '{decision['decision']}' non ammessa")
    if decision.get("decision_means_live_ready") is not False:
        errors.append("decision_means_live_ready deve essere esplicitamente False")
    if decision.get("no_optimization_performed") is not True:
        errors.append("decision card: manca no_optimization_performed=True")

    # --- visual audit: Stage A strutturalmente privo di campi di esito. ---
    visual = load_json(os.path.join(PHASE725_DIR, "visual_audit_sample_v1.json"))["payload"]
    forbidden_keys = {"actual_pnl", "exit_timestamp", "exit_price", "exit_reason", "mfe", "mae",
                      "r_multiple"}
    for stratum, revs in visual["reviews"].items():
        for rev in revs:
            shown = set(rev["stage_a_blind_review"]["data_shown"])
            if shown & forbidden_keys:
                errors.append(f"visual audit: Stage A di {rev['event_id']} espone campi di esito: "
                              f"{shown & forbidden_keys}")

    return errors


def main():
    errors = verify()
    if errors:
        print(f"VERIFY FAILED: {len(errors)} problemi")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print("VERIFY OK: tutti i controlli indipendenti passati (0 problemi)")
    sys.exit(0)


if __name__ == "__main__":
    main()
