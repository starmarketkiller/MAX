#!/usr/bin/env python3
"""Phase 7.10 - punto 4: schema riutilizzabile del Retroactive Strategy
Integrity Audit + BREAKOUT_ACC come primo case study completo.

NON esegue l'audit completo delle 83 strategie - definisce solo lo
schema e lo applica UNA VOLTA a BREAKOUT_ACC come prova di concetto.
"""
import os
import sys

PHASE710_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE710_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import save_json, wrap_with_provenance  # noqa: E402

BASELINE_COMMIT = "651d3a2a10e5c58acfc22ba820f518810356a73c"

PIPELINE_STAGES = [
    "ORIGINAL_PHENOMENON", "FORMAL_SPEC", "PYTHON_IMPLEMENTATION", "MQL5_IMPLEMENTATION",
    "TF_SESSION_HTF", "SIGNAL_TIMING", "STATEFUL_BEHAVIOR", "SL_TP_EXIT",
    "SELECTOR_PROFILE_GATES", "SIGNAL", "ORDER", "FILL", "OUTCOME_EVIDENCE",
]
STAGE_STATUSES = ["MATCHED", "PARTIAL", "MISMATCH", "UNKNOWN", "NOT_APPLICABLE"]
EVIDENCE_INTEGRITY_CLASSES = [
    "GENUINE_REFUTATION", "GENUINE_SUPPORT", "CONTAMINATED_EVIDENCE", "NEVER_REALLY_TESTED",
    "FORMALIZATION_GAP", "EXECUTION_GAP", "INSUFFICIENT_EVIDENCE",
]
DISTORTION_DIRECTIONS = ["FALSE_NEGATIVE_RISK", "FALSE_POSITIVE_RISK", "BOTH", "NONE_KNOWN"]


def schema():
    return {
        "schema_id": "RETROACTIVE_STRATEGY_INTEGRITY_AUDIT_V1",
        "purpose": "Schema riutilizzabile per verificare, per OGNI strategia del vault, se il "
            "risultato economico/statistico gia' registrato appartiene davvero all'oggetto "
            "che si crede di aver testato - senza fare optimization e senza cercare edge.",
        "pipeline_stages_ordered": PIPELINE_STAGES,
        "stage_status_values": STAGE_STATUSES,
        "stage_definitions": {
            "ORIGINAL_PHENOMENON": "La descrizione originale, in linguaggio naturale, "
                "dell'idea/pattern di mercato che ha motivato la strategia (fonte esterna, "
                "screenshot, chat, PDF, idea propria).",
            "FORMAL_SPEC": "La specifica formale (se esiste) che traduce il fenomeno in "
                "regole precise - timeframe, setup, trigger, invalidazione.",
            "PYTHON_IMPLEMENTATION": "Il codice Python (server/backtest.py o simili) che "
                "implementa la specifica per la ricerca offline.",
            "MQL5_IMPLEMENTATION": "Il codice MQL5 (NXS_Strategies*.mqh) che implementa la "
                "stessa specifica per l'esecuzione live/demo.",
            "TF_SESSION_HTF": "Timeframe dichiarato, eventuali vincoli di sessione, filtro "
                "HTF/trend - e la loro fedelta' fra le due implementazioni.",
            "SIGNAL_TIMING": "Quando esattamente il segnale viene valutato/emesso (bar-close, "
                "tick-live, shift esatti) - fedelta' fra Python e MQL5 E fedelta' del codice "
                "MQL5 al proprio commento/intento dichiarato.",
            "STATEFUL_BEHAVIOR": "Se la strategia ha stato persistente (cooldown, macchina a "
                "stati, valore ricorsivo) - come viene gestito, se e' scoped correttamente al "
                "proprio contesto (TF/sessione), se e' soggetto a CROSS_TIMEFRAME_STATE_"
                "CONTAMINATION o pattern simili.",
            "SL_TP_EXIT": "Come vengono decisi stop/target/uscita - nativi della strategia o "
                "overlay generico del framework (NXS_DefaultSLTP, profili).",
            "SELECTOR_PROFILE_GATES": "Come la strategia viene abilitata/instradata nel "
                "router (selettore, NXS_Profile_*, gate condivisi) - eventuali interazioni "
                "inattese con altre strategie o con l'architettura multi-TF.",
            "SIGNAL": "Il segnale grezzo generato (accettazione/trigger), prima di qualunque "
                "gate di esecuzione.",
            "ORDER": "Il tentativo di apertura ordine (preflight, sizing, gate di rischio).",
            "FILL": "L'esito reale dell'invio ordine (aperto/rifiutato/bloccato) nel motore "
                "reale (Tester o live).",
            "OUTCOME_EVIDENCE": "Il risultato economico/statistico registrato (PF, "
                "expectancy, n trade) e la sua provenienza dichiarata nel vault/registro.",
        },
        "evidence_integrity_final_classification": {
            "values": EVIDENCE_INTEGRITY_CLASSES,
            "definitions": {
                "GENUINE_REFUTATION": "Il risultato negativo e' attribuibile alla strategia "
                    "stessa (assenza di edge), non a un difetto di formalizzazione/esecuzione "
                    "- la pipeline e' MATCHED/PARTIAL end-to-end.",
                "GENUINE_SUPPORT": "Il risultato positivo e' attribuibile alla strategia "
                    "stessa - stessa condizione di fedelta' end-to-end.",
                "CONTAMINATED_EVIDENCE": "Il risultato (positivo O negativo) e' stato "
                    "influenzato da un difetto tecnico dimostrato (es. "
                    "CROSS_TIMEFRAME_STATE_CONTAMINATION) - non rappresenta la strategia "
                    "intesa.",
                "NEVER_REALLY_TESTED": "La pipeline ha un MISMATCH cosi' a monte (es. "
                    "FORMAL_SPEC vs MQL5_IMPLEMENTATION) che il 'test' non ha mai davvero "
                    "esercitato l'idea originale.",
                "FORMALIZATION_GAP": "L'idea originale non e' mai stata tradotta in una "
                    "specifica sufficientemente precisa da poter essere giudicata MATCHED/"
                    "MISMATCH - manca la FORMAL_SPEC o e' troppo vaga.",
                "EXECUTION_GAP": "La specifica e l'implementazione sono fedeli, ma "
                    "l'esecuzione reale (ORDER/FILL) ha introdotto una divergenza dimostrata "
                    "(diverso da CONTAMINATED_EVIDENCE: qui la causa e' nel motore di "
                    "esecuzione/gating, non nella generazione del segnale).",
                "INSUFFICIENT_EVIDENCE": "Non c'e' abbastanza informazione (campione, "
                    "provenienza, log) per classificare in nessuna delle altre categorie.",
            },
        },
        "distortion_direction": {
            "values": DISTORTION_DIRECTIONS,
            "definitions": {
                "FALSE_NEGATIVE_RISK": "Il difetto tende a SOPPRIMERE segnali/trade validi "
                    "(es. cooldown contaminato) - il risultato registrato rischia di essere "
                    "PIU' NEGATIVO del vero comportamento della strategia intesa.",
                "FALSE_POSITIVE_RISK": "Il difetto tende a GENERARE segnali/trade spuri o "
                    "valori distorti che sembrano validi - il risultato registrato rischia di "
                    "essere PIU' POSITIVO del vero comportamento.",
                "BOTH": "Il difetto puo' produrre in modo imprevedibile sia soppressione che "
                    "generazione spuria (es. contaminazione di uno stato di valore "
                    "ricorsivo/macchina a stati).",
                "NONE_KNOWN": "Nessuna distorsione nota o sospettata.",
            },
        },
        "usage_note": "Per ogni strategia dell'audit retrospettivo completo (non eseguito in "
            "questa fase), compilare gli stage nell'ordine indicato, assegnare lo status piu' "
            "debole osservato come riassunto, poi derivare evidence_integrity_final e "
            "distortion_direction dalla combinazione degli stage - MAI dal solo risultato "
            "economico.",
    }


def breakout_acc_case_study():
    return {
        "strategy": "BREAKOUT_ACC", "case_study_status": "FIRST_COMPLETE_CASE_STUDY",
        "stages": {
            "ORIGINAL_PHENOMENON": {
                "status": "MATCHED",
                "note": "Breakout con 'accettazione' (doppia chiusura oltre un range "
                    "consolidato) - idea originale luglio (fonte A, 7.9B), poi formalizzata.",
            },
            "FORMAL_SPEC": {
                "status": "MATCHED",
                "note": "Phase 7.9B lifecycle contract: D1, range 20 barre shift[3..22], "
                    "doppia chiusura, cooldown 8 barre per direzione, HTF filter, SL/TP "
                    "1.0/4.5xATR.",
            },
            "PYTHON_IMPLEMENTATION": {
                "status": "MATCHED",
                "note": "server/backtest.py:sig_breakout_acc + _breakout_acc_cooldown_series - "
                    "verificato riga-per-riga identico alla formula MQL5 (7.9C/7.9E). Mai "
                    "esposto alla contaminazione cross-TF per costruzione (simula una "
                    "strategia alla volta su un solo TF) - gia' rappresentava correttamente "
                    "BREAKOUT_ACC_INTENDED_D1_V1 senza saperlo.",
            },
            "MQL5_IMPLEMENTATION": {
                "status": "MISMATCH (pre-fix, Phase 7.9F) -> MATCHED (post-fix, Phase 7.9G)",
                "note": "Pre-fix: g_breakoutAccState condiviso cross-TF (IMPLEMENTATION_"
                    "DEFECT_CONFIRMED). Post-fix: guardia TF-scoped aggiunta, verificata "
                    "staticamente e sperimentalmente.",
            },
            "TF_SESSION_HTF": {
                "status": "MATCHED (post-fix)",
                "note": "D1 confermato come unico TF di valutazione reale dopo il fix. Gate "
                    "HTF verificato (shift0 vs shift1, effetto minore ma reale, 7.9E).",
            },
            "SIGNAL_TIMING": {
                "status": "MATCHED",
                "note": "Shift semantics (c1=shift1, c2=shift2, range shift[3..22]) "
                    "verificati algebricamente identici fra script offline e funzione reale "
                    "(7.9E) - nessun bug di indicizzazione, contrariamente al sospetto "
                    "iniziale.",
            },
            "STATEFUL_BEHAVIOR": {
                "status": "MISMATCH (pre-fix) -> MATCHED (post-fix)",
                "note": "Il cuore di questo intero filone di indagine (7.9E/F/G) - "
                    "CROSS_TIMEFRAME_STATE_CONTAMINATION, ora corretto.",
            },
            "SL_TP_EXIT": {"status": "MATCHED", "note": "Overlay di framework standard "
                "(NXS_DefaultSLTP, profilo), mai in discussione in nessuna fase."},
            "SELECTOR_PROFILE_GATES": {"status": "MATCHED", "note": "Selettore 9, profilo D1, "
                "nessuna altra anomalia di routing trovata."},
            "SIGNAL": {"status": "PARTIAL (post-fix)", "note": "Same-feed parity: 100% degli "
                "eventi live spiegati dalla ricostruzione offline, 10.7% di residuo SOLO "
                "offline non ancora diagnosticato (7.9G) - non MATCHED esatto."},
            "ORDER": {"status": "MATCHED (post-fix)", "note": "Funnel di esecuzione pulito "
                "(7.9D, riconfermato post-fix: accounting riconciliato, gate OPEN_POSITION "
                "finalmente significativo)."},
            "FILL": {"status": "MATCHED (post-fix)", "note": "47 trade realmente aperti "
                "post-fix, 9 broker_reject spiegati dall'accounting del certificato."},
            "OUTCOME_EVIDENCE": {
                "status": "MISMATCH",
                "note": "Il risultato storico (4 trade, tutti in perdita, Phase E) e' "
                    "attribuibile all'implementazione CONTAMINATA (pre-fix), non alla "
                    "strategia D1 intesa - marcato HISTORICAL_IMPLEMENTATION_EVIDENCE / "
                    "NOT_EVIDENCE_FOR_CANONICAL_D1 (7.9G). Nessun risultato economico ANCORA "
                    "esiste per BREAKOUT_ACC_INTENDED_D1_V1 (dataset canonico non ancora "
                    "costruito - prossima fase).",
            },
        },
        "evidence_integrity_final": "CONTAMINATED_EVIDENCE",
        "evidence_integrity_rationale": "Il risultato storico (4 trade, Phase E/7.9D) e' "
            "dimostrabilmente influenzato da CROSS_TIMEFRAME_STATE_CONTAMINATION (STATEFUL_"
            "BEHAVIOR=MISMATCH pre-fix) - non rappresenta la strategia D1 intesa. Non e' ne' "
            "GENUINE_REFUTATION ne' EXECUTION_GAP (la causa e' nella generazione del segnale, "
            "non nel funnel di esecuzione, gia' verificato pulito in 7.9D).",
        "distortion_direction": "FALSE_NEGATIVE_RISK",
        "distortion_direction_rationale": "Il meccanismo dimostrato (cooldown condiviso "
            "cross-TF) e' quasi esclusivamente SOPPRESSIVO (blocca segnali D1 genuini "
            "quando un altro TF ha 'sparato' di recente) - non genera segnali D1 spuri. Il "
            "risultato storico a 4 trade rischia quindi di essere SISTEMATICAMENTE PIU' "
            "SCARSO (meno trade, campione insufficiente) di quanto la strategia D1 intesa "
            "produrrebbe realmente - NON il contrario.",
        "current_readiness": "NOT_YET_VALIDATED - identita' canonica stabilita "
            "(BREAKOUT_ACC_INTENDED_D1_V1), nessun dataset economico ancora costruito su di "
            "essa (prossima fase, non eseguita qui).",
    }


def main():
    schema_payload = schema()
    case_study_payload = breakout_acc_case_study()
    combined = {"phase": "7.10", "task": 4, "baseline_commit": BASELINE_COMMIT,
                "schema": schema_payload, "breakout_acc_case_study": case_study_payload}
    doc = wrap_with_provenance(combined, os.path.basename(__file__))
    save_json(os.path.join(PHASE710_DIR, "retroactive_strategy_integrity_audit_schema_v1.json"), doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print("evidence_integrity_final:", case_study_payload["evidence_integrity_final"])
    print("distortion_direction:", case_study_payload["distortion_direction"])
    return doc


if __name__ == "__main__":
    main()
