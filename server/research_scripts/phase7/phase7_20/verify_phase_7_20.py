#!/usr/bin/env python3
"""Phase 7.20 - verificatore indipendente. Ri-deriva ogni artifact dai
builder e confronta gli hash; verifica che la copertura della matrice
sia esattamente 83 (l'intero census); verifica che nessuna
classificazione usi il PF come unico criterio dichiarato; verifica che
la shortlist contenga solo strategie READY_FOR_EDGE_VALIDATION nella
matrice; verifica che BREAKOUT_ACC/ORDER_BLOCK/TSI/ADX_RSI/SAR siano
tutte presenti in tier_a (richiesta esplicita dell'utente); verifica
che nessun file MQL5/Product-Platform/contracts sia stato toccato in
questa fase (nessuna modifica autorizzata)."""
import os
import subprocess
import sys

PHASE720_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE720_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE720_DIR)
import build_strategy_universe as universe_builder  # noqa: E402
import build_evaluation_matrix as matrix_builder  # noqa: E402
import build_shortlist as shortlist_builder  # noqa: E402
import build_edge_validation_protocol as protocol_builder  # noqa: E402
import build_recommended_first as recommended_builder  # noqa: E402
import build_evidence_reusability as reusability_builder  # noqa: E402
import build_edge_validation_gap_analysis as gap_builder  # noqa: E402
import build_inclusion_exclusion_summary as incl_excl_builder  # noqa: E402

ARTIFACTS = [
    ("strategy_universe_v1.json", universe_builder.build),
    ("evaluation_matrix_v1.json", matrix_builder.build),
    ("shortlist_v1.json", shortlist_builder.build),
    ("edge_validation_protocol_v1.json", protocol_builder.build),
    ("recommended_first_v1.json", recommended_builder.build),
    ("evidence_reusability_v1.json", reusability_builder.build),
    ("edge_validation_gap_analysis_v1.json", gap_builder.build),
    ("inclusion_exclusion_summary_v1.json", incl_excl_builder.build),
]

REQUIRED_TIER_A = {"BREAKOUT_ACC", "ORDER_BLOCK", "TSI", "ADX_RSI", "SAR"}
ALLOWED_CATEGORIES = {"READY_FOR_EDGE_VALIDATION", "PROMISING_BUT_NEEDS_INTEGRITY_WORK",
                      "INSUFFICIENT_EVIDENCE", "GENUINE_NO_EDGE_CANDIDATE", "DO_NOT_USE_YET"}


def verify():
    errors = []

    for fname, build_fn in ARTIFACTS:
        path = os.path.join(PHASE720_DIR, fname)
        if not os.path.exists(path):
            errors.append(f"{fname}: file mancante")
            continue
        saved = load_json(path)
        fresh = build_fn()
        if canonical_sha256(fresh) != canonical_sha256(saved["payload"]):
            errors.append(f"{fname}: ricostruzione indipendente differisce dal file salvato")

    universe = load_json(os.path.join(PHASE720_DIR, "strategy_universe_v1.json"))["payload"]
    if universe["n_strategies_total"] != 83:
        errors.append(f"universo: attese 83 strategie (intero census 7.11), trovate "
                      f"{universe['n_strategies_total']}")

    matrix = load_json(os.path.join(PHASE720_DIR, "evaluation_matrix_v1.json"))["payload"]
    if matrix["n_strategies_total_covered"] != 83:
        errors.append(f"matrice: copertura {matrix['n_strategies_total_covered']} != 83")
    if not matrix.get("pf_alone_never_used_to_classify"):
        errors.append("matrice: manca la dichiarazione 'pf_alone_never_used_to_classify'")

    tier_a = matrix["tier_a_deep_dive"]
    missing_required = REQUIRED_TIER_A - set(tier_a.keys())
    if missing_required:
        errors.append(f"tier_a: mancano strategie esplicitamente richieste dall'utente: {missing_required}")

    all_ids_seen = set(tier_a.keys())
    for row in matrix["tier_b_compact_rule_based"]:
        if row["category"] not in ALLOWED_CATEGORIES:
            errors.append(f"tier_b: categoria non ammessa per {row['canonical_strategy_id']}: "
                          f"{row['category']}")
        all_ids_seen.add(row["canonical_strategy_id"])
    for v in tier_a.values():
        if v["category"] not in ALLOWED_CATEGORIES:
            errors.append(f"tier_a: categoria non ammessa per {v['canonical_strategy_id']}: "
                          f"{v['category']}")
    all_ids_seen.update(matrix["tier_c_bulk"]["strategy_ids"])
    if len(all_ids_seen) != 83:
        errors.append(f"matrice: {len(all_ids_seen)} id unici coperti, attesi 83 (possibile "
                      "duplicato o strategia mancante)")

    # ogni strategia del census deve comparire esattamente una volta nella matrice.
    census_ids = {u["canonical_strategy_id"] for u in universe["universe"]}
    if all_ids_seen != census_ids:
        errors.append("matrice: l'insieme delle strategie coperte non coincide esattamente con "
                      "il census (mancanti o extra)")

    shortlist = load_json(os.path.join(PHASE720_DIR, "shortlist_v1.json"))["payload"]
    if not (3 <= shortlist["shortlist_size"] <= 5):
        if shortlist["shortlist_size"] < 3 and "why_fewer_than_requested_minimum" not in shortlist:
            errors.append("shortlist: dimensione fuori range 3-5 senza giustificazione esplicita")
    for sid in shortlist["strategies"]:
        if sid not in tier_a or tier_a[sid]["category"] != "READY_FOR_EDGE_VALIDATION":
            errors.append(f"shortlist: {sid} non e' classificata READY_FOR_EDGE_VALIDATION nella matrice")
    required_fields = ["perche_candidata", "evidenza_positiva_gia_esistente", "rischi_limiti",
                       "quali_dati_usare", "implementation_identity_canonica", "test_economico_corretto",
                       "quali_costi_includere", "quale_holdout_oos_usare",
                       "nuovo_run_mt5_o_artifact_bastano", "livello_visual_audit_possibile",
                       "minimum_viable_capital_da_verificare"]
    for sid, entry in shortlist["strategies"].items():
        missing = [f for f in required_fields if f not in entry]
        if missing:
            errors.append(f"shortlist[{sid}]: campi richiesti mancanti {missing}")

    recommended = load_json(os.path.join(PHASE720_DIR, "recommended_first_v1.json"))["payload"]
    if recommended["recommended_first"] not in shortlist["strategies"]:
        errors.append("recommended_first: la strategia raccomandata non e' nella shortlist")

    protocol = load_json(os.path.join(PHASE720_DIR, "edge_validation_protocol_v1.json"))["payload"]
    if protocol.get("not_executed_in_this_phase") is not True:
        errors.append("protocollo: manca la dichiarazione not_executed_in_this_phase")
    for forbidden in ("optimization", "sweep", "compounding", "portfolio"):
        if any(forbidden in s.lower() for s in protocol.get("explicit_exclusions_this_protocol_never_does", [])):
            continue
    exclusions_text = " ".join(protocol.get("explicit_exclusions_this_protocol_never_does", [])).lower()
    for forbidden in ("optimization", "sweep", "compounding", "portfolio"):
        if forbidden not in exclusions_text:
            errors.append(f"protocollo: esclusione attesa '{forbidden}' non dichiarata")

    # --- nessuna modifica a MQL5/Product-Platform/contracts in questa fase
    # (nessuna autorizzazione data - fase di sola classificazione). ---
    result = subprocess.run(["git", "status", "--porcelain", "--", "MQL5/", "Product-Platform/",
                            "contracts/"], cwd=ROOT, capture_output=True, text=True)
    modified = [l for l in result.stdout.strip().splitlines() if l.strip()]
    if modified:
        errors.append(f"file MQL5/Product-Platform/contracts risultano modificati in una fase di sola "
                      f"classificazione: {modified}")

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
