---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, fvg-cont, h4, buy-sell-split]
created: 2026-09-04
updated: 2026-09-04
---

# NEXUS EA — FVG_CONT (H4): miglior risultato di oggi, contraddice una nota storica nel codice (04/09)

## Perché

Quarto elemento della coda prioritaria. Il codice (`NXS_StrategyProfiles.mqh`
riga ~381) aveva un commento: *"CRITICA su MT5 reale (PF0.79) pur con
backtest Python forte"* (Python PF1.78). Testato comunque con la
metodologia di oggi, aspettandosi un esito debole.

## Risultato — il migliore di tutta la sessione

| Metrica | Valore |
|---|---|
| Trade | 167 |
| PF | **1.93** |
| Net (3 anni) | **+$2655.19** |
| Sharpe | **2.63** |
| Max DD balance | $400.68 (40.1% del deposito) |

Miglior PF e miglior Sharpe di tutte le strategie testate oggi
(ADX_RSI 2.04/1.20, BOLLINGER H4 1.35/2.45, MACD 1.53/1.28).

## BUY vs SELL — diverso dalle altre 3 di oggi

| | Trade | WR | Net |
|---|---|---|---|
| BUY | 120 | 38.3% | +$2419.22 |
| **SELL** | 47 | 31.9% | **+$581.23** |

A differenza di ADX_RSI/BOLLINGER/MACD (dove SELL era rumore puro,
~$0-160), qui **SELL è genuinamente positivo** — un pattern diverso,
non spiegabile solo col rally secolare. Da approfondire perché.

## Discrepanza con la nota storica — non risolta

Il commento nel codice cita PF0.79 su MT5 reale contro Python PF1.78.
Oggi: PF1.93 su MT5, **sopra anche il numero Python**. Possibili
spiegazioni non verificate: la config è cambiata da quando fu scritto
il commento, il periodo/dataset era diverso, oppure quel numero si
riferiva a una config con filtri diversi (es. Elliott già attivo,
trailing diverso). Segnalato come discrepanza aperta, non indagata a
fondo — prima di fidarsi ciecamente di questo risultato varrebbe la
pena capire cosa sia cambiato.

## Non ancora fatto

- Causa della discrepanza col PF0.79 storico non indagata.
- Perché SELL funziona qui e non altrove — non approfondito.
- Trailing/Elliott (ricetta Python) non provati.
- Walk-forward/finestre separate non fatto.

## Collegamenti
[[NEXUS EA - Piano di Test Master, Stato per Ogni Strategia e Coda Prioritaria (03-09)]] ·
[[MOC - Trading]]
