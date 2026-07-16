# Sweep 1-37 — passate pre-fix, round 2 (16/07 pomeriggio)

S01-S05 (ADX_RSI/BOLLINGER/MACD/SAR/TSI), compilate dopo il primo round di fix
(RecordExec, LIQ_SWEEP, ADX_RSI trigger nuovo, TP/breakeven MACD/ADX_RSI —
vedi `pre-fix-16-07/README.md`) ma **prima** del fix del cap di durata massima
piatto a 12h (`bced090`, confermato reale su ~25 strategie) e prima del fix
del log CSV chiusure (`5f44426`).

## Mappatura file → strategia
| File | InpStrategySelector | Strategia |
|---|---|---|
| SWEEP37_S01 | 1 | ADX_RSI |
| SWEEP37_S02 | 2 | BOLLINGER |
| SWEEP37_S03 | 3 | MACD |
| SWEEP37_S04 | 4 | SAR |
| SWEEP37_S05 | 5 | TSI |

Conservate per cronologia (non scartate) — confrontare con la versione
definitiva in `results/reports/sweep37/` (root) per isolare l'effetto del fix
del cap 12h.
