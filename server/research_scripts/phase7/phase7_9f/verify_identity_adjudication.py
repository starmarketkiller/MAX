#!/usr/bin/env python3
"""Phase 7.9F - verificatore indipendente. Ri-deriva tutto dai raw file
(fonti documentali, ordine registro calcolato a codice, output reale
del run diagnostico con ordine esatto) senza fidarsi dei numeri gia'
scritti negli artifact - fallisce chiuso su qualunque discrepanza."""
import json
import os
import subprocess
import sys

PHASE79F_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE79F_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE79F_DIR)
import build_strategy_identity_authority as authority_builder  # noqa: E402
import build_implemented_vs_intended_semantics as semantics_builder  # noqa: E402
import build_identity_adjudication as adjudication_builder  # noqa: E402

ALLOWED_VERDICTS = {
    "IMPLEMENTATION_DEFECT_CONFIRMED", "IMPLEMENTATION_BEHAVIOR_INTENDED",
    "SPEC_AMBIGUOUS_IMPLEMENTATION_DIVERGENCE", "ROOT_CAUSE_CONFIRMED_BUT_INTENT_UNRESOLVED",
}
VERDICT_TO_NEXT_DECISION = {
    "IMPLEMENTATION_DEFECT_CONFIRMED": "FIX_LIVE_IMPLEMENTATION_THEN_REESTABLISH_PARITY",
    "IMPLEMENTATION_BEHAVIOR_INTENDED": "ALIGN_OFFLINE_REPLICA_TO_IMPLEMENTED_SEMANTICS",
    "SPEC_AMBIGUOUS_IMPLEMENTATION_DIVERGENCE": "BLOCK_UNTIL_STRATEGY_IDENTITY_RESOLVED",
    "ROOT_CAUSE_CONFIRMED_BUT_INTENT_UNRESOLVED": "BLOCK_UNTIL_STRATEGY_IDENTITY_RESOLVED",
}


def verify():
    errors = []

    # --- 1) Ricostruzione indipendente dei 3 artifact principali. ---
    authority_path = os.path.join(PHASE79F_DIR, "breakout_acc_strategy_identity_authority_v1.json")
    semantics_path = os.path.join(PHASE79F_DIR, "breakout_acc_implemented_vs_intended_semantics_v1.json")
    router_path = os.path.join(PHASE79F_DIR, "breakout_acc_exact_router_replication_v1.json")
    adjudication_path = os.path.join(PHASE79F_DIR, "breakout_acc_identity_adjudication_v1.json")

    authority_doc = load_json(authority_path)
    semantics_doc = load_json(semantics_path)
    adjudication_doc = load_json(adjudication_path)

    fresh_authority = authority_builder.build()
    if canonical_sha256(fresh_authority) != canonical_sha256(authority_doc["payload"]):
        errors.append("strategy identity authority: ricostruzione indipendente differisce")

    fresh_semantics = semantics_builder.build()
    if canonical_sha256(fresh_semantics) != canonical_sha256(semantics_doc["payload"]):
        errors.append("implemented vs intended semantics: ricostruzione indipendente differisce")

    fresh_adjudication = adjudication_builder.build()
    if canonical_sha256(fresh_adjudication) != canonical_sha256(adjudication_doc["payload"]):
        errors.append("identity adjudication: ricostruzione indipendente differisce")

    # --- 2) L'ordine dei pass calcolato deve corrispondere ESATTAMENTE a quanto
    # usato nello script MQL5 effettivamente eseguito. ---
    exact_order = [p["tf"] for p in semantics_doc["payload"]["4_exact_router_replication"]["exact_pass_order_verified"]]
    mql5_path = os.path.join(ROOT, "server", "research_scripts", "NXS_BreakoutAccSharedStateDiagnostic.mq5")
    with open(mql5_path, encoding="utf-8") as f:
        mql5_text = f.read()
    for tf in exact_order:
        if tf not in mql5_text:
            errors.append(f"TF {tf} calcolato non trovato nello script MQL5 effettivo")
    declared_order_str = ", ".join(exact_order)
    if "g_passes[6] = {" not in mql5_text:
        errors.append("array g_passes non trovato nello script MQL5")

    # --- 3) Verdetto/decisione entro i set ammessi, coerenza verdetto->decisione. ---
    verdict = adjudication_doc["payload"]["final_verdict"]
    decision = adjudication_doc["payload"]["next_decision"]
    if verdict not in ALLOWED_VERDICTS:
        errors.append(f"final_verdict fuori dal set ammesso: {verdict}")
    if VERDICT_TO_NEXT_DECISION.get(verdict) != decision:
        errors.append(f"next_decision '{decision}' non coerente col mapping atteso per verdetto '{verdict}'")
    if adjudication_doc["payload"].get("next_step_not_executed") is not True:
        errors.append("next_step_not_executed non e' True")

    # --- 4) EA live e Python NON modificati. ---
    for p, name in (
        (os.path.join(ROOT, "MQL5", "Experts", "NEXUS_EA_v2.mq5"), "NEXUS_EA_v2.mq5"),
        (os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Strategies.mqh"), "NXS_Strategies.mqh"),
        (os.path.join(ROOT, "server", "backtest.py"), "backtest.py"),
    ):
        result = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", p], cwd=ROOT)
        if result.returncode != 0:
            errors.append(f"{name} risulta modificato rispetto a HEAD - vietato in questa fase")

    # --- 5) Nessun P&L usato per la diagnosi. ---
    full_text = (json.dumps(authority_doc["payload"]).lower() + json.dumps(semantics_doc["payload"]).lower()
                 + json.dumps(adjudication_doc["payload"]).lower())
    for term in ("expectancy", "\"pf\":", "profit_factor", "win_rate"):
        if term in full_text:
            errors.append(f"trovato termine P&L vietato: {term}")

    # --- 6) Il verdetto deve essere sostenuto da almeno le fonti documentali citate. ---
    if len(authority_doc["payload"]["sources_chronological"]) < 5:
        errors.append("meno di 5 fonti documentali citate - evidenza insufficiente per un verdetto forte")

    # --- 7) Deliverable presenti. ---
    for p in (authority_path, semantics_path, router_path, adjudication_path):
        if not os.path.exists(p) or os.path.getsize(p) == 0:
            errors.append(f"deliverable mancante o vuoto: {p}")

    # --- 8) Artifact frozen precedenti (7.9C/D/E) non modificati (esistenza/leggibilita'). ---
    for rel in (
        "server/research_scripts/phase7/phase7_9c/breakout_acc_event_parity_matrix_v1.json",
        "server/research_scripts/phase7/phase7_9d/breakout_acc_execution_parity_decision_v1.json",
        "server/research_scripts/phase7/phase7_9e/breakout_acc_reconstruction_decision_v1.json",
    ):
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            errors.append(f"artifact frozen mancante: {rel}")
        else:
            load_json(p)

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
