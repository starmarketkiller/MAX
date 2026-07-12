---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: ICHIMOKU
created: 2026-07-12
updated: 2026-07-12
---

# Strategia: ICHIMOKU

## Tipo
Trend/breakout

## Trigger meccanico
Rottura della Kumo (nuvola) con Tenkan/Kijun allineati nella direzione della rottura.

## Configurazione attuale (v2.5.0)
- **Timeframe**: H4
- **SL**: 1.0× ATR · **TP**: 4.5× ATR
- **Filtro HTF**: True
- **Trailing**: stretto (incassa presto), attivazione 0.5 ATR
- **Rischio per trade**: 1.8%
- **Abilitata nell'EA**: **No — disabilitata in NXS_Profile_Enabled**

## Risultati (build v2.4.8, stessa config di quella sopra)
- **3 mesi**: 0 trade eseguiti in questo build. (81 setup rilevati ma nessuno eseguito — strategia disabilitata/bloccata)
- **3 anni**: 0 trade eseguiti in questo build. (29 setup rilevati ma nessuno eseguito — strategia disabilitata/bloccata)

## Stato
🔴 DISABILITATA — Sweep sito 10y anomalo con HTF=0 + rumore statistico su MT5 (campione <5 trade). Resta ferma finche' non si trova un config affidabile.

## Note


## Collegamenti
[[MOC - Trading]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]]
