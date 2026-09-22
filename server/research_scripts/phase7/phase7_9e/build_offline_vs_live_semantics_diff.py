#!/usr/bin/env python3
"""Phase 7.9E - punti 1-5: confronto esplicito del percorso di generazione
live vs le ricostruzioni offline (7.9C MQL5 + Python pre-esistente),
timing semantics, TF effettivo, semantica di stato, posizionamento del
gate HTF - e SOPRATTUTTO la scoperta empirica del meccanismo causale
reale (stato condiviso multi-TF), provata con due esperimenti diagnostici
dedicati (standalone, zero rischio, nessuna modifica all'EA live).
"""
import os
import sys

PHASE79E_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE79E_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import save_json, wrap_with_provenance  # noqa: E402

BASELINE_COMMIT = "ee469d4fa62a6c6aba8b228c16a422540e05c189"


def build():
    return {
        "phase": "7.9E", "candidate": "BREAKOUT_ACC", "baseline_commit": BASELINE_COMMIT,
        "no_strategy_modification": True, "no_optimization": True, "no_performance_analysis": True,
        "no_rescue": True, "no_live_ea_modification": True,

        "1_code_path_comparison": {
            "live_path": [
                "OnTick (NEXUS_EA_v2.mq5:1140)",
                "New Bar Gate su InpTFEntry=M15 (iTime(g_sym,M15,0), riga 1250-1252)",
                "NXS_CollectAllSignals (riga 1298) -> loop multi-TF su TUTTI i TF distinti "
                "del registro (M5/M15/M30/H1/H4/D1, da NXS_Profile_TF di OGNI strategia, non "
                "solo quelle abilitate dal selector)",
                "per ciascun pass: NXS_ActivateTF(tf) [crea/attiva 10 handle indicatori D1: "
                "ADX/RSI/BB/MACD/SAR/ATR/EMA200/EMA9/EMA21/Ichimoku, TUTTI non usati da "
                "BREAKOUT_ACC] -> NXS_CollectRaw(...) -> NXS_Strat_BreakoutAcc() [chiamata "
                "SEMPRE, indipendentemente dal TF del pass, perche' il suo gate "
                "NXS_SelectorAllows(9) non dipende dal TF attivo]",
                "dentro NXS_CollectRaw, righe 634-646: gate HTF per-profilo, px200=iClose(EffTF,0) "
                "[shift0, barra IN FORMAZIONE] vs g_ema200 [shift1, ultima barra chiusa del TF "
                "attivo]",
                "filtro NXS_Profile_TF(strat)==passes[p] (riga 710): tiene SOLO il risultato "
                "del pass D1 in out[]",
                "trace GENERATED (riga 1310-1314) emesso SOLO per i segnali sopravvissuti nel "
                "out[] finale",
            ],
            "offline_7_9c_path": [
                "CopyRates una tantum su tutta la finestra storica D1",
                "loop bar-per-bar SOLO su D1, nessun altro TF mai considerato",
                "stessa formula c1/c2/range (verificata identica riga-per-riga)",
                "cooldown/HTF applicati con stato dedicato SOLO a D1",
            ],
            "offline_python_path": [
                "sig_breakout_acc + _breakout_acc_cooldown_series (server/backtest.py) - "
                "stessa struttura: loop SOLO su D1, stato dedicato SOLO a D1",
            ],
            "explicit_diff": "L'unica differenza STRUTTURALE fra i tre percorsi non e' nella "
                "formula (identica ovunque, verificata) ne' nella cadenza di valutazione D1 "
                "(anch'essa identica, verificata sperimentalmente - vedi sezione 2) - e' che "
                "SOLO il percorso live condivide lo stato di cooldown (lastFireTime) FRA TUTTI "
                "i timeframe del registro, non solo D1. Nessuna delle due ricostruzioni offline "
                "replica questo, perche' nessuna delle due aveva motivo di saperlo prima di "
                "questa fase.",
        },

        "2_timing_semantics_verified_empirically": {
            "method": "EA diagnostico standalone (NXS_BreakoutAccCadenceDiagnostic.mq5, zero "
                "rischio, nessun ordine, nessuna inclusione di NEXUS_v1) eseguito nel VERO "
                "Tester (Model=1, stessa finestra 2019.02.03-2026.08.15) - replica fedele del "
                "New Bar Gate M15 + attivazione D1 con i 10 handle indicatori REALI del router.",
            "n_m15_passes": 177808, "n_activation_success": 177808, "n_activation_fail": 0,
            "n_new_d1_bar_detected_after_success": 1944,
            "conclusion": "La cadenza di valutazione D1 e' PERFETTA: ogni singola nuova barra "
                "D1 (1944 su 1944, verificato contro il conteggio reale di barre nella cache) "
                "viene correttamente rilevata e valutata dietro il New Bar Gate M15. "
                "EVALUATION_CADENCE_DIFFERENCE e' ESCLUSA come causa - non e' un problema di "
                "quando la funzione viene chiamata.",
            "shift_semantics_confirmed": "curBar0=iTime(D1,0) [shift0, barra appena aperta, "
                "trigger della valutazione], c1=iClose(D1,1) [shift1, barra appena chiusa], "
                "c2=iClose(D1,2) [shift2] - IDENTICI a quanto gia' replicato in 7.9C (verificato "
                "algebricamente in questa fase: la parametrizzazione ad array ascendente di "
                "7.9C, con la sostituzione I=i+1, coincide ESATTAMENTE con gli shift reali - "
                "NESSUN bug di indicizzazione trovato, contrariamente al sospetto iniziale).",
        },

        "3_effective_timeframe_semantics": {
            "NXS_EffTF_definition": "NXS_Globals.mqh:125-127: ritorna g_activeTF se diverso da "
                "PERIOD_CURRENT, altrimenti InpTFEntry. g_activeTF viene impostato da "
                "NXS_ActivateTF(tf) (NEXUS_EA_v2.mq5:225-233) ad OGNI pass del loop multi-TF.",
            "verified_in_diagnostic_run": "source_tf=PERIOD_D1 nel certificato reale (7.9D) - "
                "confermato che quando il segnale FINALE sopravvive (out[] dopo il filtro "
                "NXS_Profile_TF(strat)==passes[p]), il suo sourceTF e' sempre D1, come atteso. "
                "MA questo non implica che NXS_Strat_BreakoutAcc() sia MAI chiamata "
                "esclusivamente durante il pass D1 - il gate di selettore NON dipende dal TF "
                "attivo, quindi la funzione gira (e MUTA STATO CONDIVISO) anche durante i pass "
                "M5/M15/M30/H1/H4, il cui risultato viene poi scartato dal filtro TF - ma lo "
                "STATO GIA' MUTATO non viene scartato insieme al risultato.",
        },

        "4_state_semantics_audit": {
            "g_breakoutAccState": "NXS_Strategies.mqh:1531-1532 - struct GLOBALE UNICO "
                "(lastBarTime + lastFireTime[2]), NON scoped per-timeframe, condiviso da TUTTE "
                "le chiamate a NXS_Strat_BreakoutAcc() indipendentemente dal TF attivo al "
                "momento della chiamata.",
            "root_cause_identified": "NXS_Strat_BreakoutAcc() non verifica MAI se NXS_EffTF() "
                "corrisponde al proprio TF di profilo dichiarato (D1, NXS_Profile_TF) prima di "
                "leggere/scrivere g_breakoutAccState - viene invocata (e MUTA lo stato "
                "condiviso) durante OGNI pass multi-TF (M5/M15/M30/H1/H4/D1), usando barre/"
                "cooldown-in-secondi DI QUEL TF specifico. Un TF piu' veloce (es. H4, M30) che "
                "trova la propria 'Acceptance' sui SUOI bar aggiorna lastFireTime con un "
                "timestamp molto piu' recente - quando arriva (nello stesso o in un tick "
                "successivo) il pass D1 con un'Acceptance VERA e propria, il cooldown "
                "condiviso appare erroneamente ancora attivo.",
            "cooldown_clock_semantics": "cooldownSec = InpBreakoutAccCooldownBars(8) * "
                "PeriodSeconds(tf_ATTIVO) - quindi il 'significato' degli 8 giorni di cooldown "
                "cambia per ogni TF (8gg per D1, 8*4h=32h per H4, ecc.) MA lo stato che "
                "confronta e' lo STESSO array lastFireTime[2] - un cooldown 'H4' da 32 ore puo' "
                "quindi bloccare un'Acceptance D1 legittima che sarebbe stata valida da sola.",
        },

        "5_htf_gate_placement_and_counts": {
            "location_confirmed": "Il gate HTF (NEXUS_EA_v2.mq5:634-646) e' DENTRO "
                "NXS_CollectRaw(), PRIMA del ritorno a NXS_CollectAllSignals - usa g_ema200/"
                "NXS_EffTF() del pass CORRENTE (quindi D1-corretto durante il pass D1, "
                "verificato: non c'e' un bug di stale-M15-context come inizialmente sospettato).",
            "raw_acceptance_isolated_D1_only": 205,
            "post_cooldown_isolated_D1_only": 95,
            "post_htf_isolated_D1_only_shift0_semantics": 75,
            "post_cooldown_with_cross_tf_shared_state": 0,
            "real_ea_final_generated": 4,
            "conclusion": "Il gate HTF (anche con la semantica shift0 corretta, mai testata "
                "prima empiricamente) riduce solo modestamente (95->75, -21%) - "
                "HTF_TIMING_MISMATCH e' un contributo REALE ma MINORE, non dominante. Il "
                "crollo drammatico (95->0 nell'esperimento con stato condiviso) e' "
                "quasi interamente spiegato dalla contaminazione cross-timeframe dello stato "
                "(sezione 4) - il residuo fra 0 (esperimento semplificato) e 4 (EA reale) e' "
                "attribuibile a differenze nell'ORDINE esatto dei pass multi-TF nel registro "
                "reale (non riprodotto bit-per-bit in questo esperimento, che usa un ordine "
                "ragionevole ma non verificato contro NXS_StrategyIdAt) - non ulteriormente "
                "investigato in questa fase.",
        },

        "6_experiments_executed": {
            "experiment_A_cadence_isolated": {
                "script": "server/research_scripts/NXS_BreakoutAccCadenceDiagnostic.mq5",
                "description": "Replica fedele di cadenza (New Bar Gate M15 + attivazione D1 "
                    "con i 10 handle reali) MA con stato BREAKOUT_ACC isolato (solo D1 lo "
                    "tocca) - baseline di controllo.",
                "result": "raw=205 cooldown_pass=95 htf_pass=75 - STESSO ordine di grandezza "
                    "della stima offline 7.9C (80) - conferma che cadenza/attivazione/HTF NON "
                    "sono la causa dominante.",
            },
            "experiment_B_shared_state": {
                "script": "server/research_scripts/NXS_BreakoutAccSharedStateDiagnostic.mq5",
                "description": "Stessa cadenza, MA g_breakoutAccState CONDIVISO fra 6 pass "
                    "multi-TF (M5/M15/M30/H1/H4/D1) per ogni tick M15, esattamente come nel "
                    "router reale (NXS_Strat_BreakoutAcc chiamata ad ogni pass, nessun controllo "
                    "sul TF attivo).",
                "result": "D1 isolato (controllo, ripetuto nello stesso run)=95, D1 con stato "
                    "condiviso=0, altri TF che hanno toccato/sporcato lo stato condiviso=12234 "
                    "volte - collasso quasi totale, stessa direzione e ordine di grandezza del "
                    "gap osservato nella realta' (95/75 offline vs 4 EA reale).",
            },
        },
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE79E_DIR, "breakout_acc_live_vs_offline_semantics_diff_v1.json"), doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    return doc


if __name__ == "__main__":
    main()
