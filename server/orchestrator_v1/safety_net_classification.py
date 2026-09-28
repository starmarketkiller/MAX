#!/usr/bin/env python3
"""NEXUS TASK #0002 - tabella di classificazione FATTUALE (Fase 3 del task).

Ogni voce e' il risultato di un'ISPEZIONE REALE degli artifact del repository
(fatta da Claude in ruolo di supervisore/TIER0, non un'invenzione) - per ogni
campo NOT_AVAILABLE nel Cross-Strategy Learning Packet, si dichiara se il
dato grezzo necessario esiste gia' altrove (DERIVABLE_NOW, con la fonte
esatta) o se manca davvero (REQUIRES_NEW_DATA, con la ragione strutturale).

Nessun campo qui e' stato classificato REQUIRES_SCIENTIFIC_JUDGMENT o
SOURCE_CONFLICT in questo giro - non perche' non cercati, ma perche' NESSUNO
dei gap trovati richiede una decisione interpretativa: sono o calcoli
meccanici gia' derivabili da dati esistenti, o dati grezzi che semplicemente
non sono mai stati raccolti (regime/volatility/session per-trade tagging,
bar-level MFE/MAE per ORDER_BLOCK/TSI, l'intero dataset economico per TSI).
Questo e' un risultato onesto di QUESTO giro di backfill, non un limite
dell'impalcatura di classificazione (che resta pronta a gestire quei casi
quando si presenteranno)."""

NOT_AVAILABLE_INVENTORY = {
    "BREAKOUT_ACC": ["pre_entry_context", "regime", "volatility", "trend", "session",
                    "favorable_before_loss", "adverse_before_win", "execution_degradation",
                    "exit_efficiency", "temporal_concentration"],
    "ORDER_BLOCK": ["pre_entry_context", "regime", "volatility", "trend", "session",
                   "winner_anatomy", "loser_anatomy", "mfe_mae", "time_to_mfe_mae",
                   "favorable_before_loss", "adverse_before_win", "exit_efficiency",
                   "temporal_concentration"],
    "TSI": ["pre_entry_context", "regime", "direction", "volatility", "trend", "structure",
           "session", "level_context", "winner_anatomy", "loser_anatomy", "mfe_mae",
           "time_to_mfe_mae", "favorable_before_loss", "adverse_before_win",
           "execution_degradation", "cost_sensitivity", "exit_efficiency",
           "capital_efficiency", "concentration", "temporal_concentration", "oos_behavior"],
    "LIQ_SWEEP": ["volatility", "trend"],
}

CLASSIFICATION = {
    ("BREAKOUT_ACC", "temporal_concentration"): {
        "classification": "DERIVABLE_NOW",
        "rationale": "Gia' calcolato e verificato indipendentemente in NEXUS TASK #0001 "
                   "(worker locale ministral-3:3b, verifica di riferimento separata) - mai "
                   "propagato nel Learning Packet.",
        "source_artifacts": ["server/orchestrator_v1/nexus_task_0001_result_v1.json",
                            "server/research_scripts/phase7/phase7_28/"
                            "nexus0001_result_breakout_acc_temporal_v1.json"],
    },
    ("BREAKOUT_ACC", "exit_efficiency"): {
        "classification": "DERIVABLE_NOW",
        "rationale": "Come sopra - NEXUS TASK #0001.",
        "source_artifacts": ["server/research_scripts/phase7/phase7_28/"
                            "nexus0001_result_breakout_acc_exitfx_v1.json"],
    },
    ("BREAKOUT_ACC", "execution_degradation"): {
        "classification": "DERIVABLE_NOW",
        "rationale": "Bug di key-path trovato nel builder originale "
                   "(build_cross_strategy_learning_packet.py riga 96: cerca la chiave piatta "
                   "'signal_pct_favorable' che non e' mai esistita - il dato reale e' nidificato "
                   "sotto 'signal_edge'->'pct_favorable') - i funnel_counts grezzi ESISTONO gia' "
                   "in execution_realism_v1.json, solo mai convertiti in funnel_rates (a "
                   "differenza di ORDER_BLOCK/LIQ_SWEEP, il cui artifact sorgente aveva gia' "
                   "'funnel_rates' calcolato). Calcolo qui SOLO aritmetica pura sui contatori "
                   "gia' presenti, stessa formula/convenzione di ORDER_BLOCK.",
        "source_artifacts": ["server/research_scripts/phase7/phase7_21/execution_realism_v1.json"],
    },
    ("BREAKOUT_ACC", "favorable_before_loss"): {
        "classification": "DERIVABLE_NOW",
        "rationale": "breakout_acc_path_anatomy_v2.json (phase7_9k) ha gia' MFE/MAE per-evento "
                   "(per event_id) - mai incrociato con l'esito vinto/perso (net_pnl) del "
                   "dataset economico (phase7_21) per separare la MFE media dei trade PERDENTI. "
                   "Join+media aritmetica pura su due artifact gia' esistenti e verificati, "
                   "nessun nuovo dato.",
        "source_artifacts": ["server/research_scripts/phase7/phase7_9k/"
                            "breakout_acc_path_anatomy_v2.json",
                            "server/research_scripts/phase7/phase7_21/"
                            "nxs_breakoutacc_dataset_loader.py"],
    },
    ("BREAKOUT_ACC", "adverse_before_win"): {
        "classification": "DERIVABLE_NOW",
        "rationale": "Come sopra, MAE media dei trade VINCENTI.",
        "source_artifacts": ["server/research_scripts/phase7/phase7_9k/"
                            "breakout_acc_path_anatomy_v2.json",
                            "server/research_scripts/phase7/phase7_21/"
                            "nxs_breakoutacc_dataset_loader.py"],
    },
    ("ORDER_BLOCK", "temporal_concentration"): {
        "classification": "DERIVABLE_NOW",
        "rationale": "NEXUS TASK #0001.",
        "source_artifacts": ["server/research_scripts/phase7/phase7_28/"
                            "nexus0001_result_order_block_temporal_v1.json"],
    },
    ("ORDER_BLOCK", "exit_efficiency"): {
        "classification": "DERIVABLE_NOW",
        "rationale": "NEXUS TASK #0001.",
        "source_artifacts": ["server/research_scripts/phase7/phase7_28/"
                            "nexus0001_result_order_block_exitfx_v1.json"],
    },
}

# Tutti gli altri campi NOT_AVAILABLE (non elencati sopra) sono REQUIRES_NEW_DATA - la
# ragione strutturale e' UNA delle 3 seguenti, verificata per ricerca reale nel repository
# (nessun artifact equivalente trovato per queste strategie/campi):
STRUCTURAL_REASONS_REQUIRES_NEW_DATA = {
    "PER_TRADE_MARKET_CONTEXT_TAGGING_MISSING": {
        "fields": ["pre_entry_context", "regime", "volatility", "trend", "session",
                  "structure", "level_context", "direction"],
        "reason": "Nessuna pipeline di tagging del contesto di mercato per-trade "
                 "(regime/volatilita'/sessione all'entry) esiste per NESSUNA delle 4 "
                 "strategie - verificato con ricerca nel repository (nessun artifact "
                 "trovato). Richiede sia nuovo calcolo SIA una scelta metodologica su come "
                 "definire 'regime'/'trending' - segnalato esplicitamente nella proposta di "
                 "task futura.",
    },
    "BAR_LEVEL_MFE_MAE_INSTRUMENTATION_MISSING": {
        "fields": ["winner_anatomy", "loser_anatomy", "mfe_mae", "time_to_mfe_mae",
                  "favorable_before_loss", "adverse_before_win"],
        "reason": "Richiede dati OHLC a livello di barra per ogni trade (per calcolare MFE/"
                 "MAE) - l'engine generico esiste gia' (nxs_path_anatomy_engine.py, Phase "
                 "7.26.F) ma nessun artifact con questi dati grezzi esiste per ORDER_BLOCK o "
                 "TSI (verificato con ricerca - solo BREAKOUT_ACC e LIQ_SWEEP li hanno).",
    },
    "TSI_NO_ECONOMIC_DATASET": {
        "fields": None,  # tutti i restanti campi TSI
        "reason": "TSI non ha MAI avuto un dataset economico trade-per-trade come le altre 3 "
                 "strategie (verificato - nessun file trovato) - il filone di ricerca TSI "
                 "esistente riguarda un difetto di contaminazione cross-timeframe "
                 "(DEFECT_CONFIRMED_MATERIAL_IMPACT, Phase 7.17/7.18), non un backtest "
                 "economico pulito. L'evidenza storica e' inoltre dichiarata "
                 "PARTIALLY_COMPROMISED_FOR_MT5_REAL_TICK_RESULTS - usarla per calcolare "
                 "metriche economiche violerebbe esplicitamente la regola 'non reinterpretare "
                 "vecchi risultati' di questa stessa task.",
    },
}
