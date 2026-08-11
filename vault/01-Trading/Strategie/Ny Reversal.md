---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: NY_REVERSAL
created: 2026-07-12
updated: 2026-07-12
---

# Strategia: NY_REVERSAL

## Tipo
Sessione/ICT (non portabile dal sito)

## Trigger meccanico
Reversal di sessione New York.

## Configurazione attuale (v2.5.0)
- **Timeframe**: N/D — non connessa al collector segnali
- **SL**: N/D — non connessa al collector segnali× ATR · **TP**: N/D — non connessa al collector segnali× ATR
- **Filtro HTF**: N/D — non connessa al collector segnali
- **Trailing**: N/D — non connessa al collector segnali
- **Rischio per trade**: N/D — non connessa al collector segnali%
- **Abilitata nell'EA**: Sì

## Risultati (build v2.4.8, stessa config di quella sopra)
- **3 mesi**: 0 trade eseguiti in questo build.
- **3 anni**: 0 trade eseguiti in questo build.

## Stato
🔬 Prima serie di dati mai raccolta (16/07) — non più NOT_CONNECTED. Miglior
PF del gruppo su 1h (1.42) ma campione minuscolo (20 trade) — troppo poco
per fidarsi ([[NEXUS EA - Principi]] #4). Su 4h campione ancora più piccolo
(10 trade) e negativo. Nessun profilo MT5 esiste ancora.

## Prima connessione al sito (16/07)
Implementata la vera logica MQL5 (`NXS_Strat_NYReversal`): sessione
NY/Overlap + high/low della sessione Londra precedente (6-12 GMT, calcolato
dalle ultime 48 barre) come riferimento + sweep di quel range + CHoCH
(proxy). Vedi [[Amd Cont]] per il metodo.

Test SL1.5/TP3.0 generico, ~2 anni Yahoo intraday:

| TF | Trade | PF | DD% | Net |
|---|---|---|---|---|
| 1h | 20 | **1.42** | 2.97 | +470 |
| 4h | 10 | 0.50 | 6.79 | -400 |

Il campione più piccolo delle 7 strategie a sessione — il PF1.42 è
interessante ma su soli 20 trade non è ancora un segnale, è rumore
potenziale. Da riguardare quando ci sarà più storico. Non ancora validata
su MT5 (`InpStrategySelector=31`).

## Aggiornamento 11/08 — stesso fix CHoCH-a-finestra di IFVG/TURTLE_SOUP, qui negativo

`sig_ny_reversal` condivide la stessa struttura: CHoCH fractal richiesto
sulla STESSA barra dello sweep+reclaim del range di Londra. Registrata
`NY_REVERSAL_CHOCH_WINDOW` con la stessa detection entro 5 barre, testata
su 1h e 30m (storico ampio 2019-2026, non più i 2 anni Yahoo della nota
sopra):

| TF | Variante | IS | OOS | Walk-forward |
|---|---|---|---|---|
| 1h | baseline | 0.53/19 | 4.92/11 (rumore, 5-8 trade/finestra) | 0.0, 0.68, 0.99, 8.28, 1.52 |
| 1h | CHOCH_WINDOW | 1.19/66 | 0.9/36 | 1.9, 1.15, 0.84, 1.21, 0.58 |
| 30m | baseline | 1.05/44 | 1.67/25 | 0.37, 2.16, 0.63, 1.91, 1.53 |
| 30m | CHOCH_WINDOW | 0.79/134 | **1.04/93** | 0.71–1.13, quasi piatto |

A differenza di IFVG (dove la finestra ha sbloccato segnale reale), qui il
fix **peggiora**: il campione cresce molto (3-4x) ma il PF scende verso
1.0 su entrambi i TF e il drawdown esplode (30m: 6.3%→25.4% IS, 5.7%→16.8%
OOS). La OOS 4.92 della baseline sul 1h era quasi certamente rumore (11
trade, walk-forward che oscilla 0-8.28), ma la finestra non lo sostituisce
con edge vero — lo sostituisce con un campione grande ma piatto attorno a
PF 1. Conferma che **il fix "CHoCH a finestra" non è universale**: funziona
quando il pattern di base ha un edge reale offuscato dal timing troppo
rigido (IFVG, FVG_MIT, TURTLE_SOUP), non quando il pattern di base non ha
edge e la finestra si limita ad aggiungere rumore/trade di qualità più
bassa. Nessun ulteriore fix proposto per NY_REVERSAL.

## Note

## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[Amd Cont]]
