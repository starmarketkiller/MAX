---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: BOLLINGER
created: 2026-07-12
updated: 2026-07-12
---

# Strategia: BOLLINGER

## Tipo
Mean-reversion

## Trigger meccanico
Rientro dalla banda (close attraversa la banda verso il centro) — riportata alla logica del sito in v2.4.2 (niente filtro RSI).

## Configurazione attuale (v2.5.0)
- **Timeframe**: D1
- **SL**: 1.0× ATR · **TP**: 2.0× ATR
- **Filtro HTF**: False
- **Trailing**: stretto (incassa presto)
- **Rischio per trade**: 0.6%
- **Abilitata nell'EA**: Sì

## Risultati (build v2.4.8, stessa config di quella sopra)
- **3 mesi**: 156 setup, 1W/0L/1BE, WR 100.0%, expR +0.116, **PF 99.00**
- **3 anni**: 22 setup, 2W/1L/0BE, WR 66.7%, expR +0.047, **PF 2.88**

## Stato
PENDING — campione troppo piccolo (<15 trade) per giudicare

## Aggiornamento 11/08 — storico ampio: campione ora sufficiente, risultato misto

Sullo storico Dukascopy ampio (2019-2026) il campione non è più troppo
piccolo: **1d (vero TF di profilo)** dà 94 trade totali, IS 1.05/53 → OOS
0.85/40 — quasi pareggio, non chiaramente positivo né negativo.

Testato `regime_filter=(_REGIME_WEAK_TREND,)` (stessa idea che ha aiutato
la famiglia SCALP_*, mean-reversion come BOLLINGER):
- **Su 1d (vero TF)**: non aiuta, campione si dimezza (23/12) e resta
  sotto pareggio (IS 0.94, OOS 0.85).
- **Su 4h (fuori profilo)**: aiuta davvero — IS 1.52/121, OOS 1.08/73,
  walk-forward 4/5 finestre sopra 1.0 (range 1.14-1.78, una sola finestra
  a 0.8), drawdown basso (3-13%). Ma è un TF diverso da quello che gira
  live (D1) — stesso limite già visto con TURTLE_SOUP_CHOCH/FVG_MIT_WINDOW,
  il fix non si trasferisce al TF naturale.

Testato anche `RANGING`/`RANGE_CHOPPY` (ipotesi intuitiva per mean-
reversion): **peggiora** (IS 0.84, OOS 0.7) — controintuitivo, non
approfondito oltre.

Nessun cambio di codice applicato: il miglioramento reale trovato non è
sul TF che conta per la produzione. `RANGE_FADE` è un proxy letterale di
BOLLINGER (`sig_bollinger` riusato 1:1, vedi [[Range Fade]]) — stessa
conclusione, nessun test separato necessario.

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]]
