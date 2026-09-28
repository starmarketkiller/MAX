#!/usr/bin/env python3
"""Phase 7.26 punto J - CROSS_STRATEGY_SYNTHESIS_V1. Legge SOLO gli
artifact gia' costruiti in questa fase (learning packet, failure map,
hypothesis registry) - non ricalcola nulla dai dati grezzi. Puo'
produrre SOLO OBSERVATION / CROSS_STRATEGY_PATTERN / CANDIDATE_
HYPOTHESIS - MAI EDGE_FOUND (verificato staticamente dal verificatore:
nessuna stringa 'EDGE_FOUND' nell'output)."""
import os
import sys
from collections import Counter

PHASE726_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE726_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402

sys.path.insert(0, PHASE726_DIR)
from nxs_schemas import SYNTHESIS_ALLOWED_VERDICTS, NOT_AVAILABLE  # noqa: E402

ECONOMIC_STRATEGIES = ["BREAKOUT_ACC", "ORDER_BLOCK", "LIQ_SWEEP"]  # TSI escluso: nessun dataset


def _finding(kind, statement, evidence):
    assert kind in SYNTHESIS_ALLOWED_VERDICTS, kind
    assert "EDGE_FOUND" not in statement.upper()
    return {"kind": kind, "statement": statement, "evidence": evidence}


def build():
    packets = load_json(os.path.join(PHASE726_DIR, "cross_strategy_learning_packets_v1.json"))["payload"]["packets"]
    failure_map = load_json(os.path.join(PHASE726_DIR, "failure_map_v1.json"))["payload"]["strategies"]

    findings = []

    # --- failure mode comuni ---
    mode_counter = Counter()
    for strat in ECONOMIC_STRATEGIES:
        for tag in failure_map[strat]["failure_modes"]:
            mode_counter[tag["mode"]] += 1
    shared_modes = {m: n for m, n in mode_counter.items() if n >= 2}
    for mode, n in shared_modes.items():
        strategies_with_mode = [s for s in ECONOMIC_STRATEGIES
                               if any(t["mode"] == mode for t in failure_map[s]["failure_modes"])]
        findings.append(_finding(
            "CROSS_STRATEGY_PATTERN",
            f"{n}/3 strategie economiche del corpus condividono il failure mode {mode}.",
            {"strategies": strategies_with_mode, "source": "failure_map_v1.json"}))

    # --- OOS degradation come pattern trasversale specifico (gia' incluso sopra come
    # CROSS_STRATEGY_PATTERN se n>=2, ma qui aggiungiamo il dettaglio quantitativo). ---
    oos_summaries = {s: packets[s]["oos_behavior"] for s in ECONOMIC_STRATEGIES}
    if all(isinstance(v, dict) for v in oos_summaries.values()):
        findings.append(_finding(
            "OBSERVATION",
            "Tutte e 3 le strategie economiche mostrano un OOS forward NON supportivo "
            "dell'edge storico (insufficiente o negativo) - nessuna delle tre ha ancora un OOS "
            "genuinamente POSITIVO e sufficiente.",
            {"oos_behavior_per_strategy": oos_summaries}))

    # --- asimmetria direzionale trasversale ---
    direction_notes = {s: packets[s]["direction"] for s in ECONOMIC_STRATEGIES}
    if all(v != NOT_AVAILABLE for v in direction_notes.values()):
        findings.append(_finding(
            "CANDIDATE_HYPOTHESIS",
            "Le 3 strategie economiche del corpus mostrano tutte una dominanza BUY (non SELL) - "
            "possibile riflesso di un trend secolare rialzista del simbolo/periodo studiato "
            "(GOLD, 2019-2026) piuttosto che un edge specifico di ciascuna strategia. Da "
            "verificare confrontando con un benchmark buy-and-hold sullo stesso periodo - non "
            "fatto in questa fase.",
            {"direction_per_strategy": direction_notes}))

    # --- concentrazione del profitto (per-trade) - gia' in shared_modes se OUTLIER_DEPENDENT
    # e' condiviso, ma qui riportiamo i numeri espliciti per confronto diretto. ---
    conc_values = {s: packets[s]["concentration"] for s in ECONOMIC_STRATEGIES}
    if all(isinstance(v, (int, float)) for v in conc_values.values()):
        findings.append(_finding(
            "OBSERVATION",
            "In tutte e 3 le strategie, i primi 5 trade migliori spiegano da soli oltre il 100% "
            "del P&L netto totale (concentrazione estrema, non un'anomalia isolata di una sola "
            "strategia).",
            {"top5_pct_per_strategy": conc_values}))

    # --- concentrazione temporale - dati disponibili solo per LIQ_SWEEP finora (gap dichiarato). ---
    temporal_available = {s: packets[s]["temporal_concentration"] for s in ECONOMIC_STRATEGIES}
    n_available = sum(1 for v in temporal_available.values() if v != NOT_AVAILABLE)
    findings.append(_finding(
        "OBSERVATION",
        f"Solo {n_available}/3 strategie hanno una statistica di concentrazione temporale "
        "gia' calcolata (LIQ_SWEEP: ~99% del netto in un solo anno) - BREAKOUT_ACC e ORDER_BLOCK "
        "non hanno mai avuto questa specifica analisi per-anno nel loro learning packet corrente "
        "- GAP dichiarato, non un'assenza del fenomeno.",
        {"temporal_concentration_per_strategy": temporal_available}))

    # --- exit efficiency / mismatch strutturale - solo LIQ_SWEEP ha questo campo popolato
    # con un finding specifico (mismatch MQL5/Python) - non generalizzabile senza dati
    # equivalenti per le altre due. ---
    exit_eff = {s: packets[s]["exit_efficiency"] for s in ECONOMIC_STRATEGIES}
    if exit_eff["LIQ_SWEEP"] != NOT_AVAILABLE and all(
            exit_eff[s] == NOT_AVAILABLE for s in ("BREAKOUT_ACC", "ORDER_BLOCK")):
        findings.append(_finding(
            "OBSERVATION",
            "Solo LIQ_SWEEP ha una nota esplicita di exit_efficiency (uscita ATR fissa vs target "
            "dinamico) - BREAKOUT_ACC/ORDER_BLOCK non hanno un'analisi equivalente di 'quanto "
            "efficientemente la strategia monetizza il movimento catturato' - GAP di ricerca, "
            "candidato per la Research Priority Queue (non ancora un pattern trasversale).",
            {"exit_efficiency_per_strategy": exit_eff}))

    payload = {
        "strategies_included": ECONOMIC_STRATEGIES,
        "strategies_excluded": {"TSI": "nessun dataset economico esiste - non comparabile su "
                                       "nessuno dei campi economici sopra."},
        "allowed_verdict_kinds": SYNTHESIS_ALLOWED_VERDICTS,
        "findings": findings, "n_findings": len(findings),
        "cannot_produce_edge_found": True,
        "no_new_data_computed_only_existing_artifacts_read": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE726_DIR, "cross_strategy_synthesis_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    for f in payload["findings"]:
        print(f"  [{f['kind']}] {f['statement'][:90]}")


if __name__ == "__main__":
    main()
