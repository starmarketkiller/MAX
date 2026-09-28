#!/usr/bin/env python3
"""Phase 7.27 punto 1 - PARAMETRI PREREGISTRATI, congelati PRIMA di
calcolare qualunque risultato. Ogni altro modulo di questa fase importa
QUESTI valori - nessun altro file puo' ridefinire orizzonti/metriche/
benchmark autonomamente. Se un valore qui cambiasse DOPO aver visto un
risultato, sarebbe una violazione della preregistrazione (verificato:
il verificatore ricontrolla che nessun builder importi costanti locali
con lo stesso significato)."""

STRATEGIES_INCLUDED = ["BREAKOUT_ACC", "ORDER_BLOCK", "LIQ_SWEEP"]
# TSI escluso: nessun dataset economico, nessun evento BUY con P&L reale esiste.

DATASETS_USED = {
    "BREAKOUT_ACC": "BREAKOUT_ACC::2019.02.21_2026.06.09",
    "ORDER_BLOCK": "ORDER_BLOCK::2023.10.02_2026.08.24",
    "LIQ_SWEEP": "LIQ_SWEEP::2023.10.02_2026.06.30",
}
# Tutti e 3 sono dataset di DISCOVERY gia' esposti (Phase 7.21/7.22/7.24/7.25) - NESSUN vero
# holdout consumato per questa prima verifica della hypothesis (punto 7 del task).

PRICE_SOURCE = "server/research_scripts/phase7/phase7_9h/raw_data/nxs_d1_gold_phase79h.csv"
PRICE_SOURCE_NOTE = ("Serie D1 unica per tutte e 3 le strategie e i benchmark (2019.01.02-"
                     "2026.08.19) - garantisce granularita'/fonte identica, non introduce "
                     "differenze spurie fra strategie. Ricalcolo INDIPENDENTE degli eventi reali "
                     "(non riuso diretto di misure gia' pubblicate altrove, es. Phase 7.9K) per "
                     "coerenza metodologica con i benchmark.")

HORIZONS_D1_BARS = [1, 3, 5, 10, 20, 40, 60]  # stessi orizzonti gia' usati in Phase 7.9K per BREAKOUT_ACC
PRIMARY_HORIZON_D1_BARS = 10  # orizzonte di riferimento per la sintesi primaria - dichiarato qui,
                             # prima di calcolare qualunque confronto, non scelto a posteriori

METRICS = [
    "forward_return_price_units", "probability_of_favorable_outcome",
    "mfe_price_units", "mae_price_units", "time_to_mfe_bars", "time_to_mae_bars",
    "time_to_profit_bars", "adverse_excursion_before_favorable_movement",
]

BENCHMARKS = {
    "RANDOM_TIMESTAMPS_MATCHED": "N barre D1 casuali (stesso N del campione reale), entro lo "
        "stesso periodo/frequenza del dataset della strategia - seed dichiarato PRIMA del calcolo.",
    "UNCONDITIONAL_LONG_EXPOSURE": "Media su TUTTE le barre D1 disponibili nel periodo (nessun "
        "campionamento) - baseline 'sei semplicemente long' senza alcuna selezione di timing.",
    "PERIODIC_ENTRY_LONG": "Entry a intervalli fissi (ogni K barre, K tale che il conteggio atteso "
        "sia ~N) - deterministico, nessuna casualita'.",
    "REGIME_MATCHED_RANDOM_LONG": "Per ogni evento reale, un entry casuale nella STESSA barra di "
        "regime (trend x vol_tercile) ma NON nello stesso evento - stratificato, usa solo "
        "informazione disponibile al momento (trend/ATR trailing, mai barre future).",
    "BUY_AND_HOLD_MACRO_CONTEXT": "Rendimento dell'intero periodo in un solo colpo - riportato SOLO "
        "come contesto macro (drift secolare), MAI come confronto diretto trade-per-trade "
        "(istruzione esplicita del task).",
}

MATCHING_RULES = ("Ogni barra di benchmark (random/periodic/regime-matched) usa ESCLUSIVAMENTE "
                  "informazione disponibile AL MOMENTO di quella barra (trend/vol_tercile "
                  "trailing, mai calcolati con barre future) - stesso principio causale del "
                  "Pre-Entry Feature Store (Phase 7.26).")

EXCLUSION_RULES = ("Nessun evento escluso per performance (nessun cherry-picking) - inclusi TUTTI "
                  "i BUY reali di ciascuna strategia nel dataset di discovery. Eventi con "
                  "orizzonte che eccede i dati disponibili (fine serie) sono CENSURATI per quella "
                  "singola metrica/orizzonte (NOT_AVAILABLE), non esclusi dall'evento intero.")

MIN_SAMPLE_SIZE_CAVEAT = ("ORDER_BLOCK ha solo 12 eventi BUY - qualunque effect size su questo "
                         "campione e' descrittivo, non generalizzabile. Dichiarato PRIMA di "
                         "guardare i risultati, non dopo.")

RANDOM_SEED_BASE = 72700  # dichiarato prima di ogni campionamento - un seed diverso e deterministico
                         # per ogni strategia/benchmark, derivato da questo (vedi build_benchmark_samples.py)

N_BOOTSTRAP = 10000

PRIMARY_ANALYSIS = ("Confronto ALL orizzonti x REGIME_MATCHED_RANDOM_LONG (il benchmark piu' "
                    "rigoroso, l'unico che controlla esplicitamente per trend/volatilita') su "
                    "forward_return_price_units - questa e' l'analisi PRIMARIA per la decisione "
                    "finale. Tutti gli altri benchmark/metriche sono EXPLORATORY (punto 8 del "
                    "task) - riportati ma non usati da soli per la decisione.")

DECISION_ALLOWED = ["BUY_SELECTION_SIGNAL_SUPPORTED_AS_HYPOTHESIS",
                   "BUY_DOMINANCE_LARGELY_EXPLAINED_BY_MARKET_REGIME", "MIXED_EVIDENCE",
                   "INSUFFICIENT_EVIDENCE"]
