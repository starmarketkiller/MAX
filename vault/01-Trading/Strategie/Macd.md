---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: MACD
created: 2026-07-12
updated: 2026-07-12
---

# Strategia: MACD

## Tipo
Trend-following

## Trigger meccanico
MACD > signal e sopra 0, prezzo sopra EMA200 (long, speculare per short).

## Configurazione attuale (v2.5.0)
- **Timeframe**: H4
- **SL**: 2.0× ATR · **TP**: 3.0× ATR
- **Filtro HTF**: True
- **Trailing**: stretto (incassa presto)
- **Rischio per trade**: 1.5%
- **Abilitata nell'EA**: Sì

## Risultati (build v2.4.8, CONFIG PRECEDENTE (diversa da quella sopra))
- **3 mesi**: 2134 setup, 72W/48L/24BE, WR 60.0%, expR +0.062, **PF 1.35**
- **3 anni**: 742 setup, 52W/42L/13BE, WR 55.3%, expR +0.023, **PF 1.11**

## Stato
⏳ PENDING v2.5.0 — la config precedente era GIA' valida (✅ VALIDATA — profittevole anche sui 3 anni); v2.5.0 la raffina ulteriormente coi parametri dello screening sito, non la corregge da un fallimento. In attesa della validazione 3M+3Y sul nuovo build.

## Note


## Collegamenti
[[MOC - Trading]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]]
