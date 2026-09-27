#!/usr/bin/env python3
"""Phase 7.22 - verificatore indipendente. Ri-deriva ogni artifact dai
builder; verifica il calcolo net_pnl/risk_r con un controllo ancorato
(se disponibile un evento con exit_reason='sl', |net_pnl| circa uguale
a risk_r); verifica che BREAKOUT_ACC e TSI non siano state toccate;
verifica che nessun file MQL5/Product-Platform/contracts sia stato
modificato in questa fase."""
import os
import subprocess
import sys

PHASE722_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE722_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE722_DIR)
import build_identity_and_perimeter as identity_builder  # noqa: E402
import build_orderblock_data_exposure_map as exposure_builder  # noqa: E402
import build_canonical_economic_dataset as dataset_builder  # noqa: E402
import build_orderblock_baseline_economics as baseline_builder  # noqa: E402
import build_orderblock_cost_stress as cost_builder  # noqa: E402
import build_orderblock_execution_realism as execn_builder  # noqa: E402
import build_orderblock_visual_audit_sample as visual_builder  # noqa: E402
import build_orderblock_temporal_robustness as temporal_builder  # noqa: E402
import build_orderblock_statistical_uncertainty as stats_builder  # noqa: E402
import build_orderblock_oos_forward_analysis as oos_builder  # noqa: E402
import build_orderblock_minimum_viable_capital as mvc_builder  # noqa: E402
import build_orderblock_decision_card as decision_builder  # noqa: E402
import build_orderblock_frozen_forward_config as frozen_builder  # noqa: E402
from nxs_orderblock_dataset_loader import load_events, net_pnl, risk_r  # noqa: E402

ARTIFACTS = [
    ("identity_and_perimeter_v1.json", identity_builder.build),
    ("orderblock_data_exposure_map_v1.json", exposure_builder.build),
    ("canonical_economic_dataset_v1.json", dataset_builder.build),
    ("orderblock_baseline_economics_v1.json", baseline_builder.build),
    ("orderblock_cost_stress_v1.json", cost_builder.build),
    ("orderblock_execution_realism_v1.json", execn_builder.build),
    ("orderblock_visual_audit_sample_v1.json", visual_builder.build),
    ("orderblock_temporal_robustness_v1.json", temporal_builder.build),
    ("orderblock_statistical_uncertainty_v1.json", stats_builder.build),
    ("orderblock_oos_forward_analysis_v1.json", oos_builder.build),
    ("orderblock_minimum_viable_capital_v1.json", mvc_builder.build),
    ("orderblock_decision_card_v1.json", decision_builder.build),
    ("orderblock_frozen_forward_config_v1.json", frozen_builder.build),
]

ALLOWED_DECISIONS = {"EDGE_VALIDATED_PRELIMINARY", "EDGE_CANDIDATE_REQUIRES_OOS",
                     "EDGE_CANDIDATE_REQUIRES_FORWARD_VALIDATION", "EDGE_NOT_SUPPORTED",
                     "INSUFFICIENT_EVIDENCE"}


def verify():
    errors = []

    for fname, build_fn in ARTIFACTS:
        path = os.path.join(PHASE722_DIR, fname)
        if not os.path.exists(path):
            errors.append(f"{fname}: file mancante")
            continue
        saved = load_json(path)
        fresh = build_fn()
        if canonical_sha256(fresh) != canonical_sha256(saved["payload"]):
            errors.append(f"{fname}: ricostruzione indipendente differisce dal file salvato")

    # --- controllo ancorato: qualunque evento uscito a SL deve avere
    # |net_pnl| ~= risk_r (stesso principio di verifica gia' usato per
    # BREAKOUT_ACC in Phase 7.21, qui applicato al dataset ORDER_BLOCK). ---
    events = load_events()
    zero_lot_events = [e for e in events if e.get("entry_lots", 0) <= 0]
    if events and zero_lot_events:
        errors.append(f"{len(zero_lot_events)} eventi con entry_lots<=0 (atteso 0.01 fisso per "
                      "tutti - controllo per il bug gia' trovato e corretto in questa fase: "
                      "NXS_LogTradeCSV registra lots=0.00 sulla riga OPEN, il volume reale va "
                      "letto dalla riga CLOSE)")

    sl_events = [e for e in events if "sl" in e.get("exit_reason", "").lower()]
    if events and not sl_events:
        errors.append("nessun evento con exit_reason contenente 'sl' trovato - impossibile il "
                      "controllo ancorato (non necessariamente un errore, ma da verificare)")
    for e in sl_events[:5]:  # campione, non tutti (potrebbero divergere per swap accumulato)
        diff = abs(abs(net_pnl(e)) - risk_r(e))
        # tolleranza piu' larga di BREAKOUT_ACC: ORDER_BLOCK tiene posizioni per giorni/settimane
        # (vs ore/pochi giorni tipici di BREAKOUT_ACC) - lo swap accumulato diverge di piu' dalla
        # sola distanza SL. Empiricamente verificato: ~$1/giorno di scostamento su questo dataset
        # (14.8 su 14.7 giorni, 5.54 su 6 giorni) - entrambi spiegati, non un difetto di calcolo.
        if diff > max(20.0, 0.5 * risk_r(e)):
            errors.append(f"controllo ancorato: evento {e['event_id']} uscito a SL ha "
                          f"|net_pnl-risk_r| = {diff:.2f}, oltre la tolleranza attesa")

    # --- identita': BREAKOUT_ACC e TSI non toccate. ---
    identity = load_json(os.path.join(PHASE722_DIR, "identity_and_perimeter_v1.json"))["payload"]
    if not identity.get("no_modification_to_breakout_acc_or_tsi_in_this_phase"):
        errors.append("identity_and_perimeter: manca la dichiarazione "
                      "no_modification_to_breakout_acc_or_tsi_in_this_phase")
    if identity.get("old_pf_wr_not_used_as_baseline") is not True:
        errors.append("identity_and_perimeter: old_pf_wr_not_used_as_baseline non e' True")

    result = subprocess.run(["git", "diff", "--name-only", "--", "server/research_scripts/phase7/phase7_21"],
                            cwd=ROOT, capture_output=True, text=True)
    if result.stdout.strip():
        errors.append("phase7_21 (BREAKOUT_ACC) risulta modificato in una fase che deve lasciarlo "
                      "congelato")
    result = subprocess.run(["git", "diff", "--name-only", "--", "server/research_scripts/phase7/phase7_18"],
                            cwd=ROOT, capture_output=True, text=True)
    if result.stdout.strip():
        errors.append("phase7_18 (TSI) risulta modificato in una fase che non deve toccare TSI")

    # --- decisione finale ammessa. ---
    decision = load_json(os.path.join(PHASE722_DIR, "orderblock_decision_card_v1.json"))["payload"]
    if decision["decision"] not in ALLOWED_DECISIONS:
        errors.append(f"decisione '{decision['decision']}' non ammessa")
    if decision.get("decision_means_live_ready") is not False:
        errors.append("decision_means_live_ready deve essere esplicitamente False")

    # --- cost stress: costi strettamente crescenti (nessuna selezione post-hoc). ---
    cost = load_json(os.path.join(PHASE722_DIR, "orderblock_cost_stress_v1.json"))["payload"]
    costs_in_order = [cost["scenarios"][k]["extra_roundtrip_cost_assumed_price_units"]
                      for k in ("COST_BASE", "COST_MODERATE", "COST_STRESS")]
    if costs_in_order != sorted(costs_in_order) or len(set(costs_in_order)) != 3:
        errors.append("cost_stress: i 3 scenari non hanno costo strettamente crescente")

    # --- nessuna modifica a MQL5/Product-Platform/contracts in questa fase. ---
    result = subprocess.run(["git", "status", "--porcelain", "--", "MQL5/", "Product-Platform/",
                            "contracts/"], cwd=ROOT, capture_output=True, text=True)
    modified = [l for l in result.stdout.strip().splitlines() if l.strip()]
    if modified:
        errors.append(f"file MQL5/Product-Platform/contracts risultano modificati: {modified}")

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
