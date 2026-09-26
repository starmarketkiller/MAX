#!/usr/bin/env python3
"""Phase 7.12 - Protocollo diagnostico per la candidata prioritaria
(ORDER_BLOCK). SOLO PROGETTAZIONE - nessuna esecuzione in questa fase,
nessuna modifica all'EA. Distingue esplicitamente verifica
dell'implementazione, validita' dell'evidenza storica, e redditivita'
(quest'ultima NON presunta ne' indagata)."""
import os
import sys

PHASE712_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE712_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import save_json, wrap_with_provenance  # noqa: E402


def build():
    return {
        "phase": "7.12", "candidate": "ORDER_BLOCK",
        "not_executed_this_phase": True,
        "no_ea_modification_this_phase": True,
        "supersedes_note": "Nessuno - primo protocollo dedicato a ORDER_BLOCK. Ricalca "
            "deliberatamente la metodologia gia' validata per BREAKOUT_ACC (Phase "
            "7.9C-G), riutilizzando strumenti e infrastruttura esistenti.",

        "1_precise_defect_hypothesis": (
            "NXS_Strat_OrderBlock() (MQL5/Include/NEXUS_v1/NXS_Strategies.mqh:2141) "
            "legge tf=NXS_EffTF() (dinamico, cambia a ogni pass del router multi-TF) e "
            "lo passa DIRETTAMENTE a NXS_OB_UpdateSide(dir, g_obBuy/g_obSell, tf, atr, "
            "curBar0) SENZA alcuna guardia 'if(tf != NXS_Profile_TF(\"ORDER_BLOCK\")) "
            "return s;' (assente, verificato riga per riga - la riga 2143 controlla "
            "SOLO InpStrat_ORDER_BLOCK e NXS_SelectorAllows(15), non il TF attivo). "
            "IPOTESI: durante un pass su un TF diverso da D1 (il profile_tf "
            "dichiarato), la funzione (a) puo' CREARE una zona Order Block "
            "(obLo/obHi) usando OHLC di quel TF invece di D1, o (b) puo' INVALIDARE "
            "una zona D1 gia' attiva leggendo iClose(tf,1) del TF sbagliato, o (c) "
            "puo' CONSUMARE (one-shot, st.active=false) una zona D1 in risposta a un "
            "retest apparente calcolato sul TF sbagliato - in tutti e 3 i casi, lo "
            "stato g_obBuy/g_obSell osservato dal pass D1 successivo sarebbe gia' "
            "stato alterato da un pass estraneo, esattamente il meccanismo 'discard "
            "output, keep side effect' gia' dimostrato per BREAKOUT_ACC."
        ),

        "2_reference_implementation_and_config": {
            "baseline_commit": "8e405e5 (HEAD dopo Phase 7.9K)",
            "live_ea_file": "MQL5/Experts/NEXUS_EA_v2.mq5 (NON modificato in questa "
                "fase - solo riferimento)",
            "strategy_file": "MQL5/Include/NEXUS_v1/NXS_Strategies.mqh:2069-2153",
            "canonical_config_fingerprint": (
                "strat=ORDER_BLOCK|sel=15|srcTF=PERIOD_D1|exit=RAW|lot=0.0100|lev=500|"
                "ESL=0|DailyDD=0|TotalDD=0|DPT=0|Ruin=0|RiskShield=0 - STESSA "
                "convenzione di Research Mode gia' usata per BREAKOUT_ACC (Phase 7.9G, "
                "vedi breakoutacc_postfix_parity_diagnostic.ini come template diretto, "
                "sostituendo solo InpStrategySelector=15 e InpStrat_ORDER_BLOCK=true)."
            ),
            "period": "2019.02.03 - 2026.08.15 (stesso intervallo canonico di "
                "BREAKOUT_ACC, per confrontabilita' diretta della metodologia)",
            "important_difference_from_breakout_acc": (
                "ORDER_BLOCK dipende da g_atr (calcolato altrove nel router, non "
                "dentro la funzione stessa) e da g_structH1.trend (struttura esterna "
                "H1) - queste dipendenze DEVONO essere verificate per la loro propria "
                "sensibilita' al TF attivo prima di attribuire un'eventuale "
                "discrepanza al SOLO meccanismo g_obBuy/g_obSell. Non presente in "
                "BREAKOUT_ACC (nessuna dipendenza esterna equivalente)."
            ),
        },

        "3_inputs_and_data_needed": [
            "Storico tick/OHLC GOLD gia' disponibile nel terminale (stessa fonte di "
            "BREAKOUT_ACC, nessun nuovo dato da acquisire).",
            "EA diagnostico standalone (copia byte-identica di NEXUS_EA_v2.mq5 + "
            "export read-only, stesso pattern di NXS_BreakoutAccDealExportDiagnostic."
            "mq5 - Phase 7.9H) O, in alternativa piu' semplice qui, un secondo run "
            "Tester con una guardia TF di PROVA (vedi punto 4) - la decisione fra le "
            "due strade e' un blocker aperto, non risolto in questa fase (vedi punto "
            "7).",
            "Il Decision/Gate/Execution Trace v1 gia' esistente (NXS_Trace.mqh) - "
            "STRATEGIA-AGNOSTICO, emesso dal router (NEXUS_EA_v2.mq5:1313), NESSUNA "
            "nuova strumentazione di per se' necessaria per contare GENERATED/BLOCKED/"
            "OPENED/BROKER_REJECT di ORDER_BLOCK.",
        ],

        "4_controlled_comparison": {
            "stream_A_live_multi_tf": "Run diagnostico Research Mode (selector=15) sul "
                "codice ATTUALE (nessuna guardia TF) - conta segnali GENERATED/OPENED "
                "reali via il trace esistente, ESATTAMENTE come per BREAKOUT_ACC "
                "Phase 7.9G.",
            "stream_B_offline_d1_isolated": "Ricostruzione OFFLINE che replica "
                "NXS_OB_UpdateSide() USANDO SOLO barre D1 (mai chiamata durante altri "
                "pass) - stesso approccio di NXS_BreakoutAccCadenceDiagnostic.mq5 "
                "(Phase 7.9E), da costruire ex novo per la logica specifica di "
                "ORDER_BLOCK (zona/invalidazione/retest, non un semplice cooldown).",
            "comparison_metric": "Conteggio e TIMESTAMP dei segnali generati (bar_date, "
                "direzione) fra A e B - se A << B con lo stesso pattern di 'evento "
                "presente in B ma assente in A' gia' visto per BREAKOUT_ACC, il "
                "meccanismo e' corroborato; se A ≈ B, l'ipotesi e' indebolita e va "
                "riconsiderata.",
            "explicit_non_goal": "NESSUN confronto di P&L/PF/winrate in nessuna fase di "
                "questo confronto - solo conteggio/timing di eventi strutturali.",
        },

        "5_state_signal_funnel_metrics": [
            "n_generated, n_blocked, n_opened, n_broker_reject (via certificato "
            "Test Validity gia' esistente, come per BREAKOUT_ACC)",
            "n_zone_created, n_zone_invalidated, n_zone_consumed_by_retest - NUOVE "
            "metriche da aggiungere SOLO al codice diagnostico offline (stream B), "
            "MAI al codice live (stream A resta strumentazione esistente, invariata)",
            "distribuzione temporale (per anno) delle discrepanze A-vs-B, per "
            "verificare se il meccanismo e' costante o concentrato in periodi "
            "specifici (es. maggiore attivita' multi-TF in certi regimi)",
        ],

        "6_confirmation_vs_falsification_criteria": {
            "would_confirm": (
                "Stream B (D1-isolato) genera SOSTANZIALMENTE piu' eventi di Stream A "
                "(live, multi-TF reale), con gli eventi 'mancanti' in A concentrati su "
                "date in cui un pass non-D1 e' documentabile (via trace) come avvenuto "
                "fra la creazione della zona e il suo retest atteso - stesso pattern "
                "logico di BREAKOUT_ACC Phase 7.9E."
            ),
            "would_falsify": (
                "Stream A ≈ Stream B (differenza spiegabile da altre cause note, es. "
                "g_structH1.trend o gate execution generici) - indicherebbe che "
                "l'assenza di guardia TF non produce un effetto pratico misurabile per "
                "ORDER_BLOCK specificamente (possibile se il pool di zone e' "
                "raramente attivo su altri TF per ragioni di mercato, non di codice)."
            ),
            "ambiguous_case_handling": "Se il confronto risultasse ambiguo (es. "
                "differenza piccola ma non nulla), NON dichiarare ne' confermare ne' "
                "smentire - riclassificare esplicitamente come "
                "NOT_ENOUGH_EVIDENCE_AFTER_EXPERIMENT, seguendo lo stesso principio "
                "'mai forzare una conclusione' gia' applicato nelle fasi precedenti.",
        },

        "7_fix_acceptance_criteria_if_confirmed": {
            "explicit_separation": (
                "Tre domande DISTINTE, mai fuse: (a) VERIFICA DELL'IMPLEMENTAZIONE - "
                "il fix (guardia TF, stesso pattern di BREAKOUT_ACC riga "
                "'if(tf != NXS_Profile_TF(\"ORDER_BLOCK\")) return s;') elimina "
                "davvero la discrepanza A-vs-B? (b) VALIDITA' DELL'EVIDENZA - "
                "l'evidenza storica ESISTENTE su ORDER_BLOCK (se presente - il census "
                "non ne registra nel campo historical_tests) resta contaminata o va "
                "riclassificata? (c) REDDITIVITA' - NON INDAGATA, NON PRESUNTA: "
                "correggere il difetto NON implica che la strategia diventi o sia "
                "gia' profittevole - nessuna analisi di P&L e' prevista come criterio "
                "di accettazione del fix."
            ),
            "acceptance_gate": "Il fix e' accettabile SOLO se (a) e' provato "
                "equivalente in binario/compilazione dove non tocca la logica del "
                "TF-guard (stesso principio 'fix minimale' di Phase 7.9G), e (b) "
                "riproduce ESATTAMENTE la parita' same-feed gia' vista per BREAKOUT_ACC "
                "(idealmente 100% o quasi tra live post-fix e offline D1-isolato) - "
                "NON e' sufficiente che il fix 'sembri corretto' per analogia.",
        },

        "8_dependencies_and_blockers": [
            "AUTORIZZAZIONE ESPLICITA dell'utente per una nuova modifica EA live "
                "(standing rule del progetto: mai senza autorizzazione dedicata) - "
                "NON richiesta ne' presunta in questa fase, che si ferma alla "
                "PROGETTAZIONE del protocollo.",
            "Decisione non presa in questa fase: costruire un EA diagnostico "
                "STANDALONE separato (zero rischio, nessun tocco al codice live, come "
                "Phase 7.9E) vs. applicare direttamente una guardia di PROVA "
                "sull'EA live in un ramo/copia isolata - la prima strada e' piu' "
                "lenta da costruire (deve replicare zona/invalidazione/retest, non "
                "solo un cooldown) ma non richiede alcuna autorizzazione di modifica "
                "EA; la seconda e' piu' rapida ma richiede l'autorizzazione di cui "
                "sopra anche solo per un test diagnostico.",
            "Dipendenza da g_atr e g_structH1.trend (calcolati altrove nel router) - "
                "la ricostruzione offline (stream B) deve replicarli fedelmente o "
                "isolarli esplicitamente, altrimenti una discrepanza A-vs-B "
                "potrebbe riflettere una divergenza in QUESTE dipendenze esterne, "
                "non nel meccanismo g_obBuy/g_obSell in se'.",
            "Nessun blocker noto sui dati (stesso storico GOLD gia' verificato per "
                "BREAKOUT_ACC copre anche il periodo di ORDER_BLOCK).",
        ],

        "not_assumed": (
            "Non si presume che l'assenza di guardia TF produca necessariamente un "
            "effetto misurabile (vedi criterio di falsificazione), ne' che un "
            "eventuale fix crei un edge economico - queste sono domande "
            "SEPARATE e nessuna delle due e' pre-decisa da questo protocollo."
        ),
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE712_DIR, "diagnostic_protocol_order_block_v1.json"), doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    return doc


if __name__ == "__main__":
    main()
