---
type: moc
domain: trading
status: active
tags: [trading, nexus-ea]
created: 2026-07-12
updated: 2026-07-25
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
- **[[NEXUS EA - Test Generale Post-Fix (16-07 notte)]]** — riscreening di tutte
  le 36 strategie DOPO i fix del 16/07 (proxy fedeli, struttura esterna, TP
  dinamico, 7 sessione connesse): 31/36 ora positive sul sito. Per
  SAR/MACD/RSI_DIV/ADX_RSI (i 4 responsabili del 75% della perdita MT5 sui
  6 anni) — nota corretta il 17/07: ADX_RSI ha un trigger MQL5 genuinamente
  nuovo mai testato su MT5 (fix dopo la raccolta dati), SAR/MACD/RSI_DIV no
  (trigger MQL5 invariato, solo il proxy sito era sbagliato) — nessuna
  conclusione sull'esito MT5 prima del test isolato.
- **[[NEXUS EA - Gestione Uscita MFE-MAE (17-07)]]** — questi 4 indicatori
  azzeccano la direzione 70-88% delle volte (analisi MFE/MAE diretta) ma lo
  SL attuale li ferma comunque nel 60-77% dei casi: TP molto più largo +
  breakeven (non trailing) applicato a MACD/ADX_RSI, PF/DD/net migliorano
  nettamente sul sito. SAR/RSI_DIV: nessun miglioramento chiaro trovato,
  config invariata.
- **[[NEXUS EA - Caccia al Bug Esecuzione (17-07)]]** — bug CONFERMATO
  (non solo sospetto): `NXS_StrategySourceTF()` era una tabella
  strategia→timeframe vecchia e disallineata da quella vera, che copriva
  solo 10 strategie su ~30 — tutte le altre (ADX_RSI/SAR/MACD/RSI_DIV/
  BOLLINGER e ~20 altre) finivano con un cap di durata massima piatto di
  12 ore invece dei giorni previsti (`NXS_Protections.mqh`). Corretto.
  Anche un secondo bug indipendente (log CSV di chiusura sempre vuoto).
  Ricerca esterna (SAR+ADX, MACD+ADX, RSI_DIV+conferma) testata sul
  sito: nessun filtro migliora — coerente con un problema di esecuzione,
  non di trigger.
- **[[Sito Backtest Lab - Note Tecniche]]** — come funziona il backend Python/React,
  incluso il problema di deploy Render risolto il 12/07.
- **[[MOC - Strategie]]** — indice delle 36 schede per-strategia (`Strategie/`),
  raggruppate per stato di validazione (validate/pending/fallite/campione piccolo/
  disabilitate/non connesse). Punto di partenza per lavorare strategia-per-strategia:
  aggiornare la scheda e spostarla di gruppo è il modo in cui questo vault resta vivo.
- **[[NEXUS EA - Backtest 10Y Segmentato - Analisi]]** — la validazione più ampia
  fatta finora (6 anni reali di dati, 2019-2024): bug trovati, ranking per strategia,
  perché il fix HTF v2.5.0 non ha funzionato per SAR/MACD/RSI_DIV/ADX_RSI.
- **[[NEXUS EA - Backtest 10Y Segmentato (v2.5.0)]]** — nota scritta in
  parallelo (sessione diversa, stesso dataset): dati grezzi trade-count per
  segmento, il bug di pipeline che duplicava i report, e l'anomalia
  2016-2019 (17/3/59 trade contro 500-1500+ degli anni successivi). Vedi la
  sezione "Nota di riconciliazione" per la discrepanza nei conteggi non
  ancora isolata tra le due note.
- **[[NEXUS EA - Hedge nel Tempo]]** — quali strategie si coprono a vicenda nel
  tempo: il nucleo TURTLE_SOUP+BREAKOUT_ACC+CISD (ridimensionato col segmento 9).
- **[[NEXUS EA - Motore Sito - Audit e Confronto 10Y]]** — audit del codice del
  motore sito: nessun hedge/multi-posizione per design, e il proxy SAR è
  identico a EMA_PULLBACK (non testa mai la vera strategia).
- **[[TODO - Backtest 10Y]]** (cartella `01-Trading/TODO/`) — piano d'azione
  strategia-per-strategia e aggiornamenti da fare appena arriva il segmento 10.
- **[[TODO - Agente Desktop (validazione MT5 post-Dukascopy, 09-08)]]** —
  per chi ha MT5/MetaEditor sotto mano: cosa validare dopo la sessione
  Dukascopy del 09-10/08 (nuovo il 10/08: BREAKOUT_ACC filtrata per regime
  STRONG_TREND, l'unico candidato cross-validato oro+BTC di oggi; nucleo
  hedge BREAKOUT_ACC mai testato insieme, vero LIQ_VOID mai testato —
  dormiente di default, SAR/MACD/RSI_DIV/ADX_RSI da ri-validare con la
  parità tester/live post-remediation attiva).
- **[[NEXUS EA - Ricerca Combinazioni Multi-Strategia (10-08)]]** — tre
  metodi indipendenti (accordo unanime, pipeline gerarchica, voto greedy
  su pool di 20 strategie) per trovare una combinazione che batta la
  singola migliore. Nessuno dei tre ci riesce — MACD da sola resta
  meglio di ogni ensemble provato, inclusa la ricerca dopo aver corretto
  un bug di overfitting nello score dell'ensemble stesso.
- **[[NEXUS EA - Config Demo 15 Strategie (10-08)]]** — piano per un conto
  demo a 15 strategie: scan multi-TF completo (frequenza sì, qualità no
  sui TF bassi), exit-management isolato (nessun miglioramento credibile
  su 15 strategie dopo walk-forward), scoperta di un secondo layer di
  ottimizzazione MQL5 preesistente con bandiera rossa reale su MT5 per
  MACD/FVG_CONT mai risolta.
- **[[NEXUS EA - Riverifica su Storico Ampliato (11-08)]]** — cache
  Dukascopy quasi raddoppiata (2.636 giorni, dal 2019), riverifica di
  tutte le scoperte "buone": CRT confermata in modo schiacciante (15/15
  finestre walk-forward su 3 TF, quasi 20.000 trade), i 5 filtri di
  regime confermati, le 3 buone confermate ma non perfette, RETEST
  ridimensionata (non pronta per il demo senza altro lavoro).
- **[[NEXUS EA - Audit Ricetta Ufficiale vs Baseline Piatta (11-08)]]** —
  verifica se i profili MQL5 già esistenti (mai testati sul motore
  corretto + storico ampio) nascondessero un profilo migliore non
  riconosciuto, come successo con CRT. Risultato: nessuna modifica
  necessaria — FVG_CONT/TURTLE_SOUP/EMA_PULLBACK confermati già ottimali
  (walk-forward 5/5, 4/5, 4/5), il resto alla pari o senza campione
  sufficiente. Nessuna "perla" trovata neanche tra le strategie escluse.
- **[[NEXUS EA - Fase C Recovery Baseline e Rischio Flottante (11-08)]]** —
  primo passo della Fase C (recovery/pyramiding ottimizzati): il recovery
  uniforme già esistente nel motore aiuta CRT/FVG_CONT ma danneggia
  EMA_PULLBACK/SAR — non è un miglioramento universale, conferma la
  richiesta di gestione differenziata per gamba. Scoperto e corretto un
  buco di misurazione: il drawdown esistente è "a trade chiuso", non
  mark-to-market — aggiunto `track_floating_dd` a `run_backtest`.
  Rivelato che CRT ha un drawdown flottante strutturale enorme (stop
  ancorato al wick, non ATR) — non un rischio attivo oggi (`InpEnableGrid
  =false` di default), ma da tenere presente prima di costruire sopra.
- **[[NEXUS EA - CISD_TRUE (versione vera, negativa) e Censimento Completo (11-08)]]** —
  stessa indagine fatta per CRT (versione "vera" scartata perché non
  scattava mai) applicata a THREE_BAR_DELIVERY_BREAK/CISD: sul sito dava
  PF 5.95 ma 0/1067 setup. Sullo storico ampliato spara regolarmente, ma
  il test onesto (walk-forward) è negativo su tutti e 3 i TF — non ogni
  versione scartata è una CRT nascosta. Include anche il censimento
  completo e coerente di tutte le 50 strategie del motore (16 nucleo +
  34 escluse), stesso metodo per tutte.
- **[[NEXUS EA - Riverifica su Storico Ampliato (11-08)]]** (corretta lo
  stesso giorno) — i 5 filtri di regime "confermati due volte" erano un
  artefatto di test (motore semplificato, TF 4h invece del vero TF di
  profilo). Riverificati sul motore vero (`regime_filter` aggiunto a
  `run_backtest`): nessuno regge, walk-forward 1/5-3/5 su campioni
  spesso troppo sottili. TURTLE_SOUP + CHoCH entro 5 barre dopo il sweep
  (idea già diagnosticata il 16/07, mai testata su storico sufficiente):
  promettente su 4h (walk-forward 4/5, drawdown dimezzato), non su 1h.
  SAR e TSI: i fix "trigger vero" trovati a luglio sono già applicati,
  non sono opportunità nuove.
- **[[NEXUS EA - MALAYSIAN_SNR Porting Tier 1 (Specifica Tecnica)]]** —
  architettura completa (non ancora codice) per ricostruire la strategia
  fedele alla fonte originale (Yanu Emmanuel): perché il trigger attuale
  è quasi tautologico, i 5 pilastri mancanti (SNR close-to-open,
  fresh/unfresh/flip, regola di conferma a 2 timeframe, filtro MISS,
  killzone), e un piano d'implementazione in 4 stadi. Contiene anche un
  bug importante scoperto durante i test (`_fetch_dukascopy` ignorava il
  parametro `bars`, tetto silenzioso di 26-104 giorni su 15m/30m/1h) e
  la sua correzione, e — la scoperta più solida della sessione del
  10/08 — il **direction-lock BUY-only su 4h** che regge con campioni
  di 54-114 trade su MACD/TURTLE_SOUP/BREAKOUT_ACC insieme, sempre
  meglio del rispettivo baseline, mai ancora portato in MQL5.
- **[[NEXUS EA - Setup Buy-Sell — Framework]]** — metodologia per ricostruire
  ogni strategia come due setup indipendenti (buy e sell), con il primo
  esempio completo (MALAYSIAN_SNR). **Leggi anche [[NEXUS EA - Principi]]
  #9** prima di proporre di disattivare una direzione.
- **`01-Trading/Fonti/`** — materiale esterno (libri/PDF/chat) mano a mano
  fornito dall'utente e sintetizzato in regole azionabili: al 15/07,
  [[NEXUS EA - Fonte MSNR SMC ICT (Yanu Emmanuel)]],
  [[NEXUS EA - Fonte Secret of 4111 (Ali Yusoff)]] e
  [[NEXUS EA - Fonte Chat WhatsApp (Said)]] (conferma un bug reale ancora
  presente in v2.5.0: due sistemi di durata massima non coordinati).
- **[[NEXUS EA - Ricerca Esterna e Test A-B per Strategia]]** — ricerca web
  + test A/B reali su SAR/ADX_RSI/MACD/RSI_DIV, con **fix già applicati nel
  codice** (sito e MQL5): vero Parabolic SAR, vero filtro ADX su ADX_RSI, fix
  del bug che rompeva lo strumento "Strat Diag" del sito.
- **[[NEXUS EA - Audit Fedeltà Trigger (tutte le 37 strategie)]]** — lettura
  completa di tutte le 37 strategie per verificare che ognuna usi davvero la
  logica del suo nome. 6 bug di proxy trovati e corretti al 16/07 (SAR,
  BJORGUM, MACD, RSI_DIV, BREAKOUT_ACC, LIQ_SWEEP), TSI in attesa di una
  decisione tua sul trade-off frequenza/qualità.
- **[[NEXUS EA - Struttura Interna vs Esterna — Framework]]** — teoria
  (tua, confermata) su swing minori/maggiori come due prospettive
  separate per ogni pattern SMC, non una gerarchia di filtri. Primi test:
  funziona come "due varianti" (LIQ_SWEEP), non come gate extra sullo
  stesso bar (IFVG/TURTLE_SOUP, entrambi peggiorati).

## Remediation dell'audit master (25 luglio 2026)
- **[[NEXUS EA - Remediation Audit v18]]** — revisione completa dei 310 finding
  del master document e implementazione nel codice. Cosa è stato corretto
  davvero, e il limite grosso: **niente di MQL5 è stato compilato né eseguito**.
- **[[DEC - Cambi di comportamento post-remediation]]** — **leggi questa prima di
  confrontare qualsiasi backtest nuovo con uno vecchio.** La parità tester/live
  è ora attiva di default: i numeri cambiano, e i confronti storici non valgono
  più.
- **[[NEXUS EA - Igiene Repository e Duplicati]]** — 257 MB su 448 sono copie
  identiche, cinque coppie di report dichiarano strategie diverse ma sono lo
  stesso file, e il bundle React distribuito contiene ancora le credenziali di
  default.
- **[[TODO - Agente Desktop (consegna remediation)]]** — il piano ordinato per
  chi ha MetaEditor, MT5 e la macchina sotto mano.

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
