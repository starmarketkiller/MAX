---
type: moc
domain: trading
status: active
tags: [trading, nexus-ea]
created: 2026-07-12
updated: 2026-07-15
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
- **[[NEXUS EA - Backtest 10Y Segmentato - Analisi]]** — la validazione più ampia
  fatta finora (5 anni reali di dati, 2019-2023): bug trovati, ranking per strategia,
  perché il fix HTF v2.5.0 non ha funzionato per SAR/MACD/ADX_RSI.
- **[[NEXUS EA - Hedge nel Tempo]]** — quali strategie si coprono a vicenda nel
  tempo: il nucleo TURTLE_SOUP+BREAKOUT_ACC+CISD.
- **[[TODO - Backtest 10Y]]** (cartella `01-Trading/TODO/`) — aggiornamenti da fare
  appena arrivano i segmenti 9-10 e le eventuali ri-esecuzioni di 1-3.

## Stato corrente (15 luglio 2026)
- Versione EA: **v2.5.0** — applica filtro HTF universale (scoperto nello screening a
  10 anni) a ADX_RSI/EMA_PULLBACK/MACD/SAR/OB_MIT, riabilita TSI e BREAKOUT_ACC.
- **Backtest 10 anni segmentato in corso** (10 segmenti da 1 anno): 8/10 arrivati.
  Segmenti 1-3 falliti per bug del tester (da ri-eseguire), segmenti 4-8 (5 anni
  reali 2019-2023) affidabili e **tutti in perdita** — PF 0.63-0.98, DD fino
  all'87.22% (stesso numero del DD fuori-campione di v2.4.8, causa mai chiusa:
  nessun gate protegge il drawdown cumulato dal picco, solo quello giornaliero).
  Segmenti 9-10 ancora in esecuzione.
- Il fix HTF v2.5.0 **non ha funzionato** per le 3 strategie che dovevano
  beneficiarne di più: SAR (-29.2R, 0/5 anni positivi), MACD (-18.5R — era già
  validata su v2.4.8, ora la 2ª peggiore), ADX_RSI (-14.2R). Insieme sono
  l'80% della perdita totale del portafoglio (-78.4R su 5 anni).
- Uniche strategie **validate/promettenti** oggi: **TURTLE_SOUP** (✅ +7.3R su 5
  anni, confermata su più finestre), **BREAKOUT_ACC** (+3.9R, 4/5 anni positivi) e
  **CISD** (+3.5R, mai un anno negativo) — insieme formano un nucleo che fa
  +14.7R con un solo anno debolmente negativo su 5. **BJORGUM** si è ribaltata:
  da PF 2.14 (5 trade, 3 anni) a -6.6R (46 trade, 5 anni, 4/5 anni negativi) —
  la conferma pratica di [[NEXUS EA - Principi]] #4.
