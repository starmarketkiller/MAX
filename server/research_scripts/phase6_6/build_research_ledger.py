#!/usr/bin/env python3
"""Phase 6.6 sec.6 - Research Ledger v1: registro (logicamente append-only)
delle transizioni di stato dell'idea "sweep+reclaim", da H004 (Phase 5,
scoperta post-hoc) fino allo stato attuale (H006 RETAIN_E2, Phase 6.6).

Ogni voce e' un fatto storico gia' accaduto - questo script non decide
nulla, riformatta solo la sequenza di eventi gia' documentata nei
report/artifact delle fasi precedenti."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from canonical_utils import ROOT, wrap_with_provenance, save_json, rel_path  # noqa: E402

PHASE66_DIR = os.path.dirname(os.path.abspath(__file__))

TRANSITIONS = [
    {
        "seq": 1,
        "timestamp": "2026-09-17T18:00:00Z",
        "phase": "Phase5",
        "event_type": "HYPOTHESIS_DISCOVERED",
        "entity": "H004_EVENT_RECLAIM",
        "from_status": None,
        "to_status": "SUPPORTED_EDGE (classificazione originale Phase 5, poi rivista)",
        "reason": "Test su un batch di 14 ipotesi (9 event-alone + 5 interazioni); RECLAIM unico risultato chiaramente positivo su discovery E validation nello stesso run.",
        "source_artifact": "server/research_scripts/phase5/data/edge_results_v1.json",
        "commit": "bd274e1",
    },
    {
        "seq": 2,
        "timestamp": "2026-09-17T20:00:00Z",
        "phase": "Phase5.5",
        "event_type": "CONTAMINATION_IDENTIFIED",
        "entity": "H004_EVENT_RECLAIM",
        "from_status": "SUPPORTED_EDGE",
        "to_status": "POST_HOC_CANDIDATE",
        "reason": "Independent Validation Integrity taxonomy applicata retroattivamente: la selezione di RECLAIM come headline e' avvenuta DOPO aver visto i risultati di validazione di tutti i 14 candidati - classificato CONTAMINATED_VALIDATION, non TRUE_HOLDOUT.",
        "source_artifact": "vault/01-Trading/_phase4_artifacts/independent_validation_integrity_v1.md",
        "commit": "9b1076e",
    },
    {
        "seq": 3,
        "timestamp": "2026-09-17T20:00:00Z",
        "phase": "Phase5.5",
        "event_type": "EVIDENCE_GRADE_ASSIGNED",
        "entity": "H004_EVENT_RECLAIM",
        "from_status": None,
        "to_status": "E2",
        "reason": "Scala di evidenza E0-E6 formalizzata; H004 assegnato E2 (INTERNAL_VALIDATION) per la contaminazione identificata al passo precedente.",
        "source_artifact": "vault/01-Trading/_phase4_artifacts/evidence_grading_and_decision_card_v1.md",
        "commit": "9b1076e",
    },
    {
        "seq": 4,
        "timestamp": "2026-09-18T00:00:00Z",
        "phase": "Phase6",
        "event_type": "HYPOTHESIS_PREREGISTERED",
        "entity": "H006_LIQUIDITY_SWEEP_RECLAIM_TRUE_HOLDOUT",
        "from_status": None,
        "to_status": "PRE_REGISTERED",
        "reason": "Nuova ipotesi congelata (detector identico a H004, zero semantic drift) con criteri PASS/BORDERLINE/FAIL dichiarati PRIMA di acquisire il dataset di holdout.",
        "source_artifact": "server/research_scripts/phase6/H006_frozen_spec.json",
        "commit": "b9414e6",
    },
    {
        "seq": 5,
        "timestamp": "2026-09-18T09:00:00Z",
        "phase": "Phase6",
        "event_type": "TRUE_HOLDOUT_EXECUTED",
        "entity": "H006_LIQUIDITY_SWEEP_RECLAIM_TRUE_HOLDOUT",
        "from_status": "PRE_REGISTERED",
        "to_status": "BORDERLINE",
        "reason": "Test su Dukascopy XAUUSD 2022-02-04..2023-02-03 (mai visto prima): n=115, DeltaP=+0.057 (sotto soglia 0.15), CI95 sovrapposte, consistenza direzionale BUY/SELL fallita.",
        "source_artifact": "server/research_scripts/phase6/h006_primary_result.json",
        "commit": "b9414e6",
    },
    {
        "seq": 6,
        "timestamp": "2026-09-18T09:00:00Z",
        "phase": "Phase6",
        "event_type": "EVIDENCE_GRADE_RETAINED",
        "entity": "H006_LIQUIDITY_SWEEP_RECLAIM_TRUE_HOLDOUT",
        "from_status": "E2 (ereditato da H004)",
        "to_status": "E2",
        "reason": "Regola congelata in H006_frozen_spec.json: if_FAIL_or_BORDERLINE -> resta E2. Nessuna promozione a E3.",
        "source_artifact": "vault/01-Trading/NEXUS - Phase 6 True Holdout Validation Sweep Reclaim.md",
        "commit": "b9414e6",
    },
    {
        "seq": 7,
        "timestamp": "2026-09-18T10:00:00Z",
        "phase": "Phase6.5",
        "event_type": "METHODOLOGICAL_AUDIT",
        "entity": "H006_LIQUIDITY_SWEEP_RECLAIM_TRUE_HOLDOUT",
        "from_status": "E2",
        "to_status": "E2 (invariato - audit, non re-test)",
        "reason": "Dependence diagnostics: dependence_flag=HIGH, overlap_rate=99.1%, n_effective fra 46 e 115 a seconda del metodo. Block bootstrap: CI +9.5% piu' ampia dell'iid.",
        "source_artifact": "server/research_scripts/phase6_5/h006_dependence_audit.json",
        "commit": "0e78972",
    },
    {
        "seq": 8,
        "timestamp": "2026-09-18T10:00:00Z",
        "phase": "Phase6.5",
        "event_type": "DIRECTIONAL_BASELINE_CORRECTED",
        "entity": "H006_LIQUIDITY_SWEEP_RECLAIM_TRUE_HOLDOUT",
        "from_status": "E2",
        "to_status": "E2 (invariato - audit, non re-test)",
        "reason": "Baseline v3 direction-aware: BUY-only baseline (50.5%) e SELL-only baseline (56.9%) non comparabili. DeltaP corretto: BUY -0.010->+0.019, SELL +0.139->+0.104. Asimmetria persiste ma ridimensionata.",
        "source_artifact": "server/research_scripts/phase6_5/h006_directional_baseline_v3.json",
        "commit": "0e78972",
    },
    {
        "seq": 9,
        "timestamp": "2026-09-18T10:00:00Z",
        "phase": "Phase6.5",
        "event_type": "POST_HOC_OBSERVATION_REGISTERED",
        "entity": "SELL_SWEEP_RECLAIM_ASYMMETRY",
        "from_status": None,
        "to_status": "POST_HOC_OBSERVATION",
        "reason": "Asimmetria BUY/SELL osservata, esplicitamente NON promossa a ipotesi/edge. Nessun test H007 eseguito.",
        "source_artifact": "server/research_scripts/phase6_5/directional_diagnostics_policy.json",
        "commit": "0e78972",
    },
    {
        "seq": 10,
        "timestamp": "2026-09-18T12:00:00Z",
        "phase": "Phase6.6",
        "event_type": "EVIDENCE_NORMALIZED",
        "entity": "H006_LIQUIDITY_SWEEP_RECLAIM_TRUE_HOLDOUT",
        "from_status": "E2",
        "to_status": "E2 (RETAIN_E2, decision card strutturata)",
        "reason": "Normalizzazione in Canonical Evidence Record v2, con primary_evidence e retroactive_methodological_audit tenuti separati. Nessuna ri-validazione, nessuna promozione.",
        "source_artifact": "server/research_scripts/phase6_6/h006_evidence_v2.json",
        "commit": "PENDING (questo commit)",
    },
]


def build():
    ledger = {
        "schema_version": 1,
        "description": "Ledger logicamente append-only delle transizioni di stato per l'idea sweep+reclaim (H004->H006). Ogni voce e' immutabile una volta scritta - correzioni future si aggiungono come nuove voci con seq incrementale, non sovrascrivono voci esistenti.",
        "entity_chain": "H004_EVENT_RECLAIM -> H006_LIQUIDITY_SWEEP_RECLAIM_TRUE_HOLDOUT",
        "transitions": TRANSITIONS,
        "current_state_summary": {
            "hypothesis_id": "H006_LIQUIDITY_SWEEP_RECLAIM_TRUE_HOLDOUT",
            "evidence_grade": "E2",
            "decision": "RETAIN_E2",
            "as_of_seq": 10,
        },
    }
    return ledger


if __name__ == "__main__":
    ledger = build()
    wrapped = wrap_with_provenance(ledger, script="server/research_scripts/phase6_6/build_research_ledger.py")
    out_path = os.path.join(PHASE66_DIR, "research_evidence_ledger_v1.json")
    save_json(out_path, wrapped)
    print(f"canonical_sha256: {wrapped['canonical_sha256']}")
    print(f"written: {out_path}")
