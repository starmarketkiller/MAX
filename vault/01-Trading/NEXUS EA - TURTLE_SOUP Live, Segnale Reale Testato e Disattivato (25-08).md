---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, turtle-soup, mql5, ricerca-da-zero, rifiutata
created: 2026-08-25
updated: 2026-08-25
---

# NEXUS EA — TURTLE_SOUP live: segnale reale testato da zero e disattivato (25/08)

## Perché

Scoperto durante la verifica del trailing che il segnale live
`NXS_Strat_TurtleSoup` (sweep PDH/PDL/EQH/EQL + candela di rientro,
stop nativo, RR2.0 fisso) è **completamente diverso** dal pattern
Python `bt.STRATEGIES['TURTLE_SOUP']` usato in tutta la sessione dei
giorni scorsi — condividono solo il nome. Prima ricerca da zero (non
un porting) sul vero segnale, richiesta esplicitamente dall'utente.

## Meccanica del segnale reale

Da `NXS_MarketAnalysis.mqh` (`NXS_DetectSweepExt`) +
`NXS_Strategies_SMC.mqh` (`NXS_Strat_TurtleSoup`):
1. PDH/PDL = massimo/minimo del giorno PRECEDENTE (D1 shift1).
2. EQH/EQL = livelli "uguali" — cluster di 2+ swing point (wing=3
   barre) entro tolleranza 0.2×ATR.
3. Sweep = wick oltre il livello + chiusura di rientro dentro.
4. Candela di rientro con corpo ≥0.4×ATR, chiusura oltre il livello
   sweepato (in direzione opposta allo sweep).
5. Stop nativo = livello ±0.5×ATR, target RR fisso 2.0.
TF live: H1.

## Risultato: mai profittevole in modo robusto, su nessun TF/direzione

`turtle_soup_live_signal_25-08.py` — replica fedele riga-per-riga:

| TF | Direzione | n | PF (m1/m2) | Finestre |
|---|---|---|---|---|
| H1 (live) | simmetrica | 1824 | 0.58 (0.62/0.54) | 0/5 |
| H1 | BUY-only | 877 | 0.65 (0.68/0.62) | 0/5 |
| H1 | SELL-only | 947 | 0.52 (0.54/0.49) | 0/5 |
| 4h | simmetrica | 828 | 0.76 (0.70/0.84) | 1/5 |
| **4h** | **BUY-only** | 393 | **0.94 (0.81/1.09)** | 3/5 |
| 4h | SELL-only | 435 | 0.62 (0.61/0.64) | 0/5 |
| 30m | simmetrica | 3194 | 0.42 (0.41/0.44) | 0/5 |
| 30m | BUY-only | 1556 | 0.49 (0.47/0.51) | 0/5 |
| 30m | SELL-only | 1638 | 0.37 (0.36/0.37) | 0/5 |

Il migliore risultato assoluto (4h BUY-only) resta sotto pareggio
(PF0.94, solo 3/5 finestre positive). Non è un problema di timeframe
o direzione come per STRUCT_REACT/EMA_PULLBACK — il pattern
sweep-PDH/PDL/EQH/EQL + rientro con questo stop/target non ha edge
misurabile su XAUUSD in nessuna configurazione provata.

## Verdetto

**Disattivata** (`InpStrat_TurtleSoup = false`). A differenza di CRT
(escluso dal registro ma segnale ancora "vivo" nel codice), questa è
la prima strategia disattivata dopo un test COMPLETO e dedicato del
suo vero comportamento live, non solo un ripiego per rumore nei log.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Correzione Trailing Z_SCORE_BREAKOUT, il TP fisso lo annullava (25-08)]]
[[NEXUS EA - Tabella Master Strategie Verificate (24-08)]]
