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
sono già azionabili oggi con i 6 anni che abbiamo (vedi
[[NEXUS EA - Backtest 10Y Segmentato - Analisi]],
[[NEXUS EA - Hedge nel Tempo]] e
[[NEXUS EA - Motore Sito: Audit e Confronto 10Y]]).

## 🔀 Sincronizzazione tra agenti (15/07) — risolto in parte

Scoperto che un'altra sessione lavora direttamente su `main` (agente
"NEXUS Bot") mentre questa lavora su un branch feature — nessuno dei due
vedeva i commit dell'altro senza un `git fetch` esplicito. Il segmento 10 e
una nota vault parallela sullo stesso argomento
([[NEXUS EA - Backtest 10Y Segmentato (v2.5.0)]]) sono arrivati su `main`
senza che questa sessione lo sapesse.

- [x] **Creato un hook SessionStart** (`.claude/hooks/session-start.sh` +
  `.claude/settings.json`) che ad ogni avvio sessione fa `git fetch` e
  segnala commit remoti mancanti, evidenziando i file toccati sia qui che
  altrove. Funziona per qualunque sessione Claude Code che apre questo
  repo — se l'altro agente non è Claude Code, serve un meccanismo
  equivalente lato suo.
- [x] **Fatto merge di `origin/main` in questo branch** — recuperati
  segmenti 9/10, la nota vault parallela, risolto un conflitto su
  [[NEXUS EA - Log Versioni]] (unite le due voci invece di sceglierne una).
- [ ] **Ancora da fare**: questo branch non è ancora unito in `main` — il
  lavoro di oggi (audit fedeltà, fix SAR/ADX_RSI, fonti esterne, framework
  setup buy/sell) non è visibile a chi lavora su `main`. Da decidere con
  l'utente se/quando fare il merge verso `main`.
- [ ] **Riconciliazione numerica in sospeso**: i conteggi trade per segmento
  non coincidono esattamente tra le due analisi parallele (vedi nota di
  riconciliazione in [[NEXUS EA - Backtest 10Y Segmentato (v2.5.0)]]) — da
  isolare la causa (metodo di conteggio diverso) prima di fidarsi
  ciecamente di uno dei due totali.
- [ ] **Segmento 10** arrivato (1.559 trade, il volume più alto) ma non
  ancora integrato nel ranking R-per-strategia di
  [[NEXUS EA - Backtest 10Y Segmentato - Analisi]] (fermo a 6 anni/segmenti
  4-9). Prossimo passo naturale quando si riprende quel lavoro.

## 🔍 Audit di fedeltà completo (15/07) — tutte le 37 strategie controllate

Su richiesta esplicita dell'utente dopo la scoperta SAR/ADX_RSI: letto per
intero il codice di tutte le 37 strategie (MQL5) + le `sig_*` del sito.
Risultato completo: [[NEXUS EA - Audit Fedeltà Trigger (tutte le 37 strategie)]].

- [x] Confermato: **34 delle 37 hanno trigger coerenti col nome** (verificato
  leggendo il codice riga per riga, non solo i risultati).
- [x] **Terzo caso trovato**: TSI, dichiarato nel commento come "simplified
  RSI/EMA proxy", non vero True Strength Index.
- [ ] **Decisione da prendere sul fix TSI** (non applicato, a differenza di
  SAR/ADX_RSI): il vero TSI migliora PF/DD ma taglia i trade del 73% nel
  test A/B (245→67 su 10y sito). Codice pronto (`tsi_series()` in
  `backtest.py`), manca solo la decisione se accettare meno frequenza per
  più qualità.
- [x] **ELLIOTT (37ª strategia) trovata mai tracciata** — creata la scheda,
  aggiunta a [[MOC - Strategie]]. Nessun dato ancora raccolto, non è sul
  motore sito.
- [x] Corretta un'affermazione mia troppo negativa su MALAYSIAN_SNR nella
  nota fonte — il trigger attuale è più sofisticato di quanto avevo scritto
  inizialmente (ha già fresh/unfresh, storyline, corpo forte).
- [ ] I 6 proxy dichiarati sul sito (LONDON_BO/RANGE_FADE/WEEKLY_EXP/
  LIQ_VOID/SH_BMS_RTO/SMS_BMS_RTO → riusano un'altra funzione) non sono un
  bug ma vanno ricordati: lo screening sito per queste 6 non dice nulla
  sulla loro vera logica. Su MT5 hanno tutte la loro implementazione reale.

## ✅ Fix applicati oggi (15/07) — codice modificato, non solo vault

Su richiesta esplicita dell'utente di "lavorare all'EA" con ricerca esterna
+ test reali, questi cambi sono stati **implementati nel codice**, non solo
proposti. Vedi [[NEXUS EA - Ricerca Esterna e Test A-B per Strategia]] per
i test A/B completi che li giustificano.

- [x] **`server/bt_verdict.py`** — fix del bug per cui il verdetto per
  strategia usava il campo `executed` (rotto) come gate principale,
  classificando quasi tutto come BLOCCATA/NO_SETUP anche con centinaia di
  trade reali. Ora usa `wins+losses+breakeven` come fallback affidabile.
- [x] **`server/backtest.py` — `sig_sar()`**: sostituito il proxy bacato
  (identico a EMA_PULLBACK) con vero Parabolic SAR (nuova funzione
  `psar_series()`) + allineamento EMA20. Test A/B: PF 1.17→1.28, drawdown
  quasi dimezzato (12.38%→7.81%).
- [x] **`server/backtest.py` — `sig_adx_rsi()`**: aggiunto vero ADX(14)
  Wilder (nuova funzione `adx_series()`), che prima non veniva mai calcolato
  nonostante il nome. Soglia 20 (non 25 "da manuale", testato: peggiora).
  Test A/B: PF 1.26→1.23 (~stabile), drawdown 11.44%→9.72%.
- [x] **`MQL5/Include/NEXUS_v1/NXS_Strategies.mqh` — `NXS_Strat_ADXRSI()`**:
  aggiunta la riga `if(g_adx < 20.0) return s;`. L'ADX reale era già
  completamente disponibile nell'EA (`g_adx`, popolato da `iADX()` in
  `NEXUS_EA_v2.mq5:84`, già usato altrove per il regime di mercato) — non
  serviva nuovo wiring, solo leggerlo dentro il trigger. **Non ancora
  validato su MT5** — serve un backtest isolato (`InpStrategySelector`)
  prima di considerarlo definitivo.
- [ ] **Verificare su MT5** che il fix ADX_RSI migliori davvero (il test A/B
  è sul motore sito, dati Yahoo daily — motore diverso da MT5, vedi
  [[NEXUS EA - Principi]] #5/#8: un miglioramento lì non garantisce lo
  stesso risultato su MT5, va confermato).
- [ ] **SAR MQL5**: verificato che l'implementazione nativa usa già vero
  `iSAR()` (`NEXUS_EA_v2.mq5:88`, `g_hSAR`) — il problema era solo nel
  proxy del sito, non nel codice MQL5. Nessun cambio fatto lato MQL5 per
  SAR. Se il fix ADX_RSI regge su MT5, capire perché SAR nativo (già
  corretto) continua comunque a fallire — probabilmente il problema è
  altrove (bias direzionale trovato in
  [[NEXUS EA - Analisi Trade-Level SAR MACD RSI_DIV]], o parametri SL/TP).

## ⚡ Metodologia corretta (15/07): setup buy/sell indipendenti, non taglio di direzione

Prima versione di questa sezione proponeva di "tagliare gli short" per
SAR/MACD/RSI_DIV — **sbagliato, corretto su feedback diretto dell'utente**.
Rimuovere una direzione è un camuffamento statistico, non una correzione
della strategia. Metodologia corretta, ora in vigore per tutto il lavoro
successivo: [[NEXUS EA - Principi]] #9 e
[[NEXUS EA - Setup Buy-Sell — Framework]] — ogni strategia resta tradabile
sia buy che sell, ma con trigger/TF/parametri **indipendenti per direzione**,
ricostruiti da fonti esterne quando disponibili (vedi `01-Trading/Fonti/`) o
dall'analisi trade-level quando no.

L'analisi trade-level su SAR/MACD/RSI_DIV resta utile come **diagnosi**
(dove il trigger è più debole), non come soluzione:
[[NEXUS EA - Analisi Trade-Level SAR MACD RSI_DIV]].

- [x] Framework "Setup Buy-Sell" definito, primo esempio completo
  (MALAYSIAN_SNR) ricostruito da fonte esterna — vedi
  [[NEXUS EA - Setup Buy-Sell — Framework]].
- [ ] **MALAYSIAN_SNR**: implementare il setup buy/sell ricostruito dalla
  fonte MSNR (vedi framework) — priorità Tier 1, la fonte è già completa.
- [ ] **TURTLE_SOUP / LIQ_SWEEP / SH_BMS_RTO / SMS_BMS_RTO**: ricostruire
  setup buy/sell dal ciclo ZIKIR (Secret of 4.11) e dal pattern
  stop-hunt+BOS (MSNR) — Tier 1.
- [ ] **ORDER_BLOCK / OB_MIT / FVG_CONT / FVG_MIT / IFVG**: ricostruire dalle
  "5 tipologie di Engulfing" (ISL/HSL, Secret of 4.11) — Tier 1.
- [ ] **SAR/MACD/RSI_DIV/ADX_RSI**: nessuna fonte esterna diretta ancora
  raccolta (indicatori classici, non concetti SMC/ICT) — costruire i setup
  buy/sell dall'analisi trade-level esistente + attendere altre fonti
  dall'utente. Tier 2, priorità alta per impatto economico.
- [ ] **SILVER_BULLET/JUDAS_SWING/LDN_REVERSAL/NY_REVERSAL/AMD_*/PO3/OTE_CONT**:
  modelli ICT legati a sessioni specifiche, serve materiale non ancora
  fornito. Tier 3, in attesa.

## Fonti esterne in arrivo (15/07)

L'utente ha iniziato a fornire materiale esterno da incorporare nel vault
come "cervello" di trading (cartella `01-Trading/Fonti/`):
- [x] **MSNR x SMC x ICT (Yanu Emmanuel)** — letto e sintetizzato, vedi
  [[NEXUS EA - Fonte MSNR SMC ICT (Yanu Emmanuel)]].
- [x] **Secret of 4.11 (Ali Yusoff)** — letto e sintetizzato, vedi
  [[NEXUS EA - Fonte Secret of 4111 (Ali Yusoff)]].
- [x] **Chat WhatsApp con Said** — testo completo ricevuto e letto (1370
  righe). Non è un manuale di trading ma cronologia di progetto + esempi di
  ragionamento discrezionale dal vivo. Vedi
  [[NEXUS EA - Fonte Chat WhatsApp (Said)]]. Contiene un riassunto tecnico
  completo dell'EA v2.0.12 scritto dall'utente stesso, il piano mai
  completato per formalizzare il metodo di Said, e la conferma di un bug
  ancora presente in v2.5.0 (vedi sotto).
- [ ] Altre chat/documenti annunciati dall'utente — da leggere e sintetizzare
  con lo stesso metodo (estrarre solo regole azionabili, non trascrivere
  tutto, confrontare con le fonti già presenti e segnalare conflitti come
  fatto per fresh/unfresh MSNR vs Secret of 4.11).

## Piano d'azione — come arrivare a "tutte profittevoli, hedge mantenuto" (15/07)

Obiettivo dichiarato: tutte le strategie attive contribuiscono positivamente
(o restano a rischio minimo/spente) e il portafoglio mantiene la
diversificazione nel tempo scoperta in [[NEXUS EA - Hedge nel Tempo]]. Ordine
di lavoro consigliato, per gruppo:

1. **Consolidare il nucleo che già funziona** (BREAKOUT_ACC, CISD,
   TURTLE_SOUP) prima di toccare il resto — è l'unica parte del portafoglio
   con un track record reale su MT5. Prossimo passo concreto: il test isolato
   delle tre insieme (vedi sotto), non altro tuning. Nota: il sito **non può
   validare questo gruppo** (mai profittevoli lì, motore senza hedge) — la
   fonte di verità è solo MT5.
2. **SAR — ripartire da zero, letteralmente**: nessun test valido esiste
   oggi, né su MT5 (0/6 anni positivi) né sul sito (proxy bacato, identico a
   EMA_PULLBACK). Prima di ritoccare parametri, va (a) riscritta la vera
   logica Parabolic SAR nel proxy sito per poter fare uno screening reale, e
   (b) isolata su MT5 (`InpStrategySelector`) per vedere il comportamento
   grezzo senza interazioni con altre strategie.
3. **MACD — capire se è un problema di segnale o di esecuzione**: il sito
   conferma un edge raw positivo (PF 1.38, 10 anni, dati diversi da MT5) ma
   MT5 reale è pesantemente negativo (-21.1R). Quando segnale e esecuzione
   divergono così tanto, il sospetto principale è l'esecuzione (spread reali
   su M15, sizing, interazione con gate/margine), non il trigger. Test
   isolato MT5 con logging su spread/sizing per ogni trade MACD.
4. **RSI_DIV e ADX_RSI — stessa diagnosi di base**: campione ampio, segnale
   debole anche sul sito (RSI_DIV: PF max 1.09; ADX_RSI: PF 1.26, nella media).
   Probabilmente il segnale stesso ha poco edge reale su XAUUSD daily/M15 —
   non sono casi di "esecuzione rotta" come MACD. Da rivedere la logica di
   ingresso, non solo i parametri SL/TP/HTF.
5. **BJORGUM, TSI, altre "in attesa"**: interessante che BJORGUM abbia PF
   2.47 sul sito (10 anni, 27 trade) ma sia negativa su MT5 (-8.6R, 5/6
   anni) — divergenza simile a TURTLE_SOUP/CISD, probabilmente un altro caso
   "il sito non cattura la timeframe reale H4 e l'esecuzione MT5". Bassa
   priorità rispetto a SAR/MACD/RSI_DIV che pesano di più sul totale.
6. **Una volta sistemate 2-4**: ri-eseguire un backtest 10y segmentato
   completo con le correzioni applicate, per vedere se il portafoglio nel suo
   insieme torna positivo — non giudicare le singole correzioni isolatamente,
   il pattern storico del progetto (vedi [[NEXUS EA - Log Versioni]]) mostra
   che le interazioni tra modifiche contano.

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
  segmento 2020 (88.69% nel 2024) è la conferma pratica del buco. Aggiungere
  un gate tipo `InpMaxTotalDDPct` che blocchi nuovi trade (o riduca il
  rischio) quando l'equity scende oltre una soglia dal massimo storico — non
  solo dall'inizio giornata.
- [ ] **Fixare il proxy `sig_sar()` sul sito** (`server/backtest.py:387`) —
  oggi è un incrocio EMA20/EMA50 identico a `sig_ema_pullback()`, non
  Parabolic SAR. Serve implementare la vera logica (indicatore Parabolic SAR
  + EMA9/EMA21) prima che qualsiasi screening sito su SAR abbia senso. Vedi
  [[NEXUS EA - Motore Sito: Audit e Confronto 10Y]].
- [ ] **(Bassa priorità, strutturale) Il motore sito non supporta posizioni
  multiple/hedge** (`pos` è singolare in `run_backtest()`). Se si vuole usare
  il sito per validare in futuro il nucleo hedge o altre interazioni
  multi-strategia, va esteso a più posizioni concorrenti — oggi è
  strutturalmente impossibile, non solo un limite di dati.
- [ ] **Due sistemi di chiusura per durata massima, indipendenti e non
  coordinati** — bug notato dall'utente il 24/06, **verificato ancora
  presente il 15/07**: `NXS_ManageBreakevenAndTrail()`
  (`NXS_Management.mqh:29`, fallback 4h o ~40 barre del TF via profilo) e
  `NXS_Prot_CheckMaxHold()` (`NXS_Protections.mqh:190`, gate separato
  `InpUseMaxHold`, base 12h scalata con `NXS_TF_LifeFactor`) possono
  chiudere la stessa posizione con logiche di scaling diverse — vince chi
  scatta prima. Da unificare in un solo controllo. Vedi
  [[NEXUS EA - Fonte Chat WhatsApp (Said)]].

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
[[MOC - Trading]] · [[NEXUS EA - Backtest 10Y Segmentato - Analisi]] · [[NEXUS EA - Hedge nel Tempo]] · [[MOC - Strategie]] · [[NEXUS EA - Principi]] · [[NEXUS EA - Motore Sito: Audit e Confronto 10Y]]
