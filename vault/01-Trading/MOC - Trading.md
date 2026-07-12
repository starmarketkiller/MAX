---
type: moc
domain: trading
status: active
tags: [trading, nexus-ea]
created: 2026-07-12
updated: 2026-07-12
---

# 📈 Trading — NEXUS EA

EA MQL5 per gold/BTC su conto piccolo (~€200-1000), pensato per rispecchiare 1:1 il
motore di backtest Python del sito ("Backtest Lab" = source of truth). Obiettivo:
profitto reale, non solo curve di backtest.

## Note in questo dominio
- **[[NEXUS EA - Panoramica]]** — cos'è, architettura, filosofia (multi-TF, hedge per
  strategia, "il conto è il regolatore").
- **[[NEXUS EA - Principi]]** — le lezioni dure, in forma di regole durature. **Leggi
  questa prima di qualsiasi altra cosa.**
- **[[NEXUS EA - Log Versioni]]** — cronologia v2.3.7 → v2.5.0, cosa è cambiato e perché,
  con i numeri di ogni test.
- **[[NEXUS EA - Lezione Overfitting 3Y]]** — la scoperta più importante finora: il
  campione record sui 3 mesi crollava sui 3 anni. Leggila prima di fidarti di un
  qualsiasi tuning futuro.
- **[[NEXUS EA - Screening Strategie (sito 10y)]]** — tabella di riferimento: quale
  configurazione (SL/TP/HTF) massimizza l'edge di ciascuna strategia sul motore del sito.
- **[[Sito Backtest Lab - Note Tecniche]]** — come funziona il backend Python/React,
  incluso il problema di deploy Render risolto il 12/07.
- **[[MOC - Strategie]]** — indice delle 36 schede per-strategia (`Strategie/`),
  raggruppate per stato di validazione (validate/pending/fallite/campione piccolo/
  disabilitate/non connesse). Punto di partenza per lavorare strategia-per-strategia:
  aggiornare la scheda e spostarla di gruppo è il modo in cui questo vault resta vivo.

## Stato corrente (12 luglio 2026)
- Versione EA: **v2.5.0** — applica filtro HTF universale (scoperto nello screening a
  10 anni) a ADX_RSI/EMA_PULLBACK/MACD/SAR/OB_MIT, riabilita TSI e BREAKOUT_ACC.
- **In corso**: validazione 3 mesi + 3 anni su MT5 (~36 ore). Il 3 anni è il test che
  conta — deve smettere di azzerare il conto (v2.4.8 aveva fatto DD 87% fuori-campione).
- Uniche strategie **validate** su 3 anni con campione sufficiente (≥15 trade) finora:
  **TURTLE_SOUP** (PF 2.12, 17 trade) e **MACD** (PF 1.11, 94 trade — ma la sua config
  è già cambiata in v2.5.0, quindi anche questo va riconfermato).
- **BJORGUM** ha PF 2.14 sui 3 anni ma solo 5 trade eseguiti — troppo pochi per
  dichiararla validata, nonostante il numero attraente (vedi [[NEXUS EA - Principi]] #4).
