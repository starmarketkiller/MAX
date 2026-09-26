#!/usr/bin/env python3
"""Phase 7.9I - Executive Summary (max 10 righe) + Decision Card finale.
Decisione ristretta a MECHANISM_SUPPORTED / MECHANISM_PARTIALLY_SUPPORTED
/ MECHANISM_NOT_SUPPORTED / INSUFFICIENT_EVIDENCE. Mai PROMOTE/DEPLOY/
PROFITABLE. Se il meccanismo e' sufficientemente supportato, UNA sola
nuova ipotesi falsificabile, non implementata.
"""
import os
import sys

PHASE79I_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE79I_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import load_json, save_json, wrap_with_provenance  # noqa: E402

ALLOWED_DECISIONS = ["MECHANISM_SUPPORTED", "MECHANISM_PARTIALLY_SUPPORTED",
                    "MECHANISM_NOT_SUPPORTED", "INSUFFICIENT_EVIDENCE"]
FORBIDDEN_WORDS = ["PROMOTE", "DEPLOY", "PROFITABLE"]


def build():
    mech = load_json(os.path.join(PHASE79I_DIR, "breakout_acc_mechanism_discovery_v1.json"))["payload"]
    horizon = load_json(os.path.join(PHASE79I_DIR, "breakout_acc_natural_horizon_v1.json"))["payload"]
    fmap = load_json(os.path.join(PHASE79I_DIR, "breakout_acc_failure_map_and_robustness_v1.json"))["payload"]
    path = load_json(os.path.join(PHASE79I_DIR, "breakout_acc_path_anatomy_v1.json"))["payload"]

    PHASE79J_DIR = os.path.abspath(os.path.join(PHASE79I_DIR, "..", "phase7_9j"))
    horizon_reconciliation = load_json(os.path.join(
        PHASE79J_DIR, "breakout_acc_natural_horizon_reconciliation_v1.json"))["payload"]
    alignment_table = load_json(os.path.join(
        PHASE79J_DIR, "breakout_acc_direction_alignment_outcome_v1.json"))["payload"]

    robustness = fmap["robustness_minimum_checks"]
    by_dir = path["aggregate"]["by_direction"]

    executive_summary_lines = [
        "BREAKOUT_ACC (D1, GOLD 2019-2026, N=47 OPENED) mostra un pattern favorevole "
            "convergente ma FORTEMENTE direzione-dipendente, non un breakout simmetrico.",
        f"BUY: {by_dir['BUY']['n_continuation']}/{by_dir['BUY']['n']} continuation a 60gg "
            f"D1 (66.7%); SELL: {by_dir['SELL']['n_continuation']}/{by_dir['SELL']['n']} (9.1%).",
        "100% di TUTTI i 75 eventi (non solo OPENED) sono trend-aligned (EMA100/EMA20, "
            "corretti per causalita' in Phase 7.9J) - direzione e allineamento sono "
            "PERFETTAMENTE CONFUSI, non distinguibili con questo campione.",
        "Natural Horizon (Phase 7.9J): il pattern di crescita resta solo DESCRITTIVO - "
            "finestre sovrapposte e dipendenza entro-evento invalidano il CI originale.",
        "CONTINUATION_SYMMETRIC_BREAKOUT e' contraddetta dalla scomposizione BUY/SELL; "
            "TREND_PERSISTENCE resta un'etichetta descrittiva candidata, non isolata.",
        "Gli 8 eventi B-only non alterano le conclusioni primarie (Population B esclusa "
            "per costruzione) - path controfattuale ricostruito, delta non trascurabile.",
        "BLOCKED (cooldown, N=11 controfattuale) mostra un esito mediano MIGLIORE di "
            "OPENED - possibile (non confermato) filtraggio di eventi anche buoni.",
        "Confidence BASSA: N piccolo, un solo regime di mercato, confondimento "
            "direzione/trend totale, CI del Natural Horizon non validi statisticamente.",
        "Nessuna optimization eseguita; nessuna soglia scelta guardando i risultati.",
        "Decisione: MECHANISM_PARTIALLY_SUPPORTED (vedi Decision Card).",
    ]
    if len(executive_summary_lines) > 10:
        raise RuntimeError("Executive summary supera le 10 righe consentite")

    decision_card = {
        "esiste_evidenza_di_comportamento_non_casuale": {
            "answer": "SI, COME PATTERN DESCRITTIVO", "detail": "Asimmetria BUY/SELL di "
                "ampiezza sostanziale, osservata su piu' statistiche calcolate sugli "
                "STESSI eventi (non conferme statisticamente indipendenti - nessun test "
                "d'ipotesi formale eseguito). L'effect size e' ampio, ma 'non spiegabile "
                "da rumore' sarebbe un'affermazione piu' forte di quanto i dati "
                "permettano di sostenere senza un test formale."},
        "il_meccanismo_e_comprensibile": {
            "answer": "PARZIALMENTE", "detail": "La spiegazione piu' parsimoniosa "
                "(allineamento con un trend gia' in corso) e' comprensibile come "
                "etichetta descrittiva, ma Phase 7.9J ha verificato che direzione e "
                "allineamento di trend sono PERFETTAMENTE CONFUSI su tutti i 75 eventi "
                "(0 eccezioni) - non e' possibile distinguere osservazionalmente "
                "'allineamento di trend' da 'essere BUY in questo periodo'."},
        "e_stabile_nel_tempo": {
            "answer": "NON VERIFICABILE CON QUESTO CAMPIONE", "detail": "Tutto il periodo "
                "2019-2026 e' stato un mercato GOLD prevalentemente rialzista - nessun "
                "regime bear/range rappresentato per testare la stabilita' del pattern in "
                "condizioni diverse."},
        "dipende_fortemente_da_pochi_anni_direzioni": {
            "answer": "SI, FORTEMENTE (direzione, e totalmente dal trend-alignment)", "detail":
                "La dipendenza dalla direzione e' schiacciante (BUY 66.7% vs SELL 9.1% "
                f"continuation) ed e' COLLINEARE al 100% con l'allineamento di trend "
                f"(Phase 7.9J: {alignment_table['n_misaligned_ema100_regime_all75']} eventi "
                "non-allineati su 75, su entrambi i proxy EMA100/EMA20). La "
                f"concentrazione per anno e' moderata (max "
                f"{robustness['concentration_by_year']['max_single_year_share_pct']}% in "
                "un singolo anno), non estrema."},
        "il_natural_horizon_e_identificabile": {
            "answer": "NO - SOLO DESCRITTIVO", "detail": horizon_reconciliation["revised_finding"]},
        "principale_failure_mode": {
            "answer": fmap["deliverable_8_failure_map"]["primary_failure_mode"]},
        "confidence": {
            "answer": "BASSA (declassata da 'bassa-moderata' in Phase 7.9J): le tre "
                "statistiche originariamente presentate come convergenti condividono gli "
                "stessi eventi, il proxy di trend e' totalmente confuso con la direzione, "
                "e il Natural Horizon non e' statisticamente validato. Il pattern BUY/SELL "
                "resta il singolo elemento di evidenza piu' solido (effect size ampio, "
                "verificato su dati causalmente corretti), ma non e' isolabile come "
                "meccanismo a se stante da questo campione."},
        "final_decision": None,
    }

    final_decision = "MECHANISM_PARTIALLY_SUPPORTED"
    decision_card["final_decision"] = final_decision

    next_hypothesis = None
    if final_decision in ("MECHANISM_SUPPORTED", "MECHANISM_PARTIALLY_SUPPORTED"):
        next_hypothesis = {
            "hypothesis": "TREND_ALIGNMENT_CONDITIONAL_EDGE",
            "statement": "Il comportamento favorevole di BREAKOUT_ACC e' condizionato "
                "dall'allineamento con il trend di lungo periodo (proxy EMA100 causale), "
                "non dalla geometria del breakout in se'. Se falsa, segnali BUY in un "
                "regime NON rialzista (o segnali SELL in un regime NON ribassista) "
                "dovrebbero mostrare continuation/MFE/MAE paragonabili ai segnali "
                "attualmente trend-allineati; se vera, dovrebbero mostrare un "
                "comportamento sfavorevole simile a quello osservato qui per i SELL.",
            "falsification_test_not_implemented": "Richiederebbe un campione con eventi "
                "BREAKOUT_ACC generati durante un regime di mercato diverso (bear o range "
                "prolungato) su GOLD o un altro strumento - NON implementato, NON "
                "eseguito, proposto solo come prossima domanda di ricerca.",
            "explicitly_not_implemented": True,
        }

    return {
        "phase": "7.9I", "dataset_frozen_input": "breakout_acc_intended_d1_v1_dataset.json "
            "(Phase 7.9H, invariato)",
        "lineage_note": "Rivisto in Phase 7.9J dopo audit metodologico: (1) bug di "
            "causalita' temporale in causal_ema() confermato e corretto (impatto "
            "misurato: nullo sulla conclusione booleana di trend-alignment); (2) "
            "confermato che direzione e allineamento di trend sono perfettamente confusi "
            "su tutti i 75 eventi, non solo i 47 OPENED; (3) Natural Horizon declassato a "
            "puramente descrittivo (finestre sovrapposte, dipendenza entro-evento); (4) "
            "linguaggio di 'analisi indipendenti'/'non spiegabile da rumore' corretto. La "
            "decisione finale (MECHANISM_PARTIALLY_SUPPORTED) NON cambia, ma la sua "
            "giustificazione e il livello di confidence sono stati resi piu' conservativi "
            "e precisi. Originale preservato in "
            "phase7_9j/raw_data_pre_fix/breakout_acc_executive_summary_decision_card_v1_"
            "ORIGINAL_pre_temporal_fix.json.",
        "no_optimization_no_rescue_no_promotion": True,
        "executive_summary_max_10_lines": executive_summary_lines,
        "decision_card": decision_card,
        "final_decision": final_decision,
        "final_decision_allowed_values": ALLOWED_DECISIONS,
        "next_hypothesis_not_implemented": next_hypothesis,
    }


def _assert_no_forbidden_words(payload):
    import json
    text = json.dumps(payload, ensure_ascii=False).upper()
    for w in FORBIDDEN_WORDS:
        if w in text:
            raise RuntimeError(f"Parola vietata trovata nell'output: {w}")


def main():
    payload = build()
    if payload["final_decision"] not in ALLOWED_DECISIONS:
        raise RuntimeError("final_decision fuori dal vocabolario consentito")
    _assert_no_forbidden_words(payload)
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE79I_DIR, "breakout_acc_executive_summary_decision_card_v1.json"), doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(f"final_decision={payload['final_decision']}")
    for line in payload["executive_summary_max_10_lines"]:
        print(" -", line)
    return doc


if __name__ == "__main__":
    main()
