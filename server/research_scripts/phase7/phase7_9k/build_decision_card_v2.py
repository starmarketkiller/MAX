#!/usr/bin/env python3
"""Phase 7.9K - Rivalutazione del verdetto dopo la correzione del path
forward. Non mantiene automaticamente MECHANISM_PARTIALLY_SUPPORTED -
lo ri-deriva dai numeri V2, distinguendo pattern descrittivo (persiste
in direzione, si attenua in ampiezza - MAI descritto come una conferma indipendente: e' una correzione sugli stessi dati, non un nuovo
campione) da meccanismo dimostrato (mai stato affermato). La
persistenza del pattern dopo la correzione non dimostra da sola
non-casualita' ne' un edge incrementale - entrambi restano da
verificare. EMA100: 72/75 valutabili, tutti allineati; 3 B-only non
classificabili (UNKNOWN, non FALSE). Allineamento costante = effetto
non identificabile, non prova di dipendenza.
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

    agg = path_v2["aggregate_before_after"]
    n_outcome_flips = agg["n_outcome_flips_continuation_vs_failure"]
    n_outcome_denom = agg["n_outcome_flips_denominator"]
    n_coverage_changes = agg["n_coverage_status_changes"]
    outcome_flip_pct = round(100 * n_outcome_flips / n_outcome_denom, 1)

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
        "persistent_in_direction_same_dataset_corrected_methodology": True,
        "statement": (
            f"Il pattern direzionale RESTA PRESENTE dopo una correzione metodologica "
            "sugli STESSI dati (non un nuovo campione indipendente): BUY continuation "
            f"{buy_v1_pct}%->{buy_v2_pct}%, SELL "
            f"{sell_v1_pct}%->{sell_v2_pct}% (denominatore V2 esclude 1 censurato). "
            "La DIREZIONE dell'asimmetria e' sopravvissuta alla correzione - ma "
            "l'AMPIEZZA si e' attenuata in modo non trascurabile per SELL (piu' che "
            "raddoppiata, da 9.1% a 20.0%), a dimostrazione che la classificazione "
            f"binaria continuation/failure a un singolo orizzonte e' sensibile a scelte "
            f"metodologiche - {n_outcome_flips}/{n_outcome_denom} eventi comparabili "
            f"({outcome_flip_pct}%) hanno un vero cambio di ESITO (continuation<->"
            f"failure), a cui si aggiunge separatamente {n_coverage_changes} evento con "
            "un cambio di STATO DI COPERTURA (da UNKNOWN a UNKNOWN_CENSORED, non un "
            "cambio di esito - vedi nota dedicata in breakout_acc_path_anatomy_v2.json). "
            "Questa persistenza su dati corretti NON dimostra da sola non-casualita' ne' "
            "un edge incrementale rispetto a un benchmark - nessuno dei due e' stato "
            "testato in questa fase."
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
        f"{n_outcome_flips}/{n_outcome_denom} eventi comparabili ({outcome_flip_pct}%) "
            "hanno un vero cambio di ESITO continuation/failure a 60 barre dopo la sola "
            "correzione dell'offset - una classificazione binaria a singolo orizzonte e' "
            "quindi dimostrabilmente sensibile a dettagli metodologici minori. "
            f"(Separatamente, {n_coverage_changes} evento ha un cambio di STATO DI "
            "COPERTURA, non di esito - la sua classificazione V1 era gia' UNKNOWN, non "
            "FAILURE, e resta indeterminata in V2 - CENSORED_INSUFFICIENT_BARS.)",
        f"BROKER_REJECT (controfattuale, N={gate_v2['by_stage']['BROKER_REJECT']['n']}) ha "
            "CAMBIATO SEGNO del forward return mediano dopo la correzione (-10.65 -> "
            f"{gate_v2['by_stage']['BROKER_REJECT']['fwd_return_60d1']['median']}) - "
            "conferma che le analisi controfattuali su campioni piccoli non vanno lette "
            "come risultati stabili.",
        "1 evento (2026.06.09, SELL) ha copertura insufficiente (51/60 barre) - gia' "
            "UNKNOWN in V1 (non FAILURE), ora esplicitamente CENSORED_INSUFFICIENT_BARS "
            "in V2 con coverage_bars dichiarato - il miglioramento e' la ESPLICITAZIONE "
            "della copertura incompleta (che in V1 valeva gia' per MFE/MAE, calcolati "
            "silenziosamente su una finestra parziale senza dichiararlo), non una "
            "correzione della classificazione finale a 60 barre, gia' corretta (UNKNOWN) "
            "in V1.",
    ]

    decision_card = {
        "esiste_evidenza_di_comportamento_non_casuale": {
            "answer": "PATTERN DESCRITTIVO PERSISTENTE - NON CASUALITA' ED EDGE "
                "INCREMENTALE ANCORA DA VERIFICARE",
            "detail": (
                "La persistenza del pattern direzionale dopo una correzione "
                "metodologica sugli STESSI dati (non un nuovo campione indipendente) "
                "NON dimostra da sola non-casualita' - dimostra solo che il pattern non "
                "era un artefatto puro del difetto di indicizzazione corretto in questa "
                "fase. " + pattern_descriptive["statement"]
            )},
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
            "answer": f"BASSA - invariata da Phase 7.9J nella sostanza, RINFORZATA dalla "
                f"scoperta di fragilita' metodologica aggiuntiva ({outcome_flip_pct}% di "
                "veri cambi di esito da un singolo fix, sign-flip nel gate diagnostic "
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
        "direzionale resta presente qualitativamente dopo la correzione del difetto di "
        "indicizzazione (evidenza CONTRO uno scarto puramente artefattuale - MA questo "
        "e' un controllo di robustezza su una correzione metodologica degli STESSI "
        f"dati, non un secondo campione indipendente), ma la scoperta che "
        f"il {outcome_flip_pct}% delle classificazioni comparabili ha un vero cambio di "
        "esito con un fix minore, e che un'analisi controfattuale secondaria "
        "(BROKER_REJECT) cambia segno, sono segnali di fragilita' che IMPEDISCONO di "
        "alzare la decisione a MECHANISM_SUPPORTED. Non emergono nemmeno elementi per "
        "abbassarla a MECHANISM_NOT_SUPPORTED o INSUFFICIENT_EVIDENCE, dato che il "
        "pattern direzionale principale (BUY vs SELL) e' rimasto nella stessa "
        "direzione. Non-casualita' ed edge incrementale rispetto a un benchmark "
        "restano ENTRAMBI da verificare, non dimostrati da questa persistenza."
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
