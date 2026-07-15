---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: TSI
created: 2026-07-12
updated: 2026-07-15
---

# Strategia: TSI

## Tipo
Momentum

## Trigger meccanico
RSI>52 + prezzo sopra EMA20 con EMA20 in salita (short speculare) — riportata alla logica del sito.

⚠️ **Scoperta 15/07**: non è il vero True Strength Index (William Blau,
doppio smoothing EMA del momentum) — il commento nel codice lo dichiara
esplicitamente ("simplified RSI/EMA proxy"). Test A/B col vero TSI: PF
1.35→1.42, drawdown quasi azzerato (10.57%→4.99%), ma **-73% di trade**. Non
ancora corretto — è un trade-off frequenza/qualità che va deciso
esplicitamente, non un fix "gratis" come SAR/ADX_RSI. Dettaglio:
[[NEXUS EA - Audit Fedeltà Trigger (tutte le 37 strategie)]].

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

## Risultati (backtest 10y segmentato v2.5.0, 5 anni affidabili 2019-2023)
539 trade totali — ora esegue davvero (era 0 trade in v2.4.8). R per anno:
2019 -2.3 · 2020 -2.1 · 2021 -1.3 · 2022 -1.2 · 2023 +1.1. **Somma -5.8R — 1
anno su 5 positivo (solo 2023)**. Dettaglio:
[[NEXUS EA - Backtest 10Y Segmentato - Analisi]].

## Stato
⏳ PENDING — la riabilitazione ha funzionato dal punto di vista dell'esecuzione
(539 trade, campione ampio) ma il segnale resta negativo in 4 anni su 5,
con un miglioramento solo nell'ultimo anno da monitorare.

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[NEXUS EA - Backtest 10Y Segmentato - Analisi]] · [[NEXUS EA - Audit Fedeltà Trigger (tutte le 37 strategie)]]
