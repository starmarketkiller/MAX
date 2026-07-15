---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: ELLIOTT
created: 2026-07-15
updated: 2026-07-15
---

# Strategia: ELLIOTT

## Tipo
Wave counting / continuazione e reversal

## Trigger meccanico
Conteggio meccanico delle onde di Elliott su pivot swing alternati (fino a 8,
via `NXS_IsSwingHigh`/`NXS_IsSwingLow`): entra in continuazione a fine onda 2
(per onda 3) e fine onda 4 (per onda 5) su ritracciamento Fibonacci nella
zona configurata (`InpEllRetraceMin/Max`), o in reversal a fine onda 5
(impulso completo di 5 onde) puntando al 50% di ritracciamento. Target onda 3
= proiezione 1.618, target onda 5 continuazione ≈ ampiezza onda1-3.

## Scoperta 15/07
**37ª strategia dell'EA** (`NXS_Strategies_Elliott.mqh`, commento esplicito
"strategia #37") — non era mai stata tracciata in questo vault (mancava da
[[MOC - Strategie]] e non aveva una scheda propria), probabilmente perché
la lista storica di riferimento era "36 strategie". Trovata durante
[[NEXUS EA - Audit Fedeltà Trigger (tutte le 37 strategie)]]: il trigger è
sofisticato e coerente col nome (non un proxy o un mismatch).

## Configurazione attuale
Non presente in `NXS_StrategyProfiles.mqh` (verificare se ha un profilo
SL/TP dedicato o usa i default globali). **Non presente sul motore sito** —
nessuna delle `sig_*` in `backtest.py` la implementa, quindi non è
screenabile lì, solo isolabile su MT5 (`InpStrategySelector`).

## Risultati
**Nessun dato ancora raccolto** — non è mai stata inclusa nell'analisi del
backtest 10y segmentato né nello screening sito. Da aggiungere al prossimo
giro di analisi trade-level.

## Stato
🔬 Non tracciata finora — dato mancante, non "cattivo". Priorità: verificare
se è abilitata di default (`InpUseStrat_Elliott`) e se ha generato trade nei
segmenti 10y già arrivati (controllare le `_stats.csv`, riga "ELLIOTT").

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Audit Fedeltà Trigger (tutte le 37 strategie)]]
