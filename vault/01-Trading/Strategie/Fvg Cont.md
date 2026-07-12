---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: FVG_CONT
created: 2026-07-12
updated: 2026-07-12
---

# Strategia: FVG_CONT

## Tipo
SMC/continuazione

## Trigger meccanico
Gap a 3 candele (low[1]>high[3]) + continuazione nel senso del trend (close vs EMA50) — logica del sito.

## Configurazione attuale (v2.5.0)
- **Timeframe**: H4
- **SL**: 1.0× ATR · **TP**: 4.5× ATR
- **Filtro HTF**: True
- **Trailing**: largo (corre)
- **Rischio per trade**: 0.4%
- **Abilitata nell'EA**: Sì

## Risultati (build v2.4.8, stessa config di quella sopra)
- **3 mesi**: 443 setup, 15W/21L/2BE, WR 41.7%, expR +0.090, **PF 1.42**
- **3 anni**: 142 setup, 10W/12L/6BE, WR 45.5%, expR -0.009, **PF 0.97**

## Stato
❌ NON VALIDATA — sotto PF 1.0 sui 3 anni (fallisce fuori-campione)

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]]
