---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: TSI
created: 2026-07-12
updated: 2026-07-12
---

# Strategia: TSI

## Tipo
Momentum

## Trigger meccanico
RSI>52 + prezzo sopra EMA20 con EMA20 in salita (short speculare) — riportata alla logica del sito.

## Configurazione attuale (v2.5.0)
- **Timeframe**: D1
- **SL**: 1.5× ATR · **TP**: 4.5× ATR
- **Filtro HTF**: True
- **Trailing**: stretto (incassa presto)
- **Rischio per trade**: 0.5%
- **Abilitata nell'EA**: Sì

## Risultati (build v2.4.8, CONFIG PRECEDENTE (diversa da quella sopra))
- **3 mesi**: 0 trade eseguiti in questo build. (1780 setup rilevati ma nessuno eseguito — strategia disabilitata/bloccata)
- **3 anni**: 0 trade eseguiti in questo build. (1355 setup rilevati ma nessuno eseguito — strategia disabilitata/bloccata)

## Stato
⏳ PENDING v2.5.0 — era disabilitata/non raggiunta in v2.4.8, riabilitata in v2.5.0 sulla base dello screening sito. In attesa della validazione 3M+3Y sul nuovo build.

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]]
