---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: CISD
created: 2026-07-12
updated: 2026-07-12
---

# Strategia: CISD

## Tipo
SMC/change in state

## Trigger meccanico
3 barre dello stesso segno + rottura dell'estremo (Change in State of Delivery).

## Configurazione attuale (v2.5.0)
- **Timeframe**: H4
- **SL**: 1.5× ATR · **TP**: 3.0× ATR
- **Filtro HTF**: True
- **Trailing**: stretto (incassa presto)
- **Rischio per trade**: 0.5%
- **Abilitata nell'EA**: Sì

## Risultati (build v2.4.8, stessa config di quella sopra)
- **3 mesi**: 57 setup, 1W/2L/1BE, WR 33.3%, expR -0.209, **PF 0.18**
- **3 anni**: 9 setup, 1W/0L/0BE, WR 100.0%, expR +0.323, **PF 99.00**

## Stato
PENDING — campione troppo piccolo (<15 trade) per giudicare

## Note


## Collegamenti
[[MOC - Trading]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]]
