---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: ORDER_BLOCK
created: 2026-07-12
updated: 2026-07-12
---

# Strategia: ORDER_BLOCK

## Tipo
SMC/order block

## Trigger meccanico
Impulso (body>1.2 ATR) 3-10 barre fa + retest del blocco con rifiuto (chiusura oltre il midpoint). Da v2.4.2: richiede conferma reazione (structure+react engine).

## Configurazione attuale (v2.5.0)
- **Timeframe**: D1
- **SL**: 1.0× ATR · **TP**: 3.0× ATR
- **Filtro HTF**: True
- **Trailing**: largo (corre)
- **Rischio per trade**: 0.5%
- **Abilitata nell'EA**: Sì

## Risultati (build v2.4.8, stessa config di quella sopra)
- **3 mesi**: 563 setup, 3W/3L/1BE, WR 50.0%, expR +0.068, **PF 1.97**
- **3 anni**: 130 setup, 3W/5L/0BE, WR 37.5%, expR -0.202, **PF 0.24**

## Stato
PENDING — campione troppo piccolo (<15 trade) per giudicare

## Note


## Collegamenti
[[MOC - Trading]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]]
