# Sweep 1-37 — passate pre-fix (16/07 mattina)

Prime 4 passate dello sweep 1-37 (DataCollectionMode, GOLD M15, 2019.07.11-2025.07.11),
eseguite con l'EA compilato al commit `92aa96b` (merge di
`claude/export-advisor-nexus-migrate-htnz34` con l'input nativo di
`InpStrategySelector`, ma **prima** di due round di fix successivi lo stesso
giorno).

## Cosa NON includono questi dati
Compilate prima di:
- `53d15be` — fix RecordExec mancante nel path DataCollectionMode: il contatore
  `executed`/`exec_rate_pct`/`health` era inutilizzabile in questa modalità
  specifica in questi 4 file (le colonne `wins`/`losses` restano invece
  affidabili, lette dallo storico deal indipendentemente dal bug).
- Fix reale su LIQ_SWEEP (sweep generico → `NXS_DetectSweepExt`, ICT vero, +
  filtro "delivery candle").
- Fix reale su ADX_RSI (trigger MQL5 nuovo, mai testato prima su MT5) e TP
  largo/breakeven per MACD/ADX_RSI (`9f9ab2e`).

## Mappatura file → strategia
| File | InpStrategySelector | Strategia |
|---|---|---|
| SWEEP37_S01_..._stats.csv | 1 | ADX_RSI |
| SWEEP37_S02_..._stats.csv | 2 | BOLLINGER |
| SWEEP37_S03_..._stats.csv | 3 | MACD |
| SWEEP37_S04_..._stats.csv | 4 | SAR |

## Perché sono conservati (non scartati)
Danno la cronologia esatta di cosa produceva il codice **prima** dei fix del
16/07 — utile per confermare (o smentire) che un fix abbia davvero cambiato il
comportamento, confrontando pass-per-pass con la versione post-fix in
`results/reports/sweep37/` (senza sottocartella). **BOLLINGER e SAR (S02, S04)
non sono toccate da nessuno dei fix di questo round — dati confrontabili
direttamente**, non solo storico.
