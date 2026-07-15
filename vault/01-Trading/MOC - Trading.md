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
  fatta finora (6 anni reali di dati, 2019-2024): bug trovati, ranking per strategia,
  perché il fix HTF v2.5.0 non ha funzionato per SAR/MACD/RSI_DIV/ADX_RSI.
- **[[NEXUS EA - Hedge nel Tempo]]** — quali strategie si coprono a vicenda nel
  tempo: il nucleo TURTLE_SOUP+BREAKOUT_ACC+CISD (ridimensionato col segmento 9).
- **[[NEXUS EA - Motore Sito: Audit e Confronto 10Y]]** — audit del codice del
  motore sito: nessun hedge/multi-posizione per design, e il proxy SAR è
  identico a EMA_PULLBACK (non testa mai la vera strategia).
- **[[TODO - Backtest 10Y]]** (cartella `01-Trading/TODO/`) — piano d'azione
  strategia-per-strategia e aggiornamenti da fare appena arriva il segmento 10.

## Stato corrente (15 luglio 2026, aggiornato col segmento 9)
- Versione EA: **v2.5.0** — applica filtro HTF universale (scoperto nello screening a
  10 anni) a ADX_RSI/EMA_PULLBACK/MACD/SAR/OB_MIT, riabilita TSI e BREAKOUT_ACC.
- **Backtest 10 anni segmentato in corso** (10 segmenti da 1 anno): 9/10 arrivati.
  Segmenti 1-3 falliti per bug del tester (da ri-eseguire), segmenti 4-9 (6 anni
  reali 2019-2024) affidabili e **tutti in perdita** — PF 0.63-0.98, DD fino
  all'88.69% nel 2024 (il peggiore di tutto il dataset, con qualità storico 100%
  — non un artefatto). Causa mai chiusa: nessun gate protegge il drawdown
  cumulato dal picco, solo quello giornaliero, e il problema non si è attenuato
  col tempo. Segmento 10 ancora in esecuzione.
- Il fix HTF v2.5.0 **non ha funzionato** per le strategie che dovevano
  beneficiarne di più: SAR (-34.3R, 0/6 anni positivi), MACD (-21.1R — era già
  validata su v2.4.8, ora la 2ª peggiore), RSI_DIV (-17.5R, salita in classifica
  col 2024), ADX_RSI (-15.3R). Insieme sono ~75% della perdita totale del
  portafoglio (-118.1R su 6 anni).
- **Aggiornamento importante dal segmento 9**: TURTLE_SOUP, che era la
  strategia migliore in assoluto (+7.3R su 5 anni), è quasi tornata a
  breakeven (+0.1R su 6 anni) dopo un 2024 pessimo (-7.2R) — non più
  "validata senza riserve". **BREAKOUT_ACC** (+4.3R, 5/6 anni positivi) è ora
  la componente più stabile del nucleo hedge, seguita da **CISD** (+3.2R, un
  solo anno lievemente negativo). Il nucleo dei tre insieme fa +7.6R su 6
  anni (era +14.7R su 5) — ridimensionato ma ancora nettamente il miglior
  angolo del portafoglio. **BJORGUM** si è ribaltata: da PF 2.14 (5 trade, 3
  anni) a -8.6R (5/6 anni negativi) — la conferma pratica di
  [[NEXUS EA - Principi]] #4.
