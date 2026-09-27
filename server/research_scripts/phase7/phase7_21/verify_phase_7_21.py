#!/usr/bin/env python3
"""Phase 7.21 - verificatore indipendente. Ri-deriva ogni artifact dai
builder; verifica che il calcolo del P&L netto sia coerente (verificato
CONTRO il primo evento del dataset dove |realized_pnl|==risk_r, un
controllo indipendente ancorato a un valore noto, non solo la
ri-derivazione dello stesso codice); verifica l'assenza di look-ahead
nella preregistrazione (l'ipotesi e' congelata PRIMA dell'OOS); verifica
che la finestra OOS dichiarata untouched non compaia nel trace raw
usato per costruire il dataset di scoperta; verifica che nessun file
MQL5/Product-Platform/contracts sia stato toccato."""
import csv
import os
import subprocess
import sys

PHASE721_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE79G_DIR = os.path.abspath(os.path.join(PHASE721_DIR, "..", "phase7_9g"))
ROOT = os.path.abspath(os.path.join(PHASE721_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE721_DIR)
import build_data_exposure_map as exposure_builder  # noqa: E402
import build_baseline_economics as baseline_builder  # noqa: E402
import build_cost_stress as cost_builder  # noqa: E402
import build_execution_realism as execn_builder  # noqa: E402
import build_visual_audit_sample as visual_builder  # noqa: E402
import build_temporal_robustness as temporal_builder  # noqa: E402
import build_statistical_uncertainty as stats_builder  # noqa: E402
import build_oos_forward_analysis as oos_builder  # noqa: E402
import build_minimum_viable_capital as mvc_builder  # noqa: E402
import build_breakoutacc_decision_card as decision_builder  # noqa: E402
import build_frozen_forward_config as frozen_builder  # noqa: E402
from nxs_breakoutacc_dataset_loader import load_opened_events, net_pnl, risk_r  # noqa: E402

ARTIFACTS = [
    ("data_exposure_map_v1.json", exposure_builder.build),
    ("baseline_economics_v1.json", baseline_builder.build),
    ("cost_stress_v1.json", cost_builder.build),
    ("execution_realism_v1.json", execn_builder.build),
    ("visual_audit_sample_v1.json", visual_builder.build),
    ("temporal_robustness_v1.json", temporal_builder.build),
    ("statistical_uncertainty_v1.json", stats_builder.build),
    ("oos_forward_analysis_v1.json", oos_builder.build),
    ("minimum_viable_capital_v1.json", mvc_builder.build),
    ("breakoutacc_decision_card_v1.json", decision_builder.build),
    ("frozen_forward_config_v1.json", frozen_builder.build),
]

ALLOWED_DECISIONS = {"EDGE_VALIDATED_PRELIMINARY", "EDGE_CANDIDATE_REQUIRES_OOS",
                     "EDGE_CANDIDATE_REQUIRES_FORWARD_VALIDATION", "EDGE_NOT_SUPPORTED",
                     "INSUFFICIENT_EVIDENCE"}


def verify():
    errors = []

    for fname, build_fn in ARTIFACTS:
        path = os.path.join(PHASE721_DIR, fname)
        if not os.path.exists(path):
            errors.append(f"{fname}: file mancante")
            continue
        saved = load_json(path)
        fresh = build_fn()
        if canonical_sha256(fresh) != canonical_sha256(saved["payload"]):
            errors.append(f"{fname}: ricostruzione indipendente differisce dal file salvato")

    # --- controllo ancorato: il PRIMO evento del dataset canonico ha
    # |realized_pnl| == risk_r esattamente (uscito a SL) - se questa
    # identita' nota si rompe, la logica net_pnl/risk_r e' stata alterata. ---
    events = load_opened_events()
    first = next((e for e in events if e["event_id"] == "evt_1209b7abca9456d1"), None)
    if first is None:
        errors.append("evento ancora evt_1209b7abca9456d1 non trovato - impossibile il controllo "
                      "ancorato del calcolo net_pnl/risk_r")
    else:
        if abs(abs(first["realized_pnl"]) - risk_r(first)) > 0.01:
            errors.append("controllo ancorato fallito: |realized_pnl| != risk_r per "
                          "evt_1209b7abca9456d1 (atteso: uscita a SL, valori quasi identici)")

    # --- preregistrazione: l'hypothesis deve dichiararsi congelata PRIMA
    # di qualunque risultato OOS. ---
    exposure = load_json(os.path.join(PHASE721_DIR, "data_exposure_map_v1.json"))["payload"]
    if not exposure["hypothesis_preregistration"]["frozen_before_any_new_result_examined"]:
        errors.append("hypothesis_preregistration non dichiara 'frozen_before_any_new_result_examined'")
    if exposure["hypothesis_preregistration"]["hypothesis_secondary"]["status"].find("POST_HOC") < 0:
        errors.append("H2 (BUY piu' robusto di SELL) non e' dichiarata esplicitamente post-hoc")

    # --- la finestra OOS dichiarata 'genuinely_untouched' non deve comparire
    # nel trace raw usato per costruire il dataset di scoperta (verifica
    # indipendente diretta sul file raw, non sul dictionary del builder). ---
    raw_trace_path = os.path.join(PHASE79G_DIR, "raw_data", "postfix_live_ea_trace_events.csv")
    if os.path.exists(raw_trace_path):
        with open(raw_trace_path, encoding="utf-8-sig") as f:
            raw_rows = list(csv.DictReader(f))
        after_cutoff = [r for r in raw_rows if r["timestamp"] > "2026.08.14"]
        if after_cutoff:
            errors.append(f"il trace raw di scoperta contiene {len(after_cutoff)} righe oltre il "
                          "cutoff dichiarato (2026.08.14) - la finestra OOS potrebbe non essere "
                          "genuinamente untouched")
    else:
        errors.append("trace raw di scoperta (phase7_9g/raw_data/postfix_live_ea_trace_events.csv) "
                      "non trovato - impossibile verificare l'esposizione della finestra OOS")

    # --- il file grezzo forward OOS committato deve essere coerente con
    # quanto dichiarato nell'analisi OOS. ---
    oos = load_json(os.path.join(PHASE721_DIR, "oos_forward_analysis_v1.json"))["payload"]
    forward_csv = os.path.join(PHASE721_DIR, "nexus_trades_forward_oos.csv")
    if not os.path.exists(forward_csv):
        errors.append("nexus_trades_forward_oos.csv mancante - il run forward non risulta catturato")
    else:
        with open(forward_csv, encoding="utf-8-sig") as f:
            forward_rows = list(csv.DictReader(f))
        n_closes = sum(1 for r in forward_rows if r["action"] == "CLOSE")
        if n_closes != oos["n_closed_trades_breakout_acc"]:
            errors.append(f"oos_forward_analysis dichiara {oos['n_closed_trades_breakout_acc']} "
                          f"trade chiusi ma il CSV grezzo ne contiene {n_closes}")

    # --- decisione finale ammessa e coerente con i checks dichiarati. ---
    decision = load_json(os.path.join(PHASE721_DIR, "breakoutacc_decision_card_v1.json"))["payload"]
    if decision["decision"] not in ALLOWED_DECISIONS:
        errors.append(f"decisione '{decision['decision']}' non ammessa")
    if decision["decision"] == "EDGE_VALIDATED_PRELIMINARY":
        checks = decision["checks"]
        required_true = [k for k in checks if k.startswith(("1_", "2_", "3_", "4_", "5_")) and
                         not k.endswith(("_note", "_detail"))]
        if not all(checks[k] for k in required_true):
            errors.append("decisione EDGE_VALIDATED_PRELIMINARY dichiarata ma non tutti i 5 check "
                          "sono True")
    if decision["decision_means_live_ready"] is not False:
        errors.append("decision_means_live_ready deve essere esplicitamente False")

    # --- se la decisione richiede forward validation, deve esistere una
    # config congelata. ---
    if decision["decision"] == "EDGE_CANDIDATE_REQUIRES_FORWARD_VALIDATION":
        frozen = load_json(os.path.join(PHASE721_DIR, "frozen_forward_config_v1.json"))["payload"]
        if frozen.get("not_executed_only_frozen") is not True:
            errors.append("frozen_forward_config: manca la dichiarazione not_executed_only_frozen")
        if frozen.get("no_live_deploy") is not True:
            errors.append("frozen_forward_config: manca la dichiarazione no_live_deploy")

    # --- nessuna modifica a MQL5/Product-Platform/contracts in questa fase
    # (nessuna autorizzazione data - fase di sola misurazione/analisi). ---
    result = subprocess.run(["git", "status", "--porcelain", "--", "MQL5/", "Product-Platform/",
                            "contracts/"], cwd=ROOT, capture_output=True, text=True)
    modified = [l for l in result.stdout.strip().splitlines() if l.strip()]
    if modified:
        errors.append(f"file MQL5/Product-Platform/contracts risultano modificati in una fase di "
                      f"sola validazione economica: {modified}")

    # --- cost stress: scenario non scelto per preservare l'edge (i 3
    # scenari devono avere costo crescente 0 < moderate < stress). ---
    cost = load_json(os.path.join(PHASE721_DIR, "cost_stress_v1.json"))["payload"]
    costs_in_order = [cost["scenarios"][k]["extra_roundtrip_cost_assumed_price_units"]
                      for k in ("COST_BASE", "COST_MODERATE", "COST_STRESS")]
    if costs_in_order != sorted(costs_in_order) or len(set(costs_in_order)) != 3:
        errors.append("cost_stress: i 3 scenari non hanno costo strettamente crescente "
                      "(possibile selezione post-hoc)")

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
