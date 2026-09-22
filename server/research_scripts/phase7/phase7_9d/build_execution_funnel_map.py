#!/usr/bin/env python3
"""Phase 7.9D - punto 1: mappa STATICA (da codice sorgente, nessuna
esecuzione) del funnel completo signal_fire -> stato terminale per
BREAKOUT_ACC.

BREAKOUT_ACC gira in Research Mode con InpUseStrategyProfiles=true (
richiesto da NXS_ResearchPreflight) -> il router che la governa e'
SEMPRE il branch "PROFILI PER-STRATEGIA" (NEXUS_EA_v2.mq5 righe
~1498-1566), MAI DataCollection/Institutional/Legacy (mutuamente
esclusivi via early return). Ogni gate qui sotto e' gia' collegato al
sistema esistente 'Decision/Gate/Execution Trace v1' (NXS_Trace.mqh,
aggiunto 12/09, NON modificato in questa fase) - questo script non
scrive nuova osservabilita', la legge e la documenta.
"""
import os
import sys

PHASE79D_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE79D_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import save_json, wrap_with_provenance  # noqa: E402

BASELINE_COMMIT = "6b16c09c9bc8d5184cef35e2e2d100161a6d4c00"

# Ordine ESATTO di valutazione nel codice reale (router "profili per-strategia",
# poi NXS_OpenTrade, poi NXS_CommonExposurePreflight) - un segnale che supera
# uno step passa al successivo, un segnale bloccato termina li'.
FUNNEL_STEPS = [
    {"step": 1, "function": "NXS_CollectAllSignals -> NXS_Strat_BreakoutAcc",
     "file": "MQL5/Include/NEXUS_v1/NXS_Strategies.mqh", "line_range": "1534-1564",
     "condition": "setup (range 20 barre) + trigger (doppia chiusura consecutiva oltre il range, "
                 "'Acceptance') + cooldown per-direzione (8 barre, in SECONDI di calendario) + "
                 "gate HTF nativo (via NXS_Profile_HTF applicato piu' sotto, non qui)",
     "trace_stage": "TRACE_GENERATED", "trace_call": "NXS_Trace_Generated (NEXUS_EA_v2.mq5:1313)",
     "note": "Questo e' il momento equivalente al 'SIGNAL_FIRE' del diagnostic script read-only "
             "di 7.9C (NXS_BreakoutAccSignalDiagnostic.mq5) - MA li' il gate HTF era gia' incluso "
             "nel conteggio finale; qui invece il gate HTF (riga sotto, step 1b) e' un passo "
             "SEPARATO del router, applicato DOPO la generazione grezza. Per confronto diretto con "
             "lo stream 7.9C, il vero equivalente di 'SIGNAL_FIRE' e' il segnale che supera "
             "ANCHE lo step 1b sotto."},
    {"step": "1b", "function": "router: applicazione profilo HTF su out[]",
     "file": "MQL5/Experts/NEXUS_EA_v2.mq5", "line_range": "634-646",
     "condition": "se InpUseStrategyProfiles e il profilo della strategia ha htf=true (vero per "
                 "BREAKOUT_ACC) e g_ema200>0: scarta (dir=DIR_NONE) i segnali controtrend "
                 "rispetto a px200 = close(TF effettivo, shift0) vs EMA200(shift1)",
     "trace_stage": "nessuno - il segnale scartato qui non genera MAI una riga GENERATED "
                    "(l'array out[] e' gia' filtrato prima del loop di trace a NEXUS_EA_v2.mq5:1310-1314)",
     "gap_declared": "GATE_HTF applicato PRIMA del trace loop non produce una riga BLOCKED "
                    "esplicita per-segnale - e' invisibile al funnel accounting invariante "
                    "(punto 5 dell'istruzione 7.9D). Dichiarato qui esplicitamente, non nascosto: "
                    "il conteggio n_blocked_htf del diagnostic script 7.9C resta l'UNICA fonte "
                    "diretta per questo gate specifico."},
    {"step": 2, "function": "router 'profili per-strategia': overlap_only",
     "file": "MQL5/Experts/NEXUS_EA_v2.mq5", "line_range": "1517-1520",
     "condition": "InpProfileOverlapOnly (default false) && sessione != OVERLAP",
     "trace_stage": "TRACE_BLOCKED", "gate_reason": "GATE_PROTECTIONS", "detail": "overlap_only",
     "expected_active": False, "note": "default OFF - non atteso attivo in questo run"},
    {"step": 3, "function": "router 'profili per-strategia': one-position-per-strategy",
     "file": "MQL5/Experts/NEXUS_EA_v2.mq5", "line_range": "1521-1526",
     "condition": "NXS_StrategyHasOpenPos(stratName) - vero se BREAKOUT_ACC ha gia' una posizione "
                 "aperta (nessun limite di durata qui: dura finche' quella posizione non si chiude "
                 "per SL/TP/MaxHold)",
     "trace_stage": "TRACE_BLOCKED", "gate_reason": "GATE_OPEN_POSITION", "detail": "",
     "hypothesis_role": "Il gate diretto dietro l'ipotesi 'one-position' della 7.9C (che la "
                        "stimava ~40/80 con una simulazione NAIVE offline) - qui viene misurato "
                        "REALMENTE dal motore, non stimato."},
    {"step": 4, "function": "router 'profili per-strategia': one-decision-per-tf-bar",
     "file": "MQL5/Experts/NEXUS_EA_v2.mq5", "line_range": "1527-1535",
     "condition": "stessa barra D1 gia' processata per questa strategia (NXS_GetLastTfBar)",
     "trace_stage": "TRACE_BLOCKED", "gate_reason": "GATE_TF_GATE", "detail": "one_decision_per_tf_bar",
     "expected_active": False, "note": "il New Bar Gate upstream (OnTick, riga 1249-1252) gia' "
                                       "impedisce piu' valutazioni sulla stessa barra M15/D1 - "
                                       "atteso raramente o mai attivo per questo motivo"},
    {"step": 5, "function": "router 'profili per-strategia': SL/TP di profilo",
     "file": "MQL5/Experts/NEXUS_EA_v2.mq5", "line_range": "1536-1540",
     "condition": "NXS_DefaultSLTP fallisce a produrre SL/TP validi",
     "trace_stage": "TRACE_BLOCKED", "gate_reason": "GATE_INVALID_STOPS", "detail": "no_sltp_after_default",
     "expected_active": False},
    {"step": 6, "function": "NXS_OpenTrade: strategia nota", "file": "MQL5/Include/NEXUS_v1/NXS_Execution.mqh",
     "line_range": "314-319", "condition": "NXS_StrategyKnown fallisce (mai per BREAKOUT_ACC, nome nel registro)",
     "trace_stage": "TRACE_BLOCKED", "gate_reason": "GATE_UNKNOWN_STRATEGY", "expected_active": False},
    {"step": 7, "function": "NXS_OpenTrade: ruin freeze", "file": "MQL5/Include/NEXUS_v1/NXS_Execution.mqh",
     "line_range": "320-325", "condition": "NXS_RuinFrozen() (scudo risk-of-ruin, opt-in "
     "InpResearchUseRuin=false in questo run -> NXS_Ruin_OnTick non gira, non puo' congelare)",
     "trace_stage": "TRACE_BLOCKED", "gate_reason": "GATE_PROTECTIONS", "detail": "ruin_frozen",
     "expected_active": False},
    {"step": 8, "function": "NXS_OpenTrade: profilo abilitato", "file": "MQL5/Include/NEXUS_v1/NXS_Execution.mqh",
     "line_range": "326-332", "condition": "NXS_Profile_Enabled(stratName) falso (BREAKOUT_ACC "
     "abilitata di default nel profilo)", "trace_stage": "TRACE_BLOCKED", "gate_reason": "GATE_PROFILE_DISABLED",
     "expected_active": False},
    {"step": 9, "function": "NXS_OpenTrade: regime veto", "file": "MQL5/Include/NEXUS_v1/NXS_Execution.mqh",
     "line_range": "333-343", "condition": "InpProfileRegimeVeto (default false in questo run/.set)",
     "trace_stage": "TRACE_BLOCKED", "gate_reason": "GATE_PROTECTIONS", "detail": "regime_veto",
     "expected_active": False},
    {"step": 10, "function": "NXS_OpenTrade: TF gate", "file": "MQL5/Include/NEXUS_v1/NXS_Execution.mqh",
     "line_range": "344-356", "condition": "bypassato in InpProfileMultiTF=true (garantito dal "
     "collector a monte)", "trace_stage": "TRACE_BLOCKED", "gate_reason": "GATE_TF_GATE",
     "expected_active": False},
    {"step": 11, "function": "NXS_OpenTrade: dashboard disable", "file": "MQL5/Include/NEXUS_v1/NXS_Execution.mqh",
     "line_range": "357-364", "condition": "NXS_Runtime_StrategyBlocked (dashboard remota, non "
     "usata in un run Tester offline)", "trace_stage": "TRACE_BLOCKED", "gate_reason": "GATE_PROFILE_DISABLED",
     "expected_active": False},
    {"step": 12, "function": "NXS_OpenTrade: bar_dir_cap", "file": "MQL5/Include/NEXUS_v1/NXS_Execution.mqh",
     "line_range": "365-376", "condition": "InpMaxNewTradesPerBarDir=8 default - irraggiungibile "
     "con al piu' 1 segnale BREAKOUT_ACC per barra", "trace_stage": "TRACE_BLOCKED", "gate_reason": "GATE_EXPOSURE",
     "detail": "bar_dir_cap", "expected_active": False},
    {"step": 13, "function": "NXS_OpenTrade: setup_matrix_cap (InpMaxPerDirTF)",
     "file": "MQL5/Include/NEXUS_v1/NXS_Execution.mqh", "line_range": "377-426",
     "condition": "InpMaxPerDirTF=4 default - con una sola strategia attiva (selector=9) e il gate "
                 "one-position-per-strategy (step 3) gia' a monte, questo cap non puo' mai essere "
                 "raggiunto da BREAKOUT_ACC da sola",
     "trace_stage": "TRACE_BLOCKED", "gate_reason": "GATE_EXPOSURE", "detail": "setup_matrix_cap",
     "expected_active": False},
    {"step": 14, "function": "NXS_OpenTrade: post_sl_cooldown", "file": "MQL5/Include/NEXUS_v1/NXS_Execution.mqh",
     "line_range": "427-436", "condition": "InpPostSLCooldownMin - cooldown generico post-SL, "
     "indipendente dal cooldown NATIVO di BREAKOUT_ACC (gia' nello step 1)",
     "trace_stage": "TRACE_BLOCKED", "gate_reason": "GATE_COOLDOWN", "detail": "post_sl_cooldown",
     "expected_active": "sconosciuto - dipende dal default di InpPostSLCooldownMin, non "
                        "esplicitamente azzerato in questo .ini: possibile causa REALE aggiuntiva, "
                        "misurata direttamente dal run, non assunta"},
    {"step": 15, "function": "NXS_OpenTrade: exhaustion", "file": "MQL5/Include/NEXUS_v1/NXS_Execution.mqh",
     "line_range": "437-445", "condition": "NXS_ExhaustionBlocks (prezzo troppo esteso da EMA200)",
     "trace_stage": "TRACE_BLOCKED", "gate_reason": "GATE_PROTECTIONS",
     "expected_active": "sconosciuto - misurato direttamente dal run"},
    {"step": 16, "function": "NXS_OpenTrade: Elliott filter", "file": "MQL5/Include/NEXUS_v1/NXS_Execution.mqh",
     "line_range": "446-458", "condition": "InpUseElliottFilter && NXS_Profile_UseElliott(stratName) "
     "- opt-in per strategia, BREAKOUT_ACC non tra le 20 validate il 25/08 (da verificare nel "
     "profilo) -> atteso inattivo", "trace_stage": "TRACE_BLOCKED", "gate_reason": "GATE_PROTECTIONS",
     "detail": "elliott_wave_exhaustion", "expected_active": False},
    {"step": 17, "function": "NXS_OpenTrade: invalid_sl_distance", "file": "MQL5/Include/NEXUS_v1/NXS_Execution.mqh",
     "line_range": "459-465", "condition": "slDist<=0 (mai atteso: SL gia' validato allo step 5)",
     "trace_stage": "TRACE_BLOCKED", "gate_reason": "GATE_INVALID_STOPS", "expected_active": False},
    {"step": 18, "function": "NXS_OpenTrade: lot_calc_zero", "file": "MQL5/Include/NEXUS_v1/NXS_Execution.mqh",
     "line_range": "467-488", "condition": "Research Mode -> lotto fisso NXS_ResearchLot() "
     "(InpResearchFixedLot=0.01, sempre >0 se il simbolo ha volume minimo <=0.01)",
     "trace_stage": "TRACE_BLOCKED", "gate_reason": "GATE_MARGIN", "detail": "lot_calc_zero",
     "expected_active": False},
    {"step": 19, "function": "NXS_CommonExposurePreflight: licenza", "file": "MQL5/Include/NEXUS_v1/NXS_Execution.mqh",
     "line_range": "68-71", "condition": "NXS_License_Enforce", "trace_stage": "TRACE_BLOCKED",
     "gate_reason": "GATE_LICENSE", "expected_active": False, "note": "licenza valida in ambiente demo/test"},
    {"step": 20, "function": "NXS_CommonExposurePreflight: ruin freeze (ridondante)",
     "file": "MQL5/Include/NEXUS_v1/NXS_Execution.mqh", "line_range": "77-80",
     "condition": "stesso di step 7, verificato due volte per costruzione (nessun path bypassabile)",
     "trace_stage": "TRACE_BLOCKED", "gate_reason": "GATE_PROTECTIONS", "expected_active": False},
    {"step": 21, "function": "NXS_CommonExposurePreflight: protezioni giornaliere",
     "file": "MQL5/Include/NEXUS_v1/NXS_Execution.mqh", "line_range": "82-85",
     "condition": "NXS_Prot_EntryBlocked() - protezioni ESL/DailyDD/TotalDD/DPT tutte opt-in=false "
                 "in questo run -> atteso non bloccante, MA la pausa/altre protezioni strutturali "
                 "vanno verificate nel run reale, non assunte",
     "trace_stage": "TRACE_BLOCKED", "gate_reason": "GATE_PROTECTIONS", "detail": "protections_block",
     "expected_active": "sconosciuto - misurato direttamente"},
    {"step": 22, "function": "NXS_CommonExposurePreflight: hard stop presente",
     "file": "MQL5/Include/NEXUS_v1/NXS_Execution.mqh", "line_range": "87-98",
     "condition": "sl<=0 (mai atteso, gia' garantito dallo step 5/17)",
     "trace_stage": "TRACE_BLOCKED", "gate_reason": "GATE_INVALID_STOPS", "expected_active": False},
    {"step": 23, "function": "NXS_CommonExposurePreflight: stato incerto (ledger/state/indicatori/VSL)",
     "file": "MQL5/Include/NEXUS_v1/NXS_Execution.mqh", "line_range": "100-145",
     "condition": "ledger degradato / snapshot non ripristinato / indicatori illeggibili / VSL non "
                 "persistibile - improbabile in un run Tester pulito senza riavvii",
     "trace_stage": "TRACE_BLOCKED", "gate_reason": "GATE_STATE_UNCERTAIN", "expected_active": False},
    {"step": 24, "function": "NXS_CommonExposurePreflight: RiskShield", "file": "MQL5/Include/NEXUS_v1/NXS_Execution.mqh",
     "line_range": "147-154", "condition": "NXS_RS_BlockEntry (breaker Sharpe PER STRATEGIA - "
     "InpResearchUseRiskShield non impostato esplicitamente in questo .ini, default da verificare)",
     "trace_stage": "TRACE_BLOCKED", "gate_reason": "GATE_RISKSHIELD",
     "expected_active": "sconosciuto - misurato direttamente, possibile causa reale se il "
                        "breaker Sharpe e' attivo di default anche in Research Mode"},
    {"step": 25, "function": "NXS_CommonExposurePreflight: cap esposizione direzionale",
     "file": "MQL5/Include/NEXUS_v1/NXS_Execution.mqh", "line_range": "156-168",
     "condition": "existing+lots > InpMaxDirExposureLots - con lotto fisso 0.01 e una sola "
                 "strategia, irraggiungibile in pratica salvo default molto stretti",
     "trace_stage": "TRACE_BLOCKED", "gate_reason": "GATE_EXPOSURE", "expected_active": "improbabile"},
    {"step": 26, "function": "NXS_CommonExposurePreflight: margine proiettato",
     "file": "MQL5/Include/NEXUS_v1/NXS_Execution.mqh", "line_range": "170-190",
     "condition": "InpUseMarginGate && proiezione equity/margine < InpMinMarginLevelPct - con "
                 "Deposit=10000 e lotto 0.01 su GOLD, margine trascurabile: atteso non bloccante",
     "trace_stage": "TRACE_BLOCKED", "gate_reason": "GATE_MARGIN", "expected_active": False},
    {"step": 27, "function": "NXS_CommonExposurePreflight: preflight broker",
     "file": "MQL5/Include/NEXUS_v1/NXS_Execution.mqh", "line_range": "192-208",
     "condition": "NXS_PreFlight - spread/stop-level/lot bounds del simbolo/broker reale",
     "trace_stage": "TRACE_BLOCKED", "gate_reason": "variabile (NXS_GateReasonFromFailure)",
     "expected_active": "sconosciuto - dipende dai vincoli reali del simbolo GOLD nel Tester"},
    {"step": 28, "function": "NXS_OpenTrade: OrderSend", "file": "MQL5/Include/NEXUS_v1/NXS_Execution.mqh",
     "line_range": "successivo al preflight (NXS_SafeBuy/NXS_SafeSell)",
     "condition": "invio ordine al broker/simulatore - esito OPENED o BROKER_REJECT",
     "trace_stage": "TRACE_OPENED / TRACE_BROKER_REJECT", "gate_reason": "GATE_OPENED / GATE_BROKER_REJECT"},
]


def build():
    return {
        "phase": "7.9D", "candidate": "BREAKOUT_ACC", "baseline_commit": BASELINE_COMMIT,
        "execution_path_used": "PROFILI_PER_STRATEGIA",
        "execution_path_evidence": "InpUseStrategyProfiles=true e' un requisito FAIL-FAST di "
            "NXS_ResearchPreflight per InpResearchMode=true (NXS_ResearchMode.mqh:63-68) - "
            "DataCollection/Institutional sono esplicitamente incompatibili con Research Mode "
            "(stesso file, righe 48-56), quindi il branch 'profili per-strategia' "
            "(NEXUS_EA_v2.mq5:1506-1566) e' l'UNICO percorso possibile per questo run, non un'ipotesi.",
        "instrumentation_source": "Decision/Gate/Execution Trace v1 (NXS_Trace.mqh) + Test "
            "Validity Certificate v2 (NXS_TestValidityCertificate.mqh) - entrambi PREESISTENTI "
            "(aggiunti 12/09), NESSUNA modifica in questa fase. g_nxsTraceActive = "
            "NXS_IsResearchMode(), quindi il trace e' attivo per costruzione in questo run.",
        "funnel_steps": FUNNEL_STEPS,
        "terminal_states_declared": [
            "OPENED", "BLOCKED_OPEN_POSITION", "BLOCKED_COOLDOWN", "BLOCKED_PROTECTIONS",
            "BLOCKED_RISKSHIELD", "BLOCKED_SPREAD", "BLOCKED_MARGIN", "BLOCKED_INVALID_STOPS",
            "BLOCKED_EXPOSURE", "BLOCKED_TF_GATE", "BLOCKED_PROFILE_DISABLED", "BLOCKED_LICENSE",
            "BLOCKED_STATE_UNCERTAIN", "BLOCKED_UNKNOWN_STRATEGY", "BROKER_REJECT", "UNKNOWN",
        ],
        "terminal_state_mapping_note": "Mappatura diretta sull'enum GIA' esistente "
            "ENUM_NXS_GATE_REASON (NXS_Trace.mqh) invece di inventarne uno nuovo, come "
            "esplicitamente permesso dall'istruzione 7.9D punto 3 ('non forzare il codice nei "
            "nomi sopra se esistono categorie piu' precise').",
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE79D_DIR, "breakout_acc_execution_funnel_v1.json"), doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(f"funnel_steps={len(payload['funnel_steps'])}")
    return doc


if __name__ == "__main__":
    main()
