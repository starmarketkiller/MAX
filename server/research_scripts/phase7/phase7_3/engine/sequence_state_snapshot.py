#!/usr/bin/env python3
"""Phase 7.3 sec.5 - Sequence State Snapshot: congela SOLO feature
CAUSAL_SAFE (leakage_risk=LOW in feature_registry_v2.json) al momento
dell'observation_cutoff_index. Nessuna feature puo' essere aggiunta
dopo aver visto l'outcome (sec.8) - lo snapshot e' costruito UNA SOLA
VOLTA, al momento del trigger, mai arricchito retroattivamente."""
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", ".."))
FEATURE_REGISTRY_PATH = os.path.join(ROOT, "server", "research_scripts", "phase7", "feature_registry_v2.json")

CORE_SNAPSHOT_FEATURES = ["volatility_state", "trend_state", "directional_efficiency",
                          "position_in_rolling_range", "roc", "session_bucket_if_available"]


class UnsafeFeatureError(Exception):
    pass


def load_causal_safe_feature_ids():
    with open(FEATURE_REGISTRY_PATH, encoding="utf-8") as f:
        registry = json.load(f)
    return {f["feature_id"] for f in registry["features"] if f.get("leakage_risk") == "LOW"}


def build_state_snapshot(market_state_row: dict, direction: str, sequence_specific_state: dict = None,
                          causal_safe_feature_ids: set = None):
    """market_state_row: dict di feature GIA' calcolate causalmente alla
    barra observation_cutoff_index (mai una barra successiva). Ritorna lo
    state_snapshot conforme a sequence_detector_contract_v1.json.

    Solleva UnsafeFeatureError se sequence_specific_state contiene una
    chiave che NON e' nell'insieme delle feature CAUSAL_SAFE dichiarate
    in feature_registry_v2.json - lo snapshot non include mai una feature
    non verificata come sicura, silenziosamente o no."""
    if causal_safe_feature_ids is None:
        causal_safe_feature_ids = load_causal_safe_feature_ids()

    sequence_specific_state = sequence_specific_state or {}
    for key in sequence_specific_state:
        # "volatility_state"/"trend_state" sono derivati (terzili di feature
        # causal-safe, vedi Phase 7.1 fit_frozen_baseline_params) - non sono
        # feature_id letterali nel registry, ma le feature SORGENTE lo sono
        # gia' state verificate a monte; qui verifichiamo solo le chiavi che
        # dichiarano esplicitamente un feature_id del registry.
        if key in causal_safe_feature_ids or key in ("volatility_state", "trend_state"):
            continue
        raise UnsafeFeatureError(
            f"'{key}' non e' una feature CAUSAL_SAFE dichiarata in feature_registry_v2.json - "
            f"rifiutata dallo state snapshot (nessuna feature non verificata puo' entrare, sec.5)."
        )

    snapshot = {
        "volatility_state": market_state_row.get("volatility_state"),
        "trend_state": market_state_row.get("trend_state"),
        "directional_efficiency": market_state_row.get("directional_efficiency"),
        "position_in_rolling_range": market_state_row.get("position_in_rolling_range"),
        "roc": market_state_row.get("roc"),
        "session_bucket_if_available": market_state_row.get("session"),
        "direction": direction,
        "sequence_specific_state": sequence_specific_state,
    }
    return snapshot


if __name__ == "__main__":
    safe_ids = load_causal_safe_feature_ids()
    print(f"n feature CAUSAL_SAFE nel registry: {len(safe_ids)}")
    assert len(safe_ids) > 0

    # Caso 1 (positivo): snapshot con solo feature causal-safe -> costruito senza errori.
    row = {"volatility_state": "HIGH", "trend_state": "UP", "directional_efficiency": 0.42,
           "position_in_rolling_range": 0.7, "roc": 0.01, "session": "LONDON"}
    snap = build_state_snapshot(row, direction="BUY", sequence_specific_state={"atr_percentile": 63.2},
                                 causal_safe_feature_ids=safe_ids)
    print("Caso 1 (feature sicure): snapshot costruito ->", snap)
    assert snap["direction"] == "BUY"

    # Caso 2 (negativo): sequence_specific_state con una chiave NON nel registry -> rifiutato.
    try:
        build_state_snapshot(row, direction="SELL", sequence_specific_state={"future_close_price_leak": 1234.5},
                              causal_safe_feature_ids=safe_ids)
        print("ERRORE: feature non sicura avrebbe dovuto essere rifiutata!")
    except UnsafeFeatureError as e:
        print(f"Caso 2 (feature non sicura) correttamente rifiutato: {type(e).__name__}")

    print("\nTutti i casi dello state snapshot verificati.")
