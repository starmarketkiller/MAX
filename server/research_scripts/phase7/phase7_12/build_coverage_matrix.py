#!/usr/bin/env python3
"""Phase 7.12 - Matrice di copertura machine-readable. Riconcilia Phase
7.11 (census, 83 identita') con Phase 7.10 (audit di 20 candidate
stateful) e aggiunge le correzioni/scoperte di questa fase (vedi
build_coverage_gaps_and_candidates.py). NON ripete il census, NON
modifica i file frozen di 7.10/7.11 - solo lettura + arricchimento in
un artifact separato.

Principi espliciti (dalla richiesta):
- "Non auditata" != SAFE.
- SAFE rispetto a UN pattern != validata complessivamente.
- Distingue identita', alias, varianti, implementazioni.
"""
import os
import sys

PHASE712_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE710_DIR = os.path.abspath(os.path.join(PHASE712_DIR, "..", "phase7_10"))
PHASE711_DIR = os.path.abspath(os.path.join(PHASE712_DIR, "..", "phase7_11"))
ROOT = os.path.abspath(os.path.join(PHASE712_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import load_json, save_json, wrap_with_provenance  # noqa: E402

# Correzioni verificate DIRETTAMENTE sul codice in questa fase (Phase 7.12) al campo
# 'stateful' del census 7.11, che risultava ERRATO per questi due casi - vedi
# build_coverage_gaps_and_candidates.py per l'evidenza completa. Il census 7.11 NON
# viene modificato (file frozen) - la correzione vive solo qui.
STATEFUL_FIELD_CORRECTIONS = {
    "FVG_MIT_WINDOW": {
        "census_said": False, "verified_actual": True,
        "evidence": "g_fvgMitWBull[]/g_fvgMitWBear[] (pool di zone FVG persistenti) + "
            "g_fvgMitWLastBar, mutati da NXS_FvgMitWindow_Update() usando NXS_EffTF() "
            "dinamico, senza guardia TF - NXS_Strategies_SMC.mqh:260-310. Il campo "
            "'stateful' del census era False probabilmente perche' la variabile non "
            "segue la convenzione di naming '*State g_*' usata dal grep di Phase 7.10.",
    },
    "OB_MIT": {
        "census_said": False, "verified_actual": True,
        "evidence": "NXS_Strat_OB_Mitigation_Structural() chiama DIRETTAMENTE "
            "NXS_Strat_OrderBlock() come wrapper (NXS_Strategies_SMC.mqh:355-366) - "
            "eredita l'INTERA mutazione di stato g_obBuy/g_obSell di ORDER_BLOCK "
            "(gia' DEFECT_CONFIRMED in Phase 7.10) a ogni chiamata.",
    },
}

# Riclassificazioni motivate da questa fase (vedi coverage_gaps_and_new_candidates
# per il dettaglio completo delle evidenze) - applicate SOLO nella matrice di
# copertura di Phase 7.12, mai retroattivamente sui file frozen di 7.10/7.11.
NEW_CLASSIFICATIONS_7_12 = {
    "FVG_MIT_WINDOW": {
        "classification": "SUSPECT",
        "pattern": "CROSS_TIMEFRAME_STATE_CONTAMINATION",
        "confidence": "MODERATA - struttura del codice identica per forma (gate "
            "lastBar/mutazione con NXS_EffTF() dinamico, nessuna guardia TF) al "
            "meccanismo gia' dimostrato per BREAKOUT_ACC, MA con un commento del "
            "codice (righe 275-278) che dichiara esplicitamente l'intento 'deve girare "
            "sempre... altrimenti il registro perde barre' - la stessa ambiguita' "
            "intento-vs-difetto gia' risolta con adjudication documentale per "
            "BREAKOUT_ACC (Phase 7.9F) qui NON e' stata ripetuta - serve un'analoga "
            "adjudication prima di poter dichiarare DEFECT_CONFIRMED.",
        "not_yet_confirmed_because": "Nessuna adjudication documentale (tipo Phase "
            "7.9F) ne' esperimento empirico eseguiti in questa fase - solo lettura "
            "diretta del codice.",
    },
    "OB_MIT": {
        "classification": "DEFECT_CONFIRMED",
        "pattern": "CROSS_TIMEFRAME_STATE_CONTAMINATION (ereditato da ORDER_BLOCK)",
        "confidence": "ALTA - non e' un'inferenza per analogia strutturale come gli "
            "altri 10 residui: OB_MIT chiama LETTERALMENTE la stessa funzione "
            "NXS_Strat_OrderBlock() gia' classificata DEFECT_CONFIRMED - stessa "
            "evidenza di codice, nessuna nuova ipotesi necessaria. Resta comunque "
            "'strutturale, non empiricamente misurata' come tutti i 10 residui "
            "(nessun esperimento diagnostico dedicato eseguito).",
    },
}


def load_sources():
    census = load_json(os.path.join(PHASE711_DIR, "complete_strategy_census_v1.json"))
    audit = load_json(os.path.join(PHASE710_DIR, "stateful_strategy_static_audit_v1.json"))
    return census["payload"], census["canonical_sha256"], audit["payload"], audit["canonical_sha256"]


def _find_audit_entry(audit_candidates, strategy_id):
    """Il campo 'strategy' di Phase 7.10 a volte combina piu' identita' in una riga
    (es. 'LEVEL_CONFLUENCE / LEVEL_CONFLUENCE_M5') - split esplicito per matchare
    contro i canonical_strategy_id singoli del census 7.11."""
    for c in audit_candidates:
        names = [n.strip() for n in c["strategy"].split("/")]
        if strategy_id in names:
            return c
    return None


def build():
    census, census_sha, audit, audit_sha = load_sources()
    rows = census["census_rows"]
    audit_candidates = audit["candidates"]

    matrix = []
    for r in rows:
        sid = r["canonical_strategy_id"]
        audit_entry = _find_audit_entry(audit_candidates, sid)

        stateful_census = r["stateful"]
        correction = STATEFUL_FIELD_CORRECTIONS.get(sid)
        stateful_verified = correction["verified_actual"] if correction else stateful_census

        audited_in_7_10 = audit_entry is not None
        if audit_entry is not None:
            audit_scope_note = (
                f"Trovata nell'audit 7.10 come parte della riga '{audit_entry['strategy']}' "
                f"({audit_entry['file']}:{audit_entry['lines']}) - classificazione "
                f"{audit_entry['classification']}, stato {audit_entry['status']}."
            )
            defect_7_10 = audit_entry["classification"]
        else:
            audit_scope_note = (
                "NON presente nelle 20 righe dell'audit 7.10 (metodo: grep di struct "
                "'*State g_*' globali + variabili 'static' function-local nei 4 file "
                "NXS_Strategies*.mqh, poi lettura diretta del codice per ciascun "
                "candidato trovato)."
            )
            defect_7_10 = "NOT_AUDITED_IN_PHASE_7_10"

        new_finding = NEW_CLASSIFICATIONS_7_12.get(sid)

        # "SAFE rispetto a un pattern" != "validata complessivamente" - reso esplicito.
        overall_validation_caveat = None
        if defect_7_10 == "SAFE" or (audit_entry and "SAFE" in audit_entry.get("classification", "")):
            overall_validation_caveat = (
                "SAFE si riferisce ESCLUSIVAMENTE al pattern CROSS_TIMEFRAME_STATE_"
                "CONTAMINATION verificato in Phase 7.10 - NON costituisce una "
                "validazione complessiva dell'implementazione (altri difetti, non "
                "cercati in questa fase, potrebbero esistere)."
            )

        reachable_live = bool(r["live_mql5"]) and (
            r.get("selector_presence") is not None or sid in ("SILVER_BULLET", "SH_BMS_RTO_V2"))
        registry_gap = sid in ("CRT", "FVG_MIT_WINDOW")

        matrix.append({
            "canonical_strategy_id": sid,
            "aliases": r["aliases"], "variant_of": r["variant_of"],
            "identity_kind": ("ALIAS" if r["aliases"] and r["variant_of"] is None and sid != r["canonical_strategy_id"]
                              else "VARIANT" if r["variant_of"] else "CANONICAL_IDENTITY"),
            "python_implementation": r["python_implementation"],
            "live_mql5": r["live_mql5"],
            "current_status": r["current_status"],
            "reachable_from_live_router": reachable_live,
            "registry_gap_blocks_execution": registry_gap,
            "stateful_per_census_7_11": stateful_census,
            "stateful_verified_7_12": stateful_verified,
            "stateful_correction_applied": correction is not None,
            "stateful_correction_evidence": correction["evidence"] if correction else None,
            "audited_in_phase_7_10": audited_in_7_10,
            "audit_scope_note_7_10": audit_scope_note,
            "classification_phase_7_10": defect_7_10,
            "classification_phase_7_12_new": new_finding["classification"] if new_finding else None,
            "classification_phase_7_12_pattern": new_finding["pattern"] if new_finding else None,
            "classification_phase_7_12_confidence": new_finding["confidence"] if new_finding else None,
            "not_audited_does_not_mean_safe": (defect_7_10 == "NOT_AUDITED_IN_PHASE_7_10"),
            "safe_is_pattern_scoped_not_overall": overall_validation_caveat,
            "historical_evidence_present": bool(r.get("historical_tests")),
            "historical_evidence_detail": r.get("historical_tests"),
            "evidence_status_census": r.get("evidence_status"),
            "canonical_tf": r.get("canonical_tf"),
            "profile_presence": r.get("profile_presence"),
            "selector_presence": r.get("selector_presence"),
            "lineage_notes": r.get("lineage_notes"),
        })

    n_audited = sum(1 for m in matrix if m["audited_in_phase_7_10"])
    n_stateful_verified = sum(1 for m in matrix if m["stateful_verified_7_12"])
    n_corrections = sum(1 for m in matrix if m["stateful_correction_applied"])

    return {
        "phase": "7.12",
        "sources": {
            "phase_7_11_census_sha256": census_sha,
            "phase_7_10_audit_sha256": audit_sha,
        },
        "no_modification_to_frozen_7_10_7_11": True,
        "no_ea_registry_or_strategy_correction_this_phase": True,
        "total_identities": len(matrix),
        "n_audited_in_phase_7_10": n_audited,
        "n_not_audited": len(matrix) - n_audited,
        "n_stateful_verified_7_12": n_stateful_verified,
        "n_stateful_field_corrections_applied": n_corrections,
        "principles": [
            "'Non auditata' non equivale a SAFE - vedi 'not_audited_does_not_mean_safe' "
            "per riga.",
            "SAFE rispetto a un pattern non equivale a validata complessivamente - vedi "
            "'safe_is_pattern_scoped_not_overall' per riga.",
            "Identita', alias, varianti e implementazioni distinte esplicitamente "
            "('identity_kind').",
        ],
        "matrix": matrix,
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE712_DIR, "strategy_coverage_matrix_v1.json"), doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(f"total={payload['total_identities']} audited={payload['n_audited_in_phase_7_10']} "
          f"corrections={payload['n_stateful_field_corrections_applied']}")
    return doc


if __name__ == "__main__":
    main()
