---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: OB_MIT
created: 2026-07-12
updated: 2026-07-12
---

# Strategia: OB_MIT

## Tipo
SMC/order block

## Trigger meccanico
Stessa logica di ORDER_BLOCK (mitigazione strutturale), floor di score 68.

## Configurazione attuale (v2.5.0)
- **Timeframe**: D1
- **SL**: 1.5× ATR · **TP**: 4.0× ATR
- **Filtro HTF**: False
- **Trailing**: largo (corre)
- **Rischio per trade**: 0.5%
- **Abilitata nell'EA**: Sì

## Risultati (build v2.4.8, CONFIG PRECEDENTE (diversa da quella sopra))
- **3 mesi**: 633 setup, 3W/4L/1BE, WR 42.9%, expR +0.032, **PF 1.37**
- **3 anni**: 220 setup, 5W/10L/1BE, WR 33.3%, expR -0.179, **PF 0.20**

## Stato
⏳ PENDING v2.5.0 — la config precedente falliva sui 3 anni (❌ NON VALIDATA — sotto PF 1.0 sui 3 anni (fallisce fuori-campione)); v2.5.0 la cambia apposta sulla base dello screening sito. In attesa della validazione 3M+3Y sul nuovo build.

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]]
