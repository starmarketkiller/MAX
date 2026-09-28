#!/usr/bin/env python3
"""Phase 7.27 - verificatore indipendente. Ri-deriva ogni artifact dai
builder; verifica che i parametri usati nei builder a valle coincidano
con la preregistrazione (nessun benchmark/orizzonte/metrica ridefinito
altrove); verifica che la decisione sia ammessa e MAI EDGE_VALIDATED;
verifica che Phase 7.9x-7.26 (tranne gli aggiornamenti autorizzati ai
registry di 7.26) e MQL5/Product-Platform/contracts non siano stati
modificati."""
import os
import subprocess
import sys

PHASE727_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE727_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE727_DIR)
import nxs_prereg_constants as C  # noqa: E402
import build_preregistration as prereg_builder  # noqa: E402
import build_benchmark_samples as samples_builder  # noqa: E402
import build_per_strategy_results as per_strat_builder  # noqa: E402
import build_regime_controlled_analysis as regime_builder  # noqa: E402
import build_cross_strategy_results as cross_builder  # noqa: E402
import build_multiple_testing_accounting as mtest_builder  # noqa: E402
import build_buy_dominance_decision_card as decision_builder  # noqa: E402

ARTIFACTS = [
    ("preregistration_v1.json", prereg_builder.build),
    ("benchmark_samples_v1.json", samples_builder.build),
    ("per_strategy_results_v1.json", per_strat_builder.build),
    ("regime_controlled_analysis_v1.json", regime_builder.build),
    ("cross_strategy_results_v1.json", cross_builder.build),
    ("multiple_testing_accounting_v1.json", mtest_builder.build),
    ("decision_card_v1.json", decision_builder.build),
]

# Phase 7.26 e' l'UNICA fase precedente autorizzata a essere modificata (registry viventi,
# item 10 del task) - ogni altra fase (incl. 7.9x-7.25) deve restare congelata.
FROZEN_PHASE_DIRS = [f"phase7_{n}" for n in
                    ["9c", "9d", "9e", "9f", "9g", "9h", "9i", "9j", "9k", "12", "13", "14", "15",
                     "16", "17", "18", "20", "21", "22", "23", "24", "25"]]


def verify():
    errors = []

    for fname, build_fn in ARTIFACTS:
        path = os.path.join(PHASE727_DIR, fname)
        if not os.path.exists(path):
            errors.append(f"{fname}: file mancante")
            continue
        saved = load_json(path)
        fresh = build_fn()
        if canonical_sha256(fresh) != canonical_sha256(saved["payload"]):
            errors.append(f"{fname}: ricostruzione indipendente differisce dal file salvato")

    # --- la preregistrazione salvata deve usare esattamente gli stessi valori delle
    # costanti importate da chi calcola i risultati (nessuna ridefinizione locale). ---
    prereg = load_json(os.path.join(PHASE727_DIR, "preregistration_v1.json"))["payload"]
    if prereg["horizons_d1_bars"] != C.HORIZONS_D1_BARS:
        errors.append("preregistration: horizons_d1_bars non coincide con nxs_prereg_constants")
    if prereg["primary_horizon_d1_bars"] != C.PRIMARY_HORIZON_D1_BARS:
        errors.append("preregistration: primary_horizon_d1_bars non coincide con nxs_prereg_constants")
    if not prereg["frozen_before_any_result_examined"]:
        errors.append("preregistration: frozen_before_any_result_examined non e' True")
    if not prereg["datasets_are_discovery_not_holdout"]:
        errors.append("preregistration: datasets_are_discovery_not_holdout non e' True - il task "
                      "chiede esplicitamente di non consumare un vero holdout se non necessario")

    # --- decisione ammessa, mai EDGE_VALIDATED. ---
    decision = load_json(os.path.join(PHASE727_DIR, "decision_card_v1.json"))["payload"]
    if decision["decision"] not in C.DECISION_ALLOWED:
        errors.append(f"decisione '{decision['decision']}' non ammessa")
    if "EDGE_VALIDATED" in decision["decision"].upper():
        errors.append("decisione contiene EDGE_VALIDATED - vietato esplicitamente dal task")

    # --- BUY_AND_HOLD non deve mai comparire come base di un confronto statistico
    # (design MACRO_CONTEXT_ONLY) in nessuna strategia. ---
    per_strat = load_json(os.path.join(PHASE727_DIR, "per_strategy_results_v1.json"))["payload"]
    for strat, d in per_strat.items():
        bh = d["per_benchmark_results"]["BUY_AND_HOLD_MACRO_CONTEXT"]
        if bh["design"] != "MACRO_CONTEXT_ONLY_NOT_A_STATISTICAL_COMPARISON":
            errors.append(f"{strat}: BUY_AND_HOLD non e' marcato come solo contesto macro")

    # --- multiple testing: la significativita' isolata (ORDER_BLOCK h1) e' dichiarata
    # non sopravvivere a Bonferroni - non deve essere usata per la decisione primaria. ---
    mtest = load_json(os.path.join(PHASE727_DIR, "multiple_testing_accounting_v1.json"))["payload"]
    if mtest["order_block_h1_significance_survives_bonferroni"] is not False:
        errors.append("multiple_testing_accounting: order_block_h1_significance_survives_bonferroni "
                      "deve essere False")

    # --- Phase 7.9x-7.25 restano congelate. ---
    for phase_dir in FROZEN_PHASE_DIRS:
        result = subprocess.run(["git", "diff", "--name-only", "--",
                                f"server/research_scripts/phase7/{phase_dir}"],
                               cwd=ROOT, capture_output=True, text=True)
        if result.stdout.strip():
            errors.append(f"{phase_dir} risulta modificato in una fase che deve lasciarlo "
                          f"congelato: {result.stdout.strip()}")

    # --- nessuna modifica a MQL5/Product-Platform/contracts. ---
    result = subprocess.run(["git", "status", "--porcelain", "--", "MQL5/", "Product-Platform/",
                            "contracts/"], cwd=ROOT, capture_output=True, text=True)
    modified = [l for l in result.stdout.strip().splitlines() if l.strip()]
    if modified:
        errors.append(f"file MQL5/Product-Platform/contracts risultano modificati: {modified}")

    # --- Phase 7.26 verifier/leakage devono restare puliti dopo gli aggiornamenti (item 10). ---
    phase726_dir = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_26")
    sys.path.insert(0, phase726_dir)
    import verify_phase_7_26  # noqa: E402
    p726_errors = verify_phase_7_26.verify()
    if p726_errors:
        errors.append(f"phase7_26 verifier non piu' pulito dopo gli aggiornamenti: {p726_errors}")

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
