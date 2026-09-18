#!/usr/bin/env python3
"""Phase 7 sec.3-4 - Feature Registry v2 + Feature-Role Separation.

Legge (non ricalcola) i due audit gia' prodotti in Phase 5.5:
- feature_provenance_registry_v1.json (formula/causal_safety_status/lookback/ecc.)
- feature_redundancy_audit_v1.json (classificazione UNIQUE/REDUNDANT/...)

e li fonde in un registry v2 con i campi richiesti da Phase 7:
leakage_risk, missingness, redundancy_group, allowed_for_discovery,
allowed_for_baseline, role (discovery/baseline_matching/diagnostic/
outcome - una feature NON ha automaticamente tutti i ruoli).

REGOLA ESPLICITA (sec.3): una feature con causal_safety_status diverso
da CAUSAL_SAFE ha SEMPRE allowed_for_discovery=false. Nessuna feature
UNKNOWN in questo registry (tutte le 25 di Phase 5 sono gia' CAUSAL_SAFE
- vedi audit originale) - se in futuro se ne aggiunge una nuova senza
classificazione, DEVE entrare come UNKNOWN/allowed_for_discovery=false,
mai per default true.
"""
import json
import os

# Integrity Patch (post-review, 2026-09-18): ROOT era un path assoluto
# machine-specific hardcoded (profilo utente Windows locale). Derivato
# ora da __file__ - questo script vive in <repo>/server/research_scripts/
# phase7/, quindi la repo root e' tre livelli sopra.
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
PHASE55_DIR = os.path.join(ROOT, "server", "research_scripts", "phase5_5")
PHASE7_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7")

# quali feature (fra le 25) hanno un partner "redundant_of" noto (dalla
# tabella KNOWN_DERIVED_PAIRS di feature_redundancy_audit.py, Phase 5.5)
REDUNDANT_OF = {
    "mean_reversion_score": "lag1_autocorr_rolling",
    "ema_slope_atr_norm": "ema_slope_raw",
    "dist_from_rolling_high_atr": "dist_from_rolling_low_atr",
    "dist_from_prev_day_high_atr": "dist_from_prev_day_low_atr",
    "dist_from_prev_week_high_atr": "dist_from_prev_week_low_atr",
}

# ruoli di default per gruppo semantico - una feature NON riceve
# automaticamente tutti i ruoli; il tempo/calendario e' diagnostico per
# default (rischio di leakage di regime/calendario se usato come
# discovery/baseline senza attenzione - vedi red_team_analysis.json,
# CALENDAR_LEAKAGE)
TIME_FEATURES = {"hour_utc", "day_of_week", "session"}


def leakage_risk_from_status(status: str) -> str:
    return {"CAUSAL_SAFE": "LOW", "CONDITIONAL": "MODERATE",
            "CAUSAL_UNSAFE": "HIGH", "UNKNOWN": "UNKNOWN"}.get(status, "UNKNOWN")


def roles_for(feature_id: str) -> list:
    if feature_id in TIME_FEATURES:
        return ["diagnostic"]
    return ["discovery", "baseline_matching", "diagnostic"]


def main():
    prov = json.load(open(os.path.join(PHASE55_DIR, "feature_provenance_registry_v1.json"), encoding="utf-8"))
    redundancy = json.load(open(os.path.join(PHASE55_DIR, "feature_redundancy_audit_v1.json"), encoding="utf-8"))
    classification = redundancy["classification"]

    entries = []
    for grouped in prov["features"]:
        ids = [s.strip() for s in grouped["feature_id"].split("/")]
        for fid in ids:
            causal_status = grouped["causal_safety_status"]
            redundancy_class = classification.get(fid, "UNKNOWN")
            entry = {
                "feature_id": fid,
                "definition": grouped["formula"],
                "source": grouped["input_data"],
                "observation_time": grouped["observation_point"],
                "causal_safe": causal_status == "CAUSAL_SAFE",
                "causal_safety_status": causal_status,
                "leakage_risk": leakage_risk_from_status(causal_status),
                "missingness": (
                    "NEVER_MISSING (derivata direttamente dal timestamp della barra)" if fid in TIME_FEATURES
                    else "WARMUP_ONLY (vedi missing_data_policy_v1.md, Phase 5.5 - max 75/4809 righe, 1.56%, tutte a inizio serie)"
                ),
                "redundancy_group": redundancy_class,
                "redundant_of": REDUNDANT_OF.get(fid),
                "allowed_for_discovery": causal_status == "CAUSAL_SAFE",
                "allowed_for_baseline": causal_status == "CAUSAL_SAFE",
                "role": roles_for(fid),
                "double_use_risk": (
                    "Se usata SIA per selezionare la condizione di stato di un candidato SIA per il "
                    "matching del baseline, una feature puo' rendere baseline ed evento artificialmente "
                    "simili proprio sulla dimensione che il candidato sta testando (il baseline "
                    "'assorbe' l'effetto). Regola: una feature usata come STATE_CONDITION di un "
                    "candidato (discovery role) non deve essere anche l'UNICA dimensione di matching "
                    "del baseline per quello stesso candidato - vedi baseline_contract_v4.json."
                    if "discovery" in roles_for(fid) and "baseline_matching" in roles_for(fid) else None
                ),
                "version": grouped["version"],
            }
            entries.append(entry)

    registry = {
        "schema_version": 2,
        "source_provenance": "server/research_scripts/phase5_5/feature_provenance_registry_v1.json",
        "source_redundancy": "server/research_scripts/phase5_5/feature_redundancy_audit_v1.json",
        "n_features": len(entries),
        "n_allowed_for_discovery": sum(1 for e in entries if e["allowed_for_discovery"]),
        "rule": "allowed_for_discovery=false per costruzione se causal_safety_status != CAUSAL_SAFE. Nessuna eccezione manuale.",
        "features": entries,
    }
    out_path = os.path.join(PHASE7_DIR, "feature_registry_v2.json")
    json.dump(registry, open(out_path, "w", encoding="utf-8"), indent=2, ensure_ascii=True, default=str)
    print(f"n_features={len(entries)} n_allowed_for_discovery={registry['n_allowed_for_discovery']}")
    print(f"written: {out_path}")


if __name__ == "__main__":
    main()
