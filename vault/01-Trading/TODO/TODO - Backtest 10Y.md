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

- [x] **Segmento 9** — arrivato e analizzato il 15/07: PF 0.83, DD 88.69%
  (il peggiore del dataset, qualità storico 100%). Ha ridimensionato
  TURTLE_SOUP (+7.3R→+0.1R) e peggiorato RSI_DIV (ora tra le fallite). Vault
  aggiornato.
- [ ] **Segmento 10**: ultimo mancante, ancora in esecuzione al 15/07.
- [ ] **Ri-eseguire i segmenti 1, 2, 3** — falliti per un bug di esecuzione del
  tester (race condition tra lanci consecutivi sulla stessa istanza), non
  rappresentano l'andamento reale 2016-2019. Finché non sono rifatti, il
  dataset "10 anni" è in realtà "6 anni" (2019-2024).
- [ ] Aggiornare [[NEXUS EA - Backtest 10Y Segmentato - Analisi]] e
  [[NEXUS EA - Hedge nel Tempo]] col segmento 10 non appena arriva — dato che
  il segmento 9 da solo ha già ribaltato una conclusione (TURTLE_SOUP), non
  dare per definitivi i numeri attuali nemmeno a 9/10.
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

- [ ] **SAR** — 0/6 anni positivi, -34.3R. Il fix HTF v2.5.0 le è stato
  applicato per generalizzazione (non compare tra le config vincenti dello
  screening sito). Da spegnere o riscrivere la logica di trigger da zero.
- [ ] **MACD** — regressione: era validata su v2.4.8 (PF 1.11), ora -21.1R.
  Da valutare il rollback alla config v2.4.8 (SL/TP diversi — vedi
  [[NEXUS EA - Log Versioni]]) e ri-testare in isolamento prima di
  toccarla di nuovo sulla base del sito.
- [ ] **RSI_DIV** — sale in priorità col segmento 9: ora **due** anni
  catastrofici (2022 -9.4, 2024 -10.1), non più spiegabile come evento
  isolato. -17.5R su 6 anni.
- [ ] **ADX_RSI** — 1/6 anni positivi, -15.3R, ma il 2024 (-1.1) è il meno
  negativo da 4 anni — monitorare se è un vero segno di ripresa.
- [ ] **BJORGUM** — il segnale si è ribaltato (da PF 2.14/5 trade a -8.6R/62
  trade, 5/6 anni negativi). Non urgente come le prime 3 ma va rivista.

## Potenziale da sfruttare (non ancora testato per davvero)

- [ ] **Test isolato del nucleo hedge**: TURTLE_SOUP + BREAKOUT_ACC + CISD
  sommate algebricamente fanno +7.6R su 6 anni, ridimensionato dal +14.7R su 5
  anni dopo il 2024 (vedi [[NEXUS EA - Hedge nel Tempo]]). Questo è un calcolo
  a tavolino (somma di R), **non** un backtest reale con le tre attive insieme
  (margine condiviso, corsie hedge, `InpMaxConcurrent`). Serve un run dedicato
  con `InpStrategySelector`/profilo che isoli solo queste tre per confermare
  che il combinato regge anche nell'esecuzione reale.
- [ ] **Profilo "nucleo hedge pesato su BREAKOUT_ACC + satelliti piccoli"**:
  col segmento 9, BREAKOUT_ACC è emersa come la componente più stabile
  (5/6 anni positivi, mai un anno chiaramente negativo) mentre TURTLE_SOUP e
  CISD hanno più varianza di quanto stimato prima. Testare un profilo che
  pesa BREAKOUT_ACC come base e le altre due come satelliti a rischio ridotto,
  non paritario, e mette a rischio minimo (o spegne) SAR/MACD/RSI_DIV/ADX_RSI
  finché non sono fixate.
- [ ] **MALAYSIAN_SNR / FVG_MIT / SMS_BMS_RTO**: uscite dal gruppo "nessun
  trade" nel primo giro (ora eseguono, anche se pochissimo: 10, 3, 3 trade
  in 5 anni). Aggiornare i conteggi col segmento 9 e lasciarle accumulare
  campione nei prossimi segmenti.
- [ ] **IFVG / LIQ_VOID / RANGE_FADE / WEEKLY_EXP**: 0 setup rilevati anche
  nel segmento 9 (verificato). Da investigare se la logica di rilevamento è
  troppo restrittiva per XAUUSD sui timeframe usati, o se semplicemente non
  c'è mai stato un setup valido — priorità bassa rispetto a SAR/MACD/RSI_DIV
  che perdono soldi attivamente.

## Collegamenti
[[MOC - Trading]] · [[NEXUS EA - Backtest 10Y Segmentato - Analisi]] · [[NEXUS EA - Hedge nel Tempo]] · [[MOC - Strategie]] · [[NEXUS EA - Principi]]
