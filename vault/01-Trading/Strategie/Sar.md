---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: SAR
created: 2026-07-12
updated: 2026-07-12
---

# Strategia: SAR

## Tipo
Trend-following

## Trigger meccanico
Parabolic SAR sotto il prezzo + EMA9>EMA21 (long, speculare per short).

## Configurazione attuale (v2.5.0)
- **Timeframe**: H4
- **SL**: 1.5× ATR · **TP**: 4.0× ATR
- **Filtro HTF**: True
- **Trailing**: largo (corre)
- **Rischio per trade**: 1.5%
- **Abilitata nell'EA**: Sì

## Risultati (build v2.4.8, CONFIG PRECEDENTE (diversa da quella sopra))
- **3 mesi**: 3163 setup, 81W/109L/22BE, WR 42.6%, expR +0.041, **PF 1.21**
- **3 anni**: 1169 setup, 72W/80L/17BE, WR 47.4%, expR -0.035, **PF 0.88**

## Stato
⏳ PENDING v2.5.0 — la config precedente falliva sui 3 anni (❌ NON VALIDATA — sotto PF 1.0 sui 3 anni (fallisce fuori-campione)); v2.5.0 la cambia apposta sulla base dello screening sito. In attesa della validazione 3M+3Y sul nuovo build.

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]]
