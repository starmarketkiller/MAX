#!/usr/bin/env python3
"""Phase 7.26 punto L - RESEARCH_PRIORITY_QUEUE_V1. Criteri dichiarati
PRIMA di assegnare i punteggi (nessun criterio e' il profit factor -
esplicitamente vietato dal task). Ogni criterio 1-5, punteggio finale =
somma semplice non pesata (pesi diversi non giustificati in questa
fase - dichiarato come semplificazione)."""
import os
import sys

PHASE726_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE726_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

CRITERIA = ["expected_information_gain", "evidence_quality", "sample_availability",
           "integrity_confidence", "novelty", "cost_time_to_test",
           "availability_of_untouched_data", "mechanism_distinctiveness"]
# cost_time_to_test: 5 = economico/veloce, 1 = costoso/lento (punteggio alto = fa salire la coda)

CANDIDATES = [
    {
        "candidate_id": "BACKFILL_TEMPORAL_AND_EXIT_EFFICIENCY_BREAKOUT_ACC_ORDER_BLOCK",
        "description": "Calcolare temporal_concentration ed exit_efficiency per BREAKOUT_ACC e "
                      "ORDER_BLOCK (gap esplicito trovato dalla Cross-Strategy Synthesis - solo "
                      "LIQ_SWEEP li ha oggi) - usa dataset GIA' esistenti, zero nuovo run.",
        "scores": {"expected_information_gain": 4, "evidence_quality": 5, "sample_availability": 5,
                  "integrity_confidence": 5, "novelty": 2, "cost_time_to_test": 5,
                  "availability_of_untouched_data": 1, "mechanism_distinctiveness": 2},
        "rationale": "Costo quasi zero (dati gia' raccolti), chiude un gap di comparabilita' "
                    "cross-strategy identificato meccanicamente, ma bassa novita' (nessun dato "
                    "nuovo) e nessun untouched data coinvolto.",
    },
    {
        "candidate_id": "BUY_BIAS_BENCHMARK_VS_BUY_AND_HOLD",
        "description": "Testare la CANDIDATE_HYPOTHESIS della sintesi trasversale (dominanza BUY "
                      "condivisa da 3/3 strategie potrebbe riflettere un trend secolare del "
                      "simbolo, non un edge specifico) confrontando ciascuna strategia con un "
                      "benchmark buy-and-hold/random-entry sullo stesso periodo esatto.",
        "scores": {"expected_information_gain": 5, "evidence_quality": 3, "sample_availability": 4,
                  "integrity_confidence": 4, "novelty": 5, "cost_time_to_test": 4,
                  "availability_of_untouched_data": 2, "mechanism_distinctiveness": 5},
        "rationale": "Se confermata, invaliderebbe (o ridimensionerebbe) l'apparente edge di TUTTE "
                    "e 3 le strategie economiche contemporaneamente - il guadagno di informazione "
                    "potenziale e' il piu' alto della coda. Costo moderato (nessun nuovo run MT5, "
                    "solo un confronto con una serie di prezzo gia' disponibile).",
        "status": "COMPLETED_PHASE_7_27",
        "outcome": "Testato con benchmark preregistrato (non solo buy-and-hold: random/periodic/"
                  "regime-matched/unconditional) - decisione: "
                  "BUY_DOMINANCE_LARGELY_EXPLAINED_BY_MARKET_REGIME (nessuna strategia batte "
                  "significativamente il benchmark long regime-matched). Vedi phase7_27/"
                  "decision_card_v1.json.",
    },
    {
        "candidate_id": "FVG_CONT_INTEGRITY_AUDIT",
        "description": "Prossimo candidato naturale per un audit di integrita' (stesso schema "
                      "gia' usato per ORDER_BLOCK/TSI/LIQ_SWEEP) - PF quasi breakeven (0.96) e un "
                      "segnale A/B interno mai validato su MT5 (Phase 7.20 shortlist) - MA prima "
                      "va mappata la condivisione di codice con IFVG/FVG_MIT/FVG_MIT_WINDOW.",
        "scores": {"expected_information_gain": 3, "evidence_quality": 2, "sample_availability": 3,
                  "integrity_confidence": 2, "novelty": 4, "cost_time_to_test": 3,
                  "availability_of_untouched_data": 4, "mechanism_distinctiveness": 2},
        "rationale": "Novita' alta (mai auditata) ma integrity_confidence bassa PROPRIO perche' "
                    "condivide codice con 3 altre varianti (IFVG/FVG_MIT/FVG_MIT_WINDOW) - il "
                    "lavoro di mappatura preliminare (mechanism_distinctiveness basso) va fatto "
                    "PRIMA di poter dire se questo e' davvero un test distinto o una ripetizione.",
    },
    {
        "candidate_id": "LIQ_SWEEP_PASSIVE_FORWARD_ACCUMULATION",
        "description": "Nessun nuovo lavoro attivo - lasciare accumulare altri trade forward nella "
                      "finestra genuinamente untouched (dopo il 2026.09.27) prima di ri-valutare "
                      "H_LIQ_SWEEP_EDGE_EXISTS con un campione OOS piu' grande di 6.",
        "scores": {"expected_information_gain": 3, "evidence_quality": 4, "sample_availability": 2,
                  "integrity_confidence": 5, "novelty": 1, "cost_time_to_test": 5,
                  "availability_of_untouched_data": 5, "mechanism_distinctiveness": 1},
        "rationale": "Costo quasi zero (passivo, nessun lavoro attivo) - ma richiede TEMPO di "
                    "calendario (bassa sample_availability oggi) prima di essere informativo.",
    },
    {
        "candidate_id": "REMAINING_STRATEGY_UNIVERSE_81_CANDIDATES",
        "description": "Le restanti ~81 strategie del corpus (phase7_20/strategy_universe_v1.json) "
                      "non ancora shortlistate/auditate.",
        "scores": {"expected_information_gain": 2, "evidence_quality": 1, "sample_availability": 2,
                  "integrity_confidence": 1, "novelty": 3, "cost_time_to_test": 2,
                  "availability_of_untouched_data": 3, "mechanism_distinctiveness": 3},
        "rationale": "Bucket generico a bassa priorita' - nessuna di queste ha ancora superato "
                    "nemmeno il primo filtro di shortlist (Phase 7.20) usato per le 4 gia' "
                    "studiate.",
    },
]


def build():
    ranked = []
    for c in CANDIDATES:
        c = dict(c)
        c.setdefault("status", "PENDING")
        total = sum(c["scores"][k] for k in CRITERIA)
        ranked.append({**c, "total_score_unweighted": total})
    ranked.sort(key=lambda c: -c["total_score_unweighted"])
    pending = [c for c in ranked if c["status"] == "PENDING"]

    payload = {
        "criteria_declared_before_scoring": CRITERIA,
        "pf_explicitly_not_a_criterion": True,
        "scoring_method": "somma semplice non pesata 1-5 per criterio - pesi differenziati non "
                        "giustificati in questa fase (semplificazione dichiarata).",
        "ranked_candidates": ranked,
        "top_priority": pending[0]["candidate_id"] if pending else None,
        "top_priority_excludes_completed": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE726_DIR, "research_priority_queue_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    for c in payload["ranked_candidates"]:
        print(f"  {c['total_score_unweighted']:2d}  {c['candidate_id']}")


if __name__ == "__main__":
    main()
