---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: LIQ_SWEEP
created: 2026-07-12
updated: 2026-07-12
---

# Strategia: LIQ_SWEEP

## Tipo
SMC/liquidity sweep

## Trigger meccanico
Sweep di un massimo/minimo con reversal di conferma.

## Configurazione attuale (v2.5.0)
- **Timeframe**: D1
- **SL**: 1.5× ATR · **TP**: 3.0× ATR
- **Filtro HTF**: True
- **Trailing**: largo (famiglia SMC)
- **Rischio per trade**: 0.6%
- **Abilitata nell'EA**: Sì

## Risultati (build v2.4.8, stessa config di quella sopra)
- **3 mesi**: 234 setup, 1W/1L/1BE, WR 50.0%, expR +0.017, **PF 1.60**
- **3 anni**: 4 setup, 1W/0L/0BE, WR 100.0%, expR +0.053, **PF 99.00**

## Stato
PENDING — campione troppo piccolo (<15 trade) per giudicare

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]]
