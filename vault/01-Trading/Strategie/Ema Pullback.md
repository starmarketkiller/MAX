---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: EMA_PULLBACK
created: 2026-07-12
updated: 2026-07-12
---

# Strategia: EMA_PULLBACK

## Tipo
Trend/pullback

## Trigger meccanico
EMA20>EMA50 (trend) + pullback che chiude di nuovo sopra EMA20 — logica del sito, riportata in v2.3.8.

## Configurazione attuale (v2.5.0)
- **Timeframe**: H4
- **SL**: 1.5× ATR · **TP**: 4.0× ATR
- **Filtro HTF**: True
- **Trailing**: stretto (incassa presto)
- **Rischio per trade**: 1.5%
- **Abilitata nell'EA**: Sì

## Risultati (build v2.4.8, CONFIG PRECEDENTE (diversa da quella sopra))
- **3 mesi**: 379 setup, 12W/10L/6BE, WR 54.5%, expR +0.079, **PF 1.49**
- **3 anni**: 69 setup, 1W/7L/1BE, WR 12.5%, expR -0.377, **PF 0.14**

## Stato
⏳ PENDING v2.5.0 — la config precedente falliva sui 3 anni (PENDING — campione troppo piccolo (<15 trade) per giudicare); v2.5.0 la cambia apposta sulla base dello screening sito. In attesa della validazione 3M+3Y sul nuovo build.

## Note


## Collegamenti
[[MOC - Trading]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]]
