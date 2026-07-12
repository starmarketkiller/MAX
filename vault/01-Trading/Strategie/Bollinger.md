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

## Note


## Collegamenti
[[MOC - Trading]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]]
