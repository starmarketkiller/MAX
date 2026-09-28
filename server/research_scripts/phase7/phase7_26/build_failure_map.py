#!/usr/bin/env python3
"""Phase 7.26 punto E - FAILURE_MAP_V1. Una strategia puo' avere piu'
failure mode contemporaneamente. Ogni tag e' giustificato da un
riferimento a un artifact GIA' ESISTENTE (nessun numero ricalcolato ad
hoc qui) - se un dato non e' disponibile per una strategia, il campo
resta None, mai inventato."""
import os
import sys

PHASE726_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE726_DIR, "..", "..", "..", ".."))
P7 = os.path.join(ROOT, "server", "research_scripts", "phase7")
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402

sys.path.insert(0, PHASE726_DIR)
from nxs_schemas import FAILURE_MODE_TAXONOMY  # noqa: E402


def _tag(mode, evidence_ref, note):
    assert mode in FAILURE_MODE_TAXONOMY, f"tag non in tassonomia: {mode}"
    return {"mode": mode, "evidence_ref": evidence_ref, "note": note}


def _breakout_acc():
    decision = load_json(os.path.join(P7, "phase7_21", "breakoutacc_decision_card_v1.json"))["payload"]
    ev = decision["supporting_evidence_summary"]
    tags = [
        _tag("OUTLIER_DEPENDENT", "phase7_21/breakoutacc_decision_card_v1.json:"
            "supporting_evidence_summary.top_5_trades_pct_of_total_net",
            f"top-5 = {ev['top_5_trades_pct_of_total_net']:.1f}% del netto totale."),
        _tag("DIRECTION_DEPENDENT", "phase7_21/breakoutacc_decision_card_v1.json:h2_buy_more_robust_than_sell_verdict",
            "CI95 SELL esclude lo zero sul lato negativo, CI95 BUY lo esclude sul lato positivo "
            "(debolmente) - asimmetria direzionale statisticamente supportata, non solo osservata."),
        _tag("OOS_DEGRADATION", "phase7_21/breakoutacc_decision_card_v1.json:supporting_evidence_summary.oos_status",
            f"OOS forward: 1 solo trade, {ev['oos_status']}."),
    ]
    return tags


def _order_block():
    decision = load_json(os.path.join(P7, "phase7_22", "orderblock_decision_card_v1.json"))["payload"]
    ev = decision["supporting_evidence_summary"]
    tags = [
        _tag("OUTLIER_DEPENDENT", "phase7_22/orderblock_decision_card_v1.json:checks.4_concentration_detail",
            decision["checks"]["4_concentration_detail"]),
        _tag("LOW_SAMPLE", "phase7_22/orderblock_baseline_economics_v1.json:ALL.n_trades",
            "n=13 - qualunque statistica su questo campione e' fragile per costruzione."),
        _tag("OOS_DEGRADATION", "phase7_22/orderblock_decision_card_v1.json:supporting_evidence_summary.oos_status",
            f"OOS forward: 0 trade, {ev['oos_status']}."),
    ]
    return tags


def _tsi():
    decision = load_json(os.path.join(P7, "phase7_18", "tsi_decision_card_v2.json"))["payload"]
    tags = [
        _tag("IMPLEMENTATION_DEFECT", "phase7_17/tsi_decision_card_v1.json + phase7_18/tsi_decision_card_v2.json",
            "Bug reale trovato e CORRETTO (contaminazione universale pre-fix, guardia TF-scoped "
            f"aggiunta) - decisione finale: {decision['decision']}. Nessun dataset economico mai "
            "costruito per TSI (fase puramente di integrita' di implementazione, non di edge) - "
            "gli altri tag della tassonomia (economici) sono NON_APPLICABILE per costruzione."),
    ]
    return tags


def _liq_sweep():
    decision = load_json(os.path.join(P7, "phase7_25", "decision_card_v1.json"))["payload"]
    conc = load_json(os.path.join(P7, "phase7_25", "concentration_analysis_v1.json"))["payload"]
    temporal = load_json(os.path.join(P7, "phase7_25", "temporal_robustness_v1.json"))["payload"]
    tags = [
        _tag("OUTLIER_DEPENDENT", "phase7_25/concentration_analysis_v1.json:concentration.top_5",
            f"top-5 = {conc['concentration']['top_5']['pct_of_total_net']:.1f}% del netto totale, "
            f"edge_survives_without_top_5={conc['edge_survives_without_top_5']}."),
        _tag("TEMPORALLY_CONCENTRATED", "phase7_25/temporal_robustness_v1.json:by_year",
            f"{temporal['years_with_positive_net']}/{temporal['years_total_with_at_least_1_trade']} "
            "anni positivi - il 2025 da solo spiega circa il 99% del netto totale."),
        _tag("REGIME_DEPENDENT", "phase7_25/temporal_robustness_v1.json:dependent_on_single_regime",
            "flag esplicito dependent_on_single_regime=True nell'artifact."),
        _tag("OOS_DEGRADATION", "phase7_25/decision_card_v1.json:supporting_evidence_summary",
            f"OOS forward: {decision['supporting_evidence_summary']['oos_n_trades']} trade, "
            f"net/trade={decision['supporting_evidence_summary']['oos_net_pnl_per_trade']:.2f} "
            "(primo campione OOS del corpus sufficiente per una prima lettura, e negativo)."),
    ]
    return tags


def build():
    payload = {
        "taxonomy": FAILURE_MODE_TAXONOMY,
        "multiple_tags_allowed_per_strategy": True,
        "strategies": {
            "BREAKOUT_ACC": {"phase": "7.21", "failure_modes": _breakout_acc()},
            "ORDER_BLOCK": {"phase": "7.22", "failure_modes": _order_block()},
            "TSI": {"phase": "7.17/7.18", "failure_modes": _tsi(),
                   "note": "Nessun dataset economico esiste per TSI - solo un fix di integrita' "
                          "dell'implementazione (contaminazione universale pre-fix). I failure "
                          "mode economici (concentrazione, OOS, ecc.) sono NON_APPLICABILE, non "
                          "assenti per omissione."},
            "LIQ_SWEEP": {"phase": "7.23-7.25", "failure_modes": _liq_sweep()},
        },
        "no_tag_invented_every_tag_has_evidence_ref": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE726_DIR, "failure_map_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    for strat, d in payload["strategies"].items():
        print(f"  {strat}: {[t['mode'] for t in d['failure_modes']]}")


if __name__ == "__main__":
    main()
