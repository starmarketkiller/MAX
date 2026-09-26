#!/usr/bin/env python3
"""Phase 7.9H - classificazione causale degli 8 eventi B-only residui
(presenti nella ricostruzione offline D1-isolata post-fix, MAI osservati
nel trace live reale del run 7.9G/7.9H). Ritenuti nel dataset, non
eliminati - nessuna nuova modifica all'EA in questa fase.
"""
import os
import sys

PHASE79H_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE79H_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import save_json, wrap_with_provenance  # noqa: E402

# I 3 eventi analizzati in Phase 7.9E come "missing" PRE-fix (baseline
# ee469d4). Di questi, 2019.06.21 e' ORA fra i 47 trade reali post-fix
# (risolto dal fix) - 2019.04.18 e 2019.05.15 restano assenti anche POST-fix.
PRE_FIX_ANALYZED_DATES = {"2019.04.18", "2019.05.15", "2019.06.21"}
RESOLVED_BY_FIX = {"2019.06.21"}

RULED_OUT_ALL = [
    {
        "mechanism": "CROSS_TIMEFRAME_STATE_CONTAMINATION (il meccanismo originale "
            "IMPLEMENTATION_DEFECT_CONFIRMED di Phase 7.9E/F/G)",
        "why_ruled_out": "Strutturalmente impossibile post-fix: la guardia "
            "'if(tf != NXS_Profile_TF(\"BREAKOUT_ACC\")) return s;' precede ORA ogni "
            "lettura/scrittura di g_breakoutAccState (verificato direttamente sul codice "
            "attuale, MQL5/Include/NEXUS_v1/NXS_Strategies.mqh:1548) - nessun pass su un "
            "timeframe diverso da quello dichiarato puo' piu' toccare lo stato.",
    },
    {
        "mechanism": "EXECUTION_GATES suppression (score/HTF/velocity/protections)",
        "why_ruled_out": "Verificato sul trace live: questi 8 eventi non compaiono nel "
            "trace NEMMENO come stage BLOCKED o BROKER_REJECT (che coprono gia' "
            "esplicitamente gli 11+9 eventi effettivamente soppressi a valle della "
            "generazione, tutti gia' contabilizzati nei 67 del trace) - sono "
            "completamente ASSENTI dal trace, non soppressi dopo essere stati generati.",
    },
]

CANDIDATE_MECHANISMS_ALL = [
    {
        "mechanism": "INTRADAY_BAR_TIMING_DIFFERENCE",
        "description": "La ricostruzione offline calcola accept_up/accept_dn/range su "
            "barre D1 GIA' chiuse (CopyRates post-hoc, valori OHLC definitivi). L'EA live "
            "valuta NXS_Strat_BreakoutAcc() al primo tick M15 in cui rileva una nuova "
            "barra D1 (iTime(...,0) cambiato) - se in quel preciso istante il feed reale "
            "(spread/quotazione del broker) mostra un valore di chiusura leggermente "
            "diverso da quello poi definitivamente cristallizzato nella cache storica "
            "usata dalla ricostruzione offline, accept_up/accept_dn potrebbe non "
            "risultare vero nel momento reale della valutazione anche se lo e' nella "
            "barra D1 finale.",
            "status": "PLAUSIBILE, NON VERIFICATO IN QUESTA FASE",
    },
    {
        "mechanism": "ACTIVATION_GATE_INDICATOR_READINESS_GAP",
        "description": "Ipotesi originale di Phase 7.9E: il pass D1 nel router reale "
            "richiede che tutti e 10 gli indicatori ausiliari del multi-TF collector "
            "(ADX/RSI/Bollinger/MACD/SAR/ATR/EMA200/EMA9/EMA21/Ichimoku) siano pronti "
            "PRIMA che NXS_Strat_BreakoutAcc() venga anche solo chiamata - se anche uno "
            "solo di questi fallisce su una barra D1 specifica (dati insufficienti, "
            "gap del feed), l'intero pass D1 viene saltato per quel tick, indipendentemente "
            "dalla logica di BREAKOUT_ACC. Il run di validazione 7.9E citato (activation_fail=0) "
            "copriva una finestra diversa, non l'intero 2019-2026 ne' queste date specifiche.",
        "status": "PLAUSIBILE, NON VERIFICATO IN QUESTA FASE - richiederebbe un nuovo run "
            "diagnostico dedicato (strumentazione del gate di attivazione su queste 8 date "
            "esatte), non eseguito qui per restare nello scope di questa fase (censimento e "
            "costruzione dataset, non nuova sperimentazione EA).",
    },
]

DATES_INFO = {
    "2019.02.21": 1, "2019.04.18": -1, "2019.05.15": 1, "2019.12.27": 1,
    "2021.09.07": 1, "2021.09.20": -1, "2022.01.21": 1, "2023.08.21": -1,
}


def build():
    events = []
    for date_str, direction in DATES_INFO.items():
        pre_fix_analyzed = date_str in PRE_FIX_ANALYZED_DATES
        notes = (
            f"Evento presente nella ricostruzione D1-isolata post-fix (accept/cooldown/"
            f"upstream-htf tutti soddisfatti) ma MAI osservato nel trace live reale del "
            f"run 7.9G/7.9H (ne' come GENERATED, ne' come BLOCKED/BROKER_REJECT)."
        )
        if pre_fix_analyzed:
            notes += (
                f" Questa data era GIA' stata analizzata in Phase 7.9E come evento mancante "
                f"PRE-fix (baseline ee469d4), con causa allora attribuita al meccanismo "
                f"generale di cross-TF state contamination. "
            )
            if date_str in RESOLVED_BY_FIX:
                notes += "RISOLTA dal fix 7.9G (ora fra i 47 trade reali post-fix)."
            else:
                notes += (
                    "NON risolta dal fix 7.9G: resta assente anche post-fix, quindi la causa "
                    "originale (cross-TF contamination) NON puo' essere l'unica spiegazione "
                    "per QUESTA data specifica - serve un meccanismo aggiuntivo o diverso."
                )
        else:
            notes += " Data non precedentemente analizzata (nuova scoperta di questa fase)."

        events.append({
            "d1_bar_date": date_str, "direction": direction,
            "previously_analyzed_pre_fix": pre_fix_analyzed,
            "resolved_by_7_9g_fix": date_str in RESOLVED_BY_FIX,
            "ruled_out": RULED_OUT_ALL,
            "candidate_mechanisms": CANDIDATE_MECHANISMS_ALL,
            "causal_status": "PARTIALLY_EXPLAINED_NOT_ENOUGH_EVIDENCE_FOR_EXACT_MECHANISM",
            "notes": notes,
        })

    return {
        "phase": "7.9H",
        "scope": "Classificazione causale degli 8 eventi B-only residui identificati in "
            "Phase 7.9G/7.10 (matched=67, only_a=0, only_b=8) - nessuna eliminazione, "
            "nessuna nuova modifica all'EA in questa fase.",
        "no_ea_modification_this_phase": True,
        "aggregate_finding": (
            "Il meccanismo originale (CROSS_TIMEFRAME_STATE_CONTAMINATION) e' strutturalmente "
            "escluso per tutti e 8 gli eventi post-fix (verificato sul codice attuale). Di 3 "
            "eventi gia' analizzati pre-fix, il fix ne ha risolto 1/3 (2019.06.21, ora reale) "
            "ma non gli altri 2/3 (2019.04.18, 2019.05.15) - a conferma che per questi resta "
            "un meccanismo diverso e non ancora isolato. Nessuno degli 8 eventi appare come "
            "BLOCKED/BROKER_REJECT nel trace live (escludendo suppression via execution gates) "
            "- sono completamente assenti, suggerendo che la funzione strategia non venga mai "
            "richiamata con successo su queste barre D1 specifiche nel run reale. 2 meccanismi "
            "candidati identificati (differenza di timing intrabarra, gap nel gate di "
            "attivazione) - nessuno confermato sperimentalmente in questa fase."
        ),
        "distortion_direction_consistent_with_phase_7_10": "FALSE_NEGATIVE_RISK "
            "(soppressione, non fabbricazione, di segnali D1 genuini)",
        "recommended_follow_up_not_executed_here": (
            "Nuovo run diagnostico dedicato che strumenti il gate di attivazione D1 "
            "(readiness dei 10 indicatori ausiliari) e confronti il valore OHLC "
            "intrabarra vs finale esattamente su queste 8 date, per isolare quale dei 2 "
            "meccanismi candidati (o un terzo non ancora ipotizzato) sia la causa reale."
        ),
        "events": events,
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE79H_DIR, "b_only_residual_classification_v1.json"), doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(f"eventi classificati: {len(payload['events'])}")
    return doc


if __name__ == "__main__":
    main()
