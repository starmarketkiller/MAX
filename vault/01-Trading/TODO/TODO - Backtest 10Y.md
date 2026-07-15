---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, todo, backtest, v2.5.0]
created: 2026-07-15
updated: 2026-07-15
---

# TODO — Backtest 10Y e miglioramento strategie

Lista viva di cose da fare, aggiornata mano a mano che arrivano nuovi dati.
Non aspettare che tutti i 10 segmenti siano pronti per agire — molte di queste
sono già azionabili oggi con i 5 anni che abbiamo (vedi
[[NEXUS EA - Backtest 10Y Segmentato - Analisi]] e
[[NEXUS EA - Hedge nel Tempo]]).

## Quando arrivano dati nuovi

- [ ] **Segmento 9**: verificare appena pushato (periodo reale, barre, PF,
  drawdown, ranking per strategia) — stesso trattamento dato ai segmenti 1-8.
  Al 15/07 non risultava ancora su nessun branch del repo.
- [ ] **Segmento 10**: idem appena arriva.
- [ ] **Ri-eseguire i segmenti 1, 2, 3** — falliti per un bug di esecuzione del
  tester (race condition tra lanci consecutivi sulla stessa istanza), non
  rappresentano l'andamento reale 2016-2019. Finché non sono rifatti, il
  dataset "10 anni" è in realtà "5 anni" (2019-2023).
- [ ] Aggiornare [[NEXUS EA - Backtest 10Y Segmentato - Analisi]] e
  [[NEXUS EA - Hedge nel Tempo]] con i dati completi non appena si arriva a
  10/10 segmenti affidabili.
- [ ] Verificare se le date dei segmenti (etichetta "2016", "2017"... ma range
  reale 11/07-11/07, non anno solare) sono un problema per l'interpretazione o
  solo un'etichetta — irrilevante per i numeri ma da tenere a mente.

## Bug/gap da fixare nel codice (priorità alta, non serve aspettare altri segmenti)

- [ ] **Contatore `executed` rotto** (`NXS_StratStats.mqh`): sempre 0 anche
  quando ci sono centinaia di trade reali. Rende inutilizzabili `exec_rate_pct`,
  `dominant_blocker`, `health` nei CSV diagnostici. Causa non trovata (il
  codice sembra corretto lato scrittura) — serve strumentazione aggiuntiva o
  log dal vivo per isolarla.
- [ ] **Nessun gate sul drawdown cumulato dal picco equity** — solo
  `InpMaxDailyDDPct` (giornaliero, si resetta ogni giorno). Il DD 87.22% nel
  segmento 2020 è la conferma pratica del buco. Aggiungere un gate tipo
  `InpMaxTotalDDPct` che blocchi nuovi trade (o riduca il rischio) quando
  l'equity scende oltre una soglia dal massimo storico — non solo dall'inizio
  giornata.

## Strategie da correggere/spegnere (priorità in ordine)

- [ ] **SAR** — 0/5 anni positivi, -29.2R. Il fix HTF v2.5.0 le è stato
  applicato per generalizzazione (non compare tra le config vincenti dello
  screening sito). Da spegnere o riscrivere la logica di trigger da zero.
- [ ] **MACD** — regressione: era validata su v2.4.8 (PF 1.11), ora -18.5R.
  Da valutare il rollback alla config v2.4.8 (SL/TP diversi — vedi
  [[NEXUS EA - Log Versioni]]) e ri-testare in isolamento prima di
  toccarla di nuovo sulla base del sito.
- [ ] **ADX_RSI** — 1/5 anni positivi, -14.2R, in peggioramento 2019→2022.
- [ ] **RSI_DIV** — capire cosa è successo specificamente nel **2022**
  (-9.4R da sola, mentre gli altri 4 anni sono nel complesso positivi
  +5.3R). Potrebbe essere un evento isolato (news/regime) non un difetto
  strutturale della strategia.
- [ ] **BJORGUM** — il segnale si è ribaltato (da PF 2.14/5 trade a -6.6R/46
  trade, 4/5 anni negativi). Non urgente come le prime 3 ma va rivista.

## Potenziale da sfruttare (non ancora testato per davvero)

- [ ] **Test isolato del nucleo hedge**: TURTLE_SOUP + BREAKOUT_ACC + CISD
  sommate algebricamente fanno +14.7R su 5 anni con un solo anno debolmente
  negativo (vedi [[NEXUS EA - Hedge nel Tempo]]). Questo è un calcolo a
  tavolino (somma di R), **non** un backtest reale con le tre attive insieme
  (margine condiviso, corsie hedge, `InpMaxConcurrent`). Serve un run dedicato
  con `InpStrategySelector`/profilo che isoli solo queste tre per confermare
  che il combinato regge anche nell'esecuzione reale.
- [ ] **Profilo "solo nucleo hedge + satelliti piccoli"**: una volta confermato
  il punto sopra, testare un profilo che pesa forte
  TURTLE_SOUP/BREAKOUT_ACC/CISD e mette a rischio minimo (o spegne) SAR/MACD/
  ADX_RSI finché non sono fixate. Ipotesi: l'equity curve del portafoglio
  ridotto dovrebbe avvicinarsi molto di più a un profilo accettabile per un
  conto reale piccolo (€200-1000) di quanto non faccia oggi il portafoglio
  completo (-78.4R su 5 anni).
- [ ] **MALAYSIAN_SNR / FVG_MIT / SMS_BMS_RTO**: uscite dal gruppo "nessun
  trade" in questo giro (ora eseguono, anche se pochissimo: 10, 3, 3 trade
  rispettivamente in 5 anni). Nessuna azione ora, solo lasciarle accumulare
  campione nei prossimi segmenti.
- [ ] **IFVG / LIQ_VOID / RANGE_FADE / WEEKLY_EXP**: 0 setup rilevati in 5 anni
  interi. Da investigare se la logica di rilevamento è troppo restrittiva per
  XAUUSD sui timeframe usati, o se semplicemente non c'è mai stato un setup
  valido — priorità bassa rispetto a SAR/MACD/ADX_RSI che perdono soldi
  attivamente.

## Collegamenti
[[MOC - Trading]] · [[NEXUS EA - Backtest 10Y Segmentato - Analisi]] · [[NEXUS EA - Hedge nel Tempo]] · [[MOC - Strategie]] · [[NEXUS EA - Principi]]
