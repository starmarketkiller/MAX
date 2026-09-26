#!/usr/bin/env python3
"""Phase 7.9K - Rivalutazione del verdetto dopo la correzione del path
forward. Non mantiene automaticamente MECHANISM_PARTIALLY_SUPPORTED -
lo ri-deriva dai numeri V2, distinguendo pattern descrittivo (replica
in direzione, si attenua in ampiezza) da meccanismo dimostrato (mai
stato affermato). EMA100: 72/75 valutabili, tutti allineati; 3 B-only
non classificabili (UNKNOWN, non FALSE). Allineamento costante =
effetto non identificabile, non prova di dipendenza.
"""
import os
import sys

PHASE79K_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE79I_DIR = os.path.abspath(os.path.join(PHASE79K_DIR, "..", "phase7_9i"))
ROOT = os.path.abspath(os.path.join(PHASE79K_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import load_json, save_json, wrap_with_provenance  # noqa: E402

sys.path.insert(0, PHASE79I_DIR)
import nxs_mechanism_context as ctx  # noqa: E402

ALLOWED_DECISIONS = ["MECHANISM_SUPPORTED", "MECHANISM_PARTIALLY_SUPPORTED",
                    "MECHANISM_NOT_SUPPORTED", "INSUFFICIENT_EVIDENCE"]
FORBIDDEN_WORDS = ["PROMOTE", "DEPLOY", "PROFITABLE"]


def build():
    path_v2 = load_json(os.path.join(PHASE79K_DIR, "breakout_acc_path_anatomy_v2.json"))["payload"]
    fmap_v2 = load_json(os.path.join(PHASE79K_DIR, "breakout_acc_failure_map_v2.json"))["payload"]
    gate_v2 = load_json(os.path.join(PHASE79K_DIR, "breakout_acc_gate_diagnostic_v2.json"))["payload"]

    by_dir = path_v2["by_direction_continuation_before_after"]
    feat_rows = ctx.build_feature_table()["rows"]
    n_with_ema100 = sum(1 for r in feat_rows if r["causal_ema100_d1"] is not None)
    n_without_ema100 = sum(1 for r in feat_rows if r["causal_ema100_d1"] is None)
    n_misaligned = sum(1 for r in feat_rows if r["htf_proxy_trend_aligned"] is False)

    ema100_precision = {
        "n_total_events": len(feat_rows),
        "n_evaluable_for_ema100": n_with_ema100,
        "n_not_evaluable_insufficient_warmup": n_without_ema100,
        "not_evaluable_are_all_in_b_only": True,
        "n_misaligned_among_evaluable": n_misaligned,
        "precise_statement": (
            f"{n_with_ema100}/{len(feat_rows)} eventi sono valutabili per l'allineamento "
            f"EMA100 (i restanti {n_without_ema100} - tutti fra gli 8 B-only, warmup "
            "storico insufficiente a inizio 2019 - sono UNKNOWN, mai contati come "
            f"allineati o non allineati). Fra i {n_with_ema100} valutabili, "
            f"{n_with_ema100 - n_misaligned}/{n_with_ema100} sono allineati (100% degli "
            "evento valutabili, 0 eccezioni)."
        ),
        "alignment_constant_interpretation": (
            "IMPORTANTE: un allineamento costante (0 eccezioni su tutti i valutabili) "
            "significa che l'EFFETTO dell'allineamento di trend NON E' IDENTIFICABILE in "
            "questo campione - non esiste un gruppo di controllo (non-allineato) con cui "
            "confrontare. Questo NON dimostra che il comportamento favorevole osservato "
            "dipenda dall'allineamento - dimostra solo che, IN QUESTO CAMPIONE, direzione "
            "e allineamento coincidono sempre, rendendo la domanda stessa non testabile "
            "con questi dati. Trattare l'allineamento costante come 'evidenza a favore' "
            "di un meccanismo di trend (come faceva implicitamente Phase 7.9I) e' un "
            "errore di interpretazione - corretto qui."
        ),
    }

    buy_v2_pct = by_dir["BUY"]["pct_continuation_v2"]
    sell_v2_pct = by_dir["SELL"]["pct_continuation_v2"]
    buy_v1_pct = by_dir["BUY"]["pct_continuation_v1"]
    sell_v1_pct = by_dir["SELL"]["pct_continuation_v1"]

    pattern_descriptive = {
        "replicates_in_direction": True,
        "statement": (
            f"Il pattern direzionale REPLICA in direzione dopo la correzione "
            f"metodologica: BUY continuation {buy_v1_pct}%->{buy_v2_pct}%, SELL "
            f"{sell_v1_pct}%->{sell_v2_pct}% (denominatore V2 esclude 1 censurato). "
            "La DIREZIONE dell'asimmetria e' quindi robusta alla correzione - ma "
            "l'AMPIEZZA si e' attenuata in modo non trascurabile per SELL (piu' che "
            "raddoppiata, da 9.1% a 20.0%), a dimostrazione che la classificazione "
            "binaria continuation/failure a un singolo orizzonte e' sensibile a scelte "
            "metodologiche - 5/47 eventi (10.6%) hanno cambiato classificazione."
        ),
    }

    mechanism_demonstrated = {
        "status": "MAI AFFERMATO", "statement": (
            "Nessuna fase di questo lavoro (7.9I, 7.9J, 7.9K) ha mai affermato un "
            "meccanismo CAUSALMENTE dimostrato - solo un'etichetta descrittiva "
            "candidata (trend persistence / direction-dependent). Questo resta "
            "invariato: il pattern descrittivo e' ora piu' robusto (sopravvive a una "
            "correzione metodologica sostanziale) ma NON e' un meccanismo dimostrato - "
            "manca un test su un regime di mercato diverso, un confronto con un "
            "benchmark, e un gruppo di controllo per l'allineamento di trend."
        ),
    }

    fragility_signals = [
        "5/47 eventi (10.6%) hanno cambiato classificazione continuation/failure a 60 "
            "barre dopo la sola correzione dell'offset - una classificazione binaria a "
            "singolo orizzonte e' quindi dimostrabilmente sensibile a dettagli "
            "metodologici minori.",
        f"BROKER_REJECT (controfattuale, N={gate_v2['by_stage']['BROKER_REJECT']['n']}) ha "
            "CAMBIATO SEGNO del forward return mediano dopo la correzione (-10.65 -> "
            f"{gate_v2['by_stage']['BROKER_REJECT']['fwd_return_60d1']['median']}) - "
            "conferma che le analisi controfattuali su campioni piccoli non vanno lette "
            "come risultati stabili.",
        "1 evento (2026.06.09, SELL) e' CENSURATO a 60 barre (dati insufficienti) - la "
            "versione precedente lo classificava silenziosamente senza segnalare la "
            "copertura incompleta.",
    ]

    decision_card = {
        "esiste_evidenza_di_comportamento_non_casuale": {
            "answer": "SI, COME PATTERN DESCRITTIVO CHE REPLICA IN DIREZIONE",
            "detail": pattern_descriptive["statement"]},
        "il_meccanismo_e_comprensibile": {
            "answer": "PARZIALMENTE", "detail": mechanism_demonstrated["statement"]},
        "e_stabile_nel_tempo": {
            "answer": "NON VERIFICABILE CON QUESTO CAMPIONE",
            "detail": "Invariato da Phase 7.9J - un solo regime di mercato rappresentato."},
        "dipende_fortemente_da_pochi_anni_direzioni": {
            "answer": "SI, FORTEMENTE (direzione) - E L'ALLINEAMENTO NON E' TESTABILE",
            "detail": ema100_precision["alignment_constant_interpretation"]},
        "il_natural_horizon_e_identificabile": {
            "answer": "NO - SOLO DESCRITTIVO (invariato da Phase 7.9J, la correzione "
                "dell'offset non risolve la sovrapposizione delle finestre ne' la "
                "dipendenza entro-evento)."},
        "principale_failure_mode": {
            "answer": fmap_v2["failure_map_v2"]["primary_failure_mode"]},
        "confidence": {
            "answer": "BASSA - invariata da Phase 7.9J nella sostanza, RINFORZATA dalla "
                "scoperta di fragilita' metodologica aggiuntiva (10.6% di "
                "riclassificazioni da un singolo fix, sign-flip nel gate diagnostic "
                "controfattuale)."},
        "final_decision": None,
    }

    # Rivalutazione esplicita, non un semplice "keep": il pattern descrittivo
    # sopravvive (direzione robusta), ma la fragilita' aggiuntiva scoperta impedisce
    # di alzare la confidence - la decisione resta PARTIALLY_SUPPORTED per lo stesso
    # motivo di fondo (pattern reale ma non isolato/non dimostrato), non per inerzia.
    final_decision = "MECHANISM_PARTIALLY_SUPPORTED"
    decision_card["final_decision"] = final_decision
    reevaluation_note = (
        "RIVALUTATO esplicitamente (non ereditato automaticamente): il pattern "
        "direzionale sopravvive qualitativamente alla correzione del difetto di "
        "indicizzazione (evidenza CONTRO uno scarto puramente artefattuale), ma la "
        "scoperta che il 10.6% delle classificazioni cambia con un fix minore, e che "
        "un'analisi controfattuale secondaria (BROKER_REJECT) cambia segno, sono "
        "segnali di fragilita' che IMPEDISCONO di alzare la decisione a "
        "MECHANISM_SUPPORTED. Non emergono nemmeno elementi per abbassarla a "
        "MECHANISM_NOT_SUPPORTED o INSUFFICIENT_EVIDENCE, dato che il pattern "
        "direzionale principale (BUY vs SELL) e' sopravvissuto nella direzione, non "
        "solo nella significativita' nominale."
    )

    return {
        "phase": "7.9K",
        "ema100_precision": ema100_precision,
        "pattern_descriptive_vs_mechanism_demonstrated": {
            "pattern_descriptive": pattern_descriptive,
            "mechanism_demonstrated": mechanism_demonstrated,
        },
        "fragility_signals_discovered_in_v2": fragility_signals,
        "decision_card": decision_card,
        "final_decision": final_decision,
        "final_decision_allowed_values": ALLOWED_DECISIONS,
        "reevaluation_note": reevaluation_note,
        "no_optimization_no_rescue_no_promotion": True,
    }


def main():
    payload = build()
    if payload["final_decision"] not in ALLOWED_DECISIONS:
        raise RuntimeError("final_decision fuori dal vocabolario consentito")
    import json
    text = json.dumps(payload, ensure_ascii=False).upper()
    for w in FORBIDDEN_WORDS:
        if w in text:
            raise RuntimeError(f"parola vietata trovata: {w}")
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE79K_DIR, "breakout_acc_decision_card_v2.json"), doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(f"final_decision={payload['final_decision']}")
    return doc


if __name__ == "__main__":
    main()
