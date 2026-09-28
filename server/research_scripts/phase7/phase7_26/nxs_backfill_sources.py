#!/usr/bin/env python3
"""Phase 7.26 - path e loader di sola lettura verso gli artifact GIA'
esistenti delle 4 strategie di backfill (BREAKOUT_ACC, ORDER_BLOCK,
TSI, LIQ_SWEEP). Nessuna fase precedente viene modificata. Un campo
assente ritorna None (mai un valore inventato) - vedi nxs_schemas.py
per l'elenco dei campi richiesti che il verificatore controlla."""
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
PHASE7_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7")


def _p(phase, fname):
    return os.path.join(PHASE7_DIR, phase, fname)


def load(phase, fname):
    """Ritorna il payload del JSON, o None se il file non esiste -
    mai solleva, mai inventa un default diverso da None."""
    path = _p(phase, fname)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    return doc.get("payload", doc)


def get_path(field, *keys):
    """dict.get annidato sicuro: get_path(d, 'a','b') == d['a']['b'] se
    esiste, altrimenti None."""
    cur = field
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


# --- BREAKOUT_ACC (Phase 7.9c-7.9k identita'/meccanismo, Phase 7.21 economia) ---
BREAKOUT_ACC = {
    "identity_v2": lambda: load("phase7_9k", "breakout_acc_decision_card_v2.json"),
    "path_anatomy_v2": lambda: load("phase7_9k", "breakout_acc_path_anatomy_v2.json"),
    "failure_map_v2": lambda: load("phase7_9k", "breakout_acc_failure_map_v2.json"),
    "data_exposure_map": lambda: load("phase7_21", "data_exposure_map_v1.json"),
    "baseline_economics": lambda: load("phase7_21", "baseline_economics_v1.json"),
    "concentration_temporal": lambda: load("phase7_21", "temporal_robustness_v1.json"),
    "statistical_uncertainty": lambda: load("phase7_21", "statistical_uncertainty_v1.json"),
    "cost_stress": lambda: load("phase7_21", "cost_stress_v1.json"),
    "execution_realism": lambda: load("phase7_21", "execution_realism_v1.json"),
    "oos_forward": lambda: load("phase7_21", "oos_forward_analysis_v1.json"),
    "mvc": lambda: load("phase7_21", "minimum_viable_capital_v1.json"),
    "visual_audit": lambda: load("phase7_21", "visual_audit_sample_v1.json"),
    "decision_card": lambda: load("phase7_21", "breakoutacc_decision_card_v1.json"),
}

# --- ORDER_BLOCK (Phase 7.12-7.16 identita'/fix, Phase 7.22 economia) ---
ORDER_BLOCK = {
    "identity": lambda: load("phase7_22", "identity_and_perimeter_v1.json"),
    "data_exposure_map": lambda: load("phase7_22", "orderblock_data_exposure_map_v1.json"),
    "baseline_economics": lambda: load("phase7_22", "orderblock_baseline_economics_v1.json"),
    "temporal_robustness": lambda: load("phase7_22", "orderblock_temporal_robustness_v1.json"),
    "cost_stress": lambda: load("phase7_22", "orderblock_cost_stress_v1.json"),
    "execution_realism": lambda: load("phase7_22", "orderblock_execution_realism_v1.json"),
    "oos_forward": lambda: load("phase7_22", "orderblock_oos_forward_analysis_v1.json"),
    "mvc": lambda: load("phase7_22", "orderblock_minimum_viable_capital_v1.json"),
    "visual_audit": lambda: load("phase7_22", "orderblock_visual_audit_sample_v1.json"),
    "decision_card": lambda: load("phase7_22", "orderblock_decision_card_v1.json"),
}

# --- TSI (Phase 7.17/7.18) - SOLO integrita' di meccanismo, MAI un'evidenza
# economica (nessun dataset P&L esiste per TSI in questo progetto). ---
TSI = {
    "semantic_map": lambda: load("phase7_17", "tsi_semantic_map_v1.json"),
    "historical_evidence": lambda: load("phase7_17", "tsi_historical_evidence_map_v1.json"),
    "decision_card_v2": lambda: load("phase7_18", "tsi_decision_card_v2.json"),
    "parity_comparison": lambda: load("phase7_18", "tsi_parity_comparison_v1.json"),
}

# --- LIQ_SWEEP (Phase 7.23 integrita', 7.24 adjudication, 7.25 edge validation) ---
LIQ_SWEEP = {
    "identity_map": lambda: load("phase7_23", "liq_sweep_identity_map_v1.json"),
    "integrity_decision": lambda: load("phase7_23", "liq_sweep_decision_card_v1.json"),
    "canonical_dataset": lambda: load("phase7_24", "liq_sweep_canonical_dataset_v1.json"),
    "funnel_accounting": lambda: load("phase7_24", "funnel_accounting_v1.json"),
    "readiness_decision": lambda: load("phase7_24", "liq_sweep_readiness_decision_card_v1.json"),
    "data_exposure_map": lambda: load("phase7_25", "data_exposure_map_v1.json"),
    "baseline_economics": lambda: load("phase7_25", "baseline_economics_v1.json"),
    "concentration": lambda: load("phase7_25", "concentration_analysis_v1.json"),
    "statistical_uncertainty": lambda: load("phase7_25", "statistical_uncertainty_v1.json"),
    "temporal_robustness": lambda: load("phase7_25", "temporal_robustness_v1.json"),
    "cost_stress": lambda: load("phase7_25", "cost_stress_v1.json"),
    "execution_realism": lambda: load("phase7_25", "execution_realism_v1.json"),
    "path_anatomy": lambda: load("phase7_25", "path_anatomy_v1.json"),
    "visual_audit": lambda: load("phase7_25", "visual_audit_sample_v1.json"),
    "oos_forward": lambda: load("phase7_25", "oos_forward_analysis_v1.json"),
    "mvc": lambda: load("phase7_25", "minimum_viable_capital_v1.json"),
    "decision_card": lambda: load("phase7_25", "decision_card_v1.json"),
}

STRATEGY_SOURCES = {"BREAKOUT_ACC": BREAKOUT_ACC, "ORDER_BLOCK": ORDER_BLOCK,
                   "TSI": TSI, "LIQ_SWEEP": LIQ_SWEEP}
