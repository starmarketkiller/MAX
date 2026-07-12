---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: ADX_RSI
created: 2026-07-12
updated: 2026-07-12
---

# Strategia: ADX_RSI

## Tipo
Trend-following

## Trigger meccanico
EMA50 come filtro trend + RSI in banda 45-65 (long) / 35-55 (short) — logica del sito, riportata in v2.3.8.

## Configurazione attuale (v2.5.0)
- **Timeframe**: D1
- **SL**: 1.0× ATR · **TP**: 4.0× ATR
- **Filtro HTF**: True
- **Trailing**: largo (corre)
- **Rischio per trade**: 1.3%
- **Abilitata nell'EA**: Sì

## Risultati (build v2.4.8, CONFIG PRECEDENTE (diversa da quella sopra))
- **3 mesi**: 4361 setup, 20W/26L/11BE, WR 43.5%, expR +0.014, **PF 1.17**
- **3 anni**: 780 setup, 21W/42L/19BE, WR 33.3%, expR -0.094, **PF 0.45**

## Stato
⏳ PENDING v2.5.0 — la config precedente falliva sui 3 anni (❌ NON VALIDATA — sotto PF 1.0 sui 3 anni (fallisce fuori-campione)); v2.5.0 la cambia apposta sulla base dello screening sito. In attesa della validazione 3M+3Y sul nuovo build.

## Note


## Collegamenti
[[MOC - Trading]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]]
