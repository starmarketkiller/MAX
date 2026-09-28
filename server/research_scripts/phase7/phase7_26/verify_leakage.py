#!/usr/bin/env python3
"""Phase 7.26 - verificatore di leakage/integrita' cross-registry. Non
ricostruisce gli artifact (lo fa verify_phase_7_26.py) - controlla
INVECE le REGOLE STRUTTURALI trasversali che nessun singolo builder
puo' verificare da solo: la regola discovery!=validation delle
hypothesis, la causalita' delle feature pre-entry, l'assenza di campi
di esito nella selezione dei non-eventi, e la coerenza interna del
registro di esposizione dati."""
import os
import sys

PHASE726_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE726_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import load_json  # noqa: E402

sys.path.insert(0, PHASE726_DIR)
from nxs_matched_non_event_builder import verify_no_outcome_fields_used  # noqa: E402
from nxs_pre_entry_feature_store import verify_feature_set_causal, FeatureLeakageError, make_feature  # noqa: E402


def verify_hypothesis_discovery_validation_separation():
    """Regola obbligatoria: una hypothesis SUPPORTED/REJECTED non puo'
    avere il dataset di discovery come UNICA fonte di validation, a
    meno che non dichiari esplicitamente mechanical_verification_exception."""
    errors = []
    hyp = load_json(os.path.join(PHASE726_DIR, "hypothesis_registry_v1.json"))["payload"]
    for h in hyp["hypotheses"]:
        if h["lifecycle_state"] not in ("SUPPORTED", "REJECTED"):
            continue
        val_ids = h["validation_dataset_ids"] or []
        only_same_as_discovery = val_ids and all(v == h["discovery_dataset_id"] for v in val_ids)
        if only_same_as_discovery and not h.get("mechanical_verification_exception"):
            errors.append(f"{h['hypothesis_id']}: lifecycle={h['lifecycle_state']} ma "
                          "validation_dataset_ids coincide col discovery_dataset_id senza "
                          "mechanical_verification_exception=True - violazione della regola "
                          "discovery!=validation.")
        if not val_ids and not h.get("mechanical_verification_exception"):
            errors.append(f"{h['hypothesis_id']}: lifecycle={h['lifecycle_state']} ma "
                          "validation_dataset_ids e' vuoto - nessuna validazione indipendente "
                          "dichiarata.")
    return errors


def verify_matched_non_event_no_outcome_leakage():
    violations = verify_no_outcome_fields_used()
    return [f"nxs_matched_non_event_builder: possibile riferimento a campo di esito '{v}' nel "
           f"codice di selezione" for v in violations]


def verify_pre_entry_feature_causality_self_test():
    """Auto-test del modulo: costruisce una feature causalmente valida
    (deve passare) e una causalmente INVALIDA (deve essere rifiutata) -
    se il rifiuto non avviene, il modulo stesso e' rotto."""
    errors = []
    from datetime import datetime
    decision_ts = datetime(2026, 1, 10, 12, 0)
    try:
        make_feature(value=1.0, source="test", timestamp=datetime(2026, 1, 10, 11, 0),
                    availability_time=datetime(2026, 1, 10, 11, 0), timeframe="H1",
                    forming_or_closed_bar="CLOSED", fidelity="EVENT_LEVEL_FAITHFUL",
                    decision_timestamp=decision_ts)
    except FeatureLeakageError:
        errors.append("make_feature ha rifiutato una feature CAUSALMENTE VALIDA (falso positivo)")

    leaked = False
    try:
        make_feature(value=1.0, source="test_future", timestamp=datetime(2026, 1, 10, 13, 0),
                    availability_time=datetime(2026, 1, 10, 13, 0), timeframe="H1",
                    forming_or_closed_bar="CLOSED", fidelity="EVENT_LEVEL_FAITHFUL",
                    decision_timestamp=decision_ts)
    except FeatureLeakageError:
        leaked = True
    if not leaked:
        errors.append("make_feature NON ha rifiutato una feature disponibile DOPO la decisione "
                      "- leakage non filtrato (falso negativo, bug critico)")
    return errors


def verify_data_exposure_internal_consistency():
    """Un dataset non puo' essere sia oos_exposure=True (consumato come
    OOS) sia holdout_status che dichiara NOT_USED/UNVERIFIED (mai
    attraversato) - contraddizione interna."""
    errors = []
    registry = load_json(os.path.join(PHASE726_DIR, "data_exposure_registry_v1.json"))["payload"]
    for r in registry["records"]:
        status = r["holdout_status"].split(" - ")[0]
        if r.get("oos_exposure") and status in ("NOT_USED", "UNVERIFIED"):
            errors.append(f"{r['dataset_id']}: oos_exposure=True ma holdout_status='{status}' - "
                          "contraddizione (un dataset consumato come OOS non puo' essere ancora "
                          "'mai usato').")
    return errors


def verify_synthesis_never_declares_edge_found():
    synthesis = load_json(os.path.join(PHASE726_DIR, "cross_strategy_synthesis_v1.json"))["payload"]
    errors = []
    if synthesis.get("cannot_produce_edge_found") is not True:
        errors.append("cross_strategy_synthesis_v1.json non dichiara cannot_produce_edge_found=True")
    for f in synthesis["findings"]:
        if "EDGE_FOUND" in f["statement"].upper() or f["kind"] not in (
                "OBSERVATION", "CROSS_STRATEGY_PATTERN", "CANDIDATE_HYPOTHESIS"):
            errors.append(f"finding con kind/testo non ammesso: {f}")
    return errors


def verify():
    errors = []
    errors += verify_hypothesis_discovery_validation_separation()
    errors += verify_matched_non_event_no_outcome_leakage()
    errors += verify_pre_entry_feature_causality_self_test()
    errors += verify_data_exposure_internal_consistency()
    errors += verify_synthesis_never_declares_edge_found()
    return errors


def main():
    errors = verify()
    if errors:
        print(f"LEAKAGE VERIFY FAILED: {len(errors)} problemi")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print("LEAKAGE VERIFY OK: nessuna violazione strutturale trovata")
    sys.exit(0)


if __name__ == "__main__":
    main()
