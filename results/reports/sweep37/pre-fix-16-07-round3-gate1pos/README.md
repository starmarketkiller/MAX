# Sweep 1-37 — passate pre-fix, round 3 (16/07 sera - 17/07 notte)

S01-S06 (ADX_RSI/BOLLINGER/MACD/SAR/TSI/BJORGUM), compilate al commit
`d8fa8c3` (dopo cap durata 12h `bced090`, prima del gate mancante). S06 è
completata e si è auto-pushata pochi secondi prima che riuscissi a fermare
il processo per il fix successivo - archiviata qui per lo stesso motivo.

## Cosa NON includono
Compilate **prima** di `3cba036` — Fix reale MQL5: gate "1 posizione per
strategia" mancante in DataCollectionMode. Trovato analizzando proprio
`NEXUS_trades.csv` di queste 5 passate: causa dominante, molto più
impattante del fix del cap 12h (che da solo non aveva cambiato i risultati
attesi). Vedi `[[NEXUS EA - Caccia al Bug Esecuzione (17-07)]]` nel vault
per il dettaglio dell'analisi.

## Mappatura file → strategia
| File | InpStrategySelector | Strategia |
|---|---|---|
| SWEEP37_S01 | 1 | ADX_RSI |
| SWEEP37_S02 | 2 | BOLLINGER |
| SWEEP37_S03 | 3 | MACD |
| SWEEP37_S04 | 4 | SAR |
| SWEEP37_S05 | 5 | TSI |
| SWEEP37_S06 | 6 | BJORGUM |

Conservate per cronologia — confrontare con la versione definitiva in
`results/reports/sweep37/` (root) per isolare l'effetto del fix del gate.
