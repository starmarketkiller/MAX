#!/usr/bin/env python3
"""Phase 7.9F - punti 6, 7, 8: classificazione del verdetto (cosa fa il
codice oggi vs cosa dice la specifica), prossima decisione (NON
eseguita), preservazione della cronologia storica."""
import os
import sys

PHASE79F_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE79F_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import load_json, save_json, wrap_with_provenance  # noqa: E402

BASELINE_COMMIT = "e78a17e4c738586c4c16805ae8915c6e29874354"

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


def build():
    authority = load_json(os.path.join(PHASE79F_DIR, "breakout_acc_strategy_identity_authority_v1.json"))["payload"]
    semantics = load_json(os.path.join(PHASE79F_DIR, "breakout_acc_implemented_vs_intended_semantics_v1.json"))["payload"]

    verdict = "IMPLEMENTATION_DEFECT_CONFIRMED"
    verdict_reasoning = {
        "what_code_does_today": "g_breakoutAccState (cooldown per-direzione) e' un unico "
            "struct globale, letto/scritto ad ogni pass multi-TF del router (M5/M15/M30/H1/H4/"
            "D1), indipendentemente dal fatto che il pass corrente sia quello dichiarato per "
            "BREAKOUT_ACC (D1) - confermato a codice (NXS_Strategies.mqh:1531-1561, "
            "NEXUS_EA_v2.mq5:683-713) e sperimentalmente (7.9E + 7.9F, collasso 95->0 con "
            "l'ordine ESATTO dei pass reali).",
        "what_specification_says": "TUTTE le fonti identificate (6 fonti indipendenti, "
            "cronologicamente distribuite dal commit originale del cooldown fino all'audit "
            "7.9B del 21/09 - vedi breakout_acc_strategy_identity_authority_v1.json) "
            "descrivono il cooldown in termini ESCLUSIVAMENTE D1/singola-istanza: 'blocca lo "
            "stesso verso per N barre dopo un ingresso', 'evitare l'inseguimento ripetuto "
            "dello stesso movimento'. NESSUNA fonte, in nessun momento, menziona o giustifica "
            "una condivisione cross-timeframe.",
        "supporting_evidence": [
            "L'architettura multi-TF esisteva gia' da ~54 giorni quando il cooldown e' stato "
            "introdotto - non era un elemento nuovo di cui il fix doveva necessariamente "
            "tenere conto in modo esplicito, ma nemmeno un motivo per pensare che la "
            "condivisione fosse intenzionale (nessuna menzione in nessuna direzione).",
            "Lo stesso identico pattern architetturale (struct globale non scoped) e' stato "
            "applicato SIMULTANEAMENTE a BAR_UPDN nello stesso commit - coerente con una "
            "svista di design copiato fra due strategie diverse, non una decisione "
            "specifica e ponderata per BREAKOUT_ACC.",
            "L'audit 7.9B (21/09, il piu' recente e rigoroso prima di questa fase) descrive "
            "il cooldown nello STESSO modo D1-scoped del commit originale, 19 giorni dopo che "
            "il comportamento cross-TF era gia' in produzione - indicando che nemmeno un "
            "audit di identita' dedicato aveva notato l'interazione.",
            "L'analisi architetturale (side-effect-before-filter) mostra che le chiamate a "
            "NXS_Strat_BreakoutAcc() durante i pass non-D1 non hanno ALCUNO scopo funzionale "
            "identificato - il loro output viene sempre scartato, solo il side-effect "
            "sopravvive. Questo e' il pattern classico di un bug di scoping, non di una "
            "funzionalita' condivisa deliberata.",
        ],
        "counter_evidence_considered": "Nessuna fonte suggerisce l'ipotesi opposta "
            "(comportamento intenzionale) - non e' stato trovato alcun documento, commento o "
            "commit message che giustifichi la condivisione cross-TF come una caratteristica "
            "voluta. L'ipotesi 'comportamento intenzionale' e' stata attivamente cercata "
            "(non solo assunta come falsa) e non ha trovato supporto.",
        "not_classified_as_ambiguous_because": "L'evidenza documentale e' insolitamente "
            "univoca per un progetto di questa complessita' - 6 fonti indipendenti concordano "
            "senza eccezioni. SPEC_AMBIGUOUS_IMPLEMENTATION_DIVERGENCE richiederebbe fonti "
            "contrastanti o silenzio totale; qui c'e' consenso esplicito, solo mai messo alla "
            "prova contro l'implementazione reale.",
        "not_classified_as_root_cause_unresolved_because": "Il meccanismo causale (non solo "
            "l'esistenza di UNA causa, ma il meccanismo ESATTO, con ordine di pass reale e "
            "un esempio causale concreto con timestamp) e' stato isolato e dimostrato con "
            "prove dirette - resta non riprodotta solo la cifra ESATTA finale (0 vs 4), non "
            "l'identita' della causa.",
    }

    next_decision = VERDICT_TO_NEXT_DECISION[verdict]
    next_decision_rationale = (
        "Con IMPLEMENTATION_DEFECT_CONFIRMED, la decisione mappata e' "
        "FIX_LIVE_IMPLEMENTATION_THEN_REESTABLISH_PARITY: la strategia canonica da considerare "
        "per la ricerca futura e' BREAKOUT_ACC_INTENDED_D1_V1 (scoped a D1, supportata da "
        "evidenza documentale univoca), non BREAKOUT_ACC_IMPLEMENTED_V1 (contaminata cross-TF, "
        "un difetto, non una caratteristica). I 4 trade osservati in 7,5 anni NON sono piu' "
        "evidenza valida sulla strategia D1 intesa - sono evidenza sulla sua implementazione "
        "contaminata. Prima di qualunque nuova statistica, il bug deve essere corretto "
        "nell'EA live, ricompilato, e la parity ristabilita con l'implementazione corretta - "
        "SOLO ALLORA la valutazione dell'edge avrebbe senso."
    )
    concrete_next_step_not_executed = (
        "Scoping di g_breakoutAccState per timeframe (es. un array indicizzato per TF invece "
        "di un singolo struct, o un controllo esplicito 'if(NXS_EffTF() != NXS_Profile_TF("
        "\"BREAKOUT_ACC\")) return s;' prima di leggere/scrivere lo stato) nell'EA live, "
        "seguito da recompile, verifica di parity fra la nuova implementazione e una replica "
        "offline corretta, e SOLO ALLORA un nuovo Serious backtest. NON eseguito in questa "
        "fase - richiede esplicita autorizzazione dell'utente per modificare l'EA live, per "
        "lo standing constraint di questo progetto."
    )

    assert verdict in ALLOWED_VERDICTS

    payload = {
        "phase": "7.9F", "candidate": "BREAKOUT_ACC", "baseline_commit": BASELINE_COMMIT,
        "central_question": "La mutazione cross-timeframe di g_breakoutAccState e' parte "
            "intenzionale di BREAKOUT_ACC, o un difetto implementativo rispetto all'identita' "
            "congelata della strategia?",
        "final_verdict": verdict, "verdict_reasoning": verdict_reasoning,
        "next_decision": next_decision, "next_decision_rationale": next_decision_rationale,
        "concrete_next_step_not_executed": concrete_next_step_not_executed,
        "next_step_not_executed": True,
        "historical_chronology_preserved": {
            "7_9c": "EXECUTION_GAP_DOMINANT - apparente gap di esecuzione (80 vs 4)",
            "7_9d": "il funnel di esecuzione e' in realta' pulito (0 blocchi, 4/4 aperti) - "
                "l'assunzione 7.9C era nel posto sbagliato",
            "7_9e": "scoperta della contaminazione di stato cross-timeframe nel router live "
                "come meccanismo dominante (95->0 con stato condiviso)",
            "7_9f": "determinato che la contaminazione e' un DIFETTO IMPLEMENTATIVO rispetto "
                "all'identita' documentata della strategia (D1-scoped), non una semantica "
                "intenzionale - i 4 trade osservati NON sono evidenza valida sulla strategia "
                "D1 intesa",
            "frozen_artifacts_not_modified": [
                "7.9C: breakout_acc_event_parity_matrix_v1.json",
                "7.9D: breakout_acc_execution_parity_decision_v1.json",
                "7.9E: breakout_acc_reconstruction_decision_v1.json",
            ],
        },
        "no_python_bug_replication_performed": True,
        "no_live_ea_modification": True, "no_performance_backtest": True, "no_optimization": True,
        "volbrk_not_reopened": True, "h006_not_reopened": True, "hvcw_backlog_only": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE79F_DIR, "breakout_acc_identity_adjudication_v1.json"), doc)
    print(f"final_verdict={payload['final_verdict']}")
    print(f"next_decision={payload['next_decision']}")
    return doc


if __name__ == "__main__":
    main()
