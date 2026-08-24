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
- **[[NEXUS EA - Tabella Master Strategie Verificate (24-08)]]** —
  riferimento rapido: configurazione vincente per ciascuna delle 21
  strategie verificate il 24/08 (TF, SL/TP, filtro, direzione, PF),
  senza dover ricostruirla dalle ~15 note sparse. **Consulta questa
  prima se cerchi "qual è la config giusta per X".**
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
- **[[NEXUS EA - Ensemble Riverificato e TP Dinamico su Liquidità (11-08)]]** —
  l'ensemble a voto (segnato "oro") non aveva lo stesso bug dei filtri di
  regime (SL/TP piatto = convenzione flat baseline di tutta la sessione,
  non un difetto), solo lo storico vecchio (60k→110k barre). Riverificato:
  consistente (IS≈OOS) ma non superiore a CRT da sola. TP dinamico su
  liquidità reale (il meccanismo di CRT) esteso a LIQ_SWEEP/FVG_CONT: non
  si trasferisce, walk-forward 2/5-3/5 — probabile causa, in CRT target e
  ingresso condividono la stessa struttura locale, qui no.
- **[[NEXUS EA - Strategie Escluse, Analisi Una-ad-Una (11-08)]]** (in
  corso) — le 34 escluse dal nucleo, una alla volta, stesso metodo.
  MALAYSIAN_SNR_BREAKOUT: chiuso, il vault aveva già la risposta (IS-blind
  trap). Le varianti "_v2": trovati e corretti 3 bug reali mai sistemati
  (freshness/EntryAt50Pct auto-referenziali, fib618/705 invertiti) —
  FVG_CONT_V2 ora promettente (non ancora confermato), SILVER_BULLET_V2
  troppo sottile, OTE_CONT_V2 strutturalmente morto anche corretto.
  **Famiglia SNR/MSNR chiusa (11/08)**: già diagnosticata come
  quasi-tautologica (condizioni contraddittorie), il Pilastro 3 costruito
  apposta per risolverlo non regge su nessun TF; l'ultimo filo aperto
  (gate fuori-range su RETEST) testato col motore vero — non aiuta,
  walk-forward 2/5 su entrambi i TF, era un artefatto dello stesso tipo
  dei filtri di regime (motore standalone, SL/TP sbagliato). Nessuna
  variante regge un test onesto.
- **I due problemi aperti del nucleo, approfonditi (11/08)** — TSI:
  variante "cross da zona estrema" (soglia motivata, mediana del TSI
  assoluto) testata su 1d/4h, **negativa su entrambi** (peggiora su 1d,
  identica ma con meno campione su 4h). Resta senza soluzione. FVG_MIT:
  il trigger valuta ogni gap per mitigazione una sola volta (4-6 barre
  dopo la formazione, mai più tardi) — registro di zone attive fino a
  15 barre (`FVG_MIT_WINDOW`) **promettente su 4h** (campione quasi
  triplicato, walk-forward molto più stabile, range 0.95-1.55 contro le
  oscillazioni 0.39-1.85 della baseline), ma peggiora nettamente su 1h
  (drawdown 58%) — fix specifico al TF naturale, non universale. Vedi
  [[Tsi]] e [[Fvg Mit]].
- **IFVG e SMS_BMS_RTO (11/08)**: stesso fix "CHoCH a finestra di N barre"
  applicato con esiti opposti. IFVG (4h): sbloccata da quasi-zero a OOS
  1.53/10, ma walk-forward volatile (0,0,6.71,7.9,0) — **promettente, non
  confermato**. SMS_BMS_RTO (1d): sbloccata da 0 trade strutturali a un
  campione minimo, ma OOS 0.0/2 e walk-forward quasi tutto perdente —
  **negativo**. Corretta anche una claim vault obsoleta su SMS_BMS_RTO
  ("non testabile sul motore sito", falsa dal 04/08). Vedi [[Ifvg]],
  [[Sms Bms Rto]] e [[NEXUS EA - Strategie Escluse, Analisi Una-ad-Una (11-08)]].
- **NY_REVERSAL (11/08)**: stesso fix "CHoCH a finestra" applicato,
  stavolta **negativo** — campione cresce 3-4x ma PF scende verso 1.0 e
  drawdown esplode (30m: 6.3%→25.4% IS). Conferma importante: il fix non
  è universale, aiuta solo dove il pattern di base ha edge reale offuscato
  dal timing (IFVG/FVG_MIT/TURTLE_SOUP), non dove il pattern non ha edge
  (SMS_BMS_RTO/NY_REVERSAL). Vedi [[Ny Reversal]].
- **Famiglia SCALP_* (11/08) — miglioramento reale**: le 4 SCALP_*
  (BB_FADE/EMA/RANGE_BRK/RSI_SNAP, 15m) avevano drawdown 35-79% pur con
  PF vicino/sopra 1. Il filtro `regime_filter=STRONG_TREND` (motore vero)
  dimezza il drawdown su tutte e 4, confermato IS/OOS e su ogni finestra
  walk-forward, PF stabile/migliore su 3 delle 4. Non serve una nuova
  strategia — è un parametro runtime già esistente, quindi una
  **configurazione raccomandata** per l'uso pratico di queste 4. Vedi
  [[Scalp Family]].
- **Giro veloce completato (11/08)**: coperte tutte le strategie escluse
  rimanenti — BOLLINGER/RANGE_FADE (proxy, quasi pareggio su 1d), LIQ_VOID
  (proxy corretto, eredita lo stato SOLIDA di FVG_CONT), ORDER_BLOCK_V2
  (trappola IS-blind, non promuovibile), OTE_CONT v1 (decadimento
  classico, chiuso), SH_BMS_RTO v1 (claim vault obsoleta corretta, debole
  su entrambi i lati — v2 resta la versione da preferire), SILVER_BULLET
  v1 (overfitting su 1h e 4h, filtro regime non aiuta). Bilancio
  complessivo del giro: 2 miglioramenti reali, 1 promettente non
  confermato, il resto negativi onesti o già chiusi. Dettaglio completo in
  [[NEXUS EA - Strategie Escluse, Analisi Una-ad-Una (11-08)]].
- **[[NEXUS EA - Rischio a Livelli e Moltiplicatore da Streak (12-08)]]** —
  richiesta esplicita dell'utente (conto ~200-300 EUR, 0.5% flat troppo
  poco e sotto il lotto minimo XAUUSD). Costruiti: (1) 5 fasce di rischio
  per-strategia (0.3%-5.0%, prima flat) sulle 16 del nucleo, incrociando
  PF reale MT5 + Python OOS/WF, con le red flag di esecuzione note che
  sovrascrivono un buon backtest; (2) moltiplicatore da perdite consecutive
  per-strategia (`NXS_StreakRisk.mqh`, nuovo modulo) — dichiaratamente un
  martingale, ma cappato (max 2x, +30%/step, 9 perdite per il tetto) e
  scoped per-strategia, guardrail concordati esplicitamente prima di
  costruirlo; (3) `InpMaxRiskAtMinLotPct` alzato 0→8 (senza, il floor sul
  lotto minimo restava inutilizzato su un conto così piccolo); (4)
  `InpMaxAggregateRiskPct` 15→25 (i tier più alti lo avrebbero reso un
  collo di bottiglia); (5) floor minimo sullo stop di CRT (0.3×ATR),
  necessario ora che il suo tier sale, per la riserva di rischio flottante
  già nota. Tutto scritto ma **non compilato/testato** (sessione remota
  senza MT5) — verifica live richiesta prima dell'uso su conto reale.
- **[[NEXUS EA - Riverifica via Sito su Storico Esteso 2016-2026 (12-08)]]**
  — richiesta esplicita dell'utente: rifare il censimento attraverso il
  motore DEL SITO (Render), non `run_backtest` diretto. Scoperto che il
  sito ha 3 anni di storico in più del file locale usato tutta la sessione
  (2016-08 contro 2019-05) — aggiunto supporto `bars`/`bar_range`
  all'endpoint `/api/backtest/run` (mancava, sempre 800 barre di default)
  e deployato. 45/59 strategie completate puliteremente; 14 (soprattutto
  15m/alta-frequenza: SCALP_*, OTE_CONT*, SH_BMS_RTO*) non hanno mai
  completato dopo retry — limite reale della piattaforma (il sito è anche
  crashato una volta per il carico, poi riavviato da Render), non un bug
  nostro. **Nessuna sorpresa che ribalti un verdetto**: CRT e TURTLE_SOUP
  quasi identici tra le due finestre (conferma robustezza), ADX_RSI/
  THREE_BAR_DELIVERY_BREAK guadagnano campione con la finestra più ampia
  (conferma, non smentisce, i verdetti già dati sui campioni sottili D1).
- **[[NEXUS EA - Demo Multi-Timeframe Pronta (12-08)]]** — richiesta
  esplicita dell'utente (martingale spento, test in demo su tutti i TF).
  Verificato che è già il comportamento di default (nessun `.set`
  necessario): `InpUseStrategyProfiles=true` attiva sia il TF
  per-strategia sia il gate `NXS_Profile_Enabled` che decide chi apre
  davvero. Scoperta collaterale: **THREE_BAR_DELIVERY_BREAK non ha mai
  avuto un'implementazione MQL5** (solo Python) — il nucleo davvero
  tradabile in demo è di 15 strategie, non 16. File di convenienza
  `.set` creato per rendere la config esplicita/riproducibile, checklist
  pre-demo inclusa (nulla ancora compilato/testato in questa sessione).
- **[[NEXUS EA - Riverifica Master-Slave Bias sul Motore Vero (12-08)]]** —
  la claim del piano utente ("BREAKOUT_ACC come Master ha aiutato SAR/
  FVG_CONT/TSI/MACD") veniva da `phase3c_bias_pipeline.py`, un motore
  parallelo con SL/TP piatto hardcoded — mai riverificata dopo la scoperta
  dello stesso difetto sui 5 filtri di regime. Aggiunto `master_bias=` a
  `run_backtest()` (stesso principio di `regime_filter`, ogni slave gira
  col proprio SL/TP reale) e riverificato IS/OOS/WF su XAUUSD 4h.
  **Risultato misto, non un fallimento totale**: FVG_CONT migliora in modo
  coerente su OGNI finestra walk-forward (5/5 vs 4/5 baseline, drawdown IS
  quasi dimezzato) — il segnale più convincente per un vettore
  "extra-strategia" trovato finora in sessione. SAR migliora ma più
  debolmente. TSI e MACD: nessun beneficio reale (IS peggiora, walk-forward
  invariata). La claim originale non regge per tutte e 4 come affermato.
- **[[NEXUS EA - TSI Ricerca Dedicata Uscite (12-08)]]** — ricerca a
  griglia piena per il secondo "problema aperto" del nucleo (dopo il
  segnale troppo sottile del batch sulle 58). Baseline vero OOS PF1.35/
  DD2.97%/n31 (IS sotto pareggio). 330 combinazioni, 79 sopra baseline,
  i migliori raggruppati sulla stessa zona (non un picco isolato).
  Vincitore: SL2.0×/TP6.0×/BE1R/HTF on/trail2.0× — OOS PF1.35→**2.41**,
  DD2.97%→**1.99%**, walk-forward 1.76-2.95 (mai sotto 1.76). Resta la
  scoperta più fragile della sessione (22-24 trade OOS, D1) — ipotesi
  forte, non un fatto acquisito. **Portata in MQL5** insieme a CRT e
  FVG_CONT (non ancora compilata/testata).
- **[[NEXUS EA - Ottimizzazione Uscite Tutte le 58 Strategie (12-08)]]** —
  richiesta esplicita dell'utente: estendere la griglia SL/TP/BE/trailing
  a tutte le 58, non solo il nucleo. Griglia dimezzata per stare nei
  tempi (58 strategie, alcune 15m/30m molto pesanti) — **confermato che
  questo fa perdere il vincitore migliore**: per CRT/FVG_CONT (dove
  esiste anche la ricerca dedicata a griglia piena) il batch trova un
  risultato nettamente peggiore, usare i numeri della ricerca dedicata
  per quelle due. 19/58 migliorate, ma solo 10 con campione OOS robusto
  (n≥100) — le altre 9 sono indizi da riverificare, non conclusioni.
  MACD/EMA_PULLBACK migliorano il PF ma peggiorano il drawdown (stesso
  trade-off già visto). TSI (problema aperto del nucleo) mostra il primo
  segnale di miglioramento mai trovato, ma su campione troppo sottile
  (n=21) — prossimo candidato per una ricerca dedicata.
- **[[NEXUS EA - Ottimizzazione Uscite Strutturali CRT e FVG_CONT (12-08)]]** —
  griglia SL/TP × breakeven × trailing (script fornito dall'utente,
  adattato al vero `run_backtest`: niente df/params, chiavi vere, e
  scoperto che per CRT `atr_sl`/`atr_tp` sono INERTI perché la sua SL/TP è
  sempre quella ancorata al wick/sweep — sweepati solo be/trailing).
  **CRT**: BE a 1R + trailing 1×ATR insieme migliora DD 36.5%→29.1% e PF
  1.25→1.38, walk-forward più stabile. **FVG_CONT**: lo script (come
  quello di riferimento) sceglieva solo il PF più alto ignorando il DD —
  quel candidato (sl1.0/tp4.0) alza il PF a 1.43 ma quasi raddoppia il DD
  (13.5%→20.9%). Verificato a mano un candidato "duale" (sl2.0/tp3.0,
  niente BE/trailing): PF 1.29→1.33 più modesto ma DD scende a 12.1% ed è
  l'unico profilo la cui walk-forward non scende mai sotto pareggio —
  coerente con l'obiettivo dichiarato (ridurre il DD), non ancora portato
  in MQL5.
- **[[NEXUS EA - Incidente Sicurezza e Setup Desktop (13-08)]]** — bridge
  token e license key trovati in chiaro in 45 `.set` + 103 report `.htm`
  già pubblici su GitHub (entrambi ora invalidati, repo ripulito dal
  tracking, commit ancora da fare); worker locale + MetaTrader configurati
  e collegati a Render; bug reale trovato e corretto (`NXS_Profile_Risk`
  senza firma, mai compilato dopo il 12/08) — l'EA ora compila pulito.
  **13/08 (stesso giorno)**: FVG_MIT_WINDOW portata in MQL5 (registro di
  zone a 15 barre, confermato due volte) e sostituisce FVG_MIT nel nucleo
  demo.
- **[[NEXUS EA - Malaysian SNR Test Annuale Basso Timeframe (13-08)]]** —
  QML base non manca di segnali su M15/M5/M1, ma nessun rapporto
  setup→esecuzione supera sviluppo+validazione: M30→M5 è l'unico con 3/3
  fold di sviluppo positivi ma fallisce in validazione (PF 0.55,
  -0.36R); M1 è economicamente morto (costi ≈-0.377R/trade). Resta
  disabilitata live, nessun cambio di codice. V4 consigliata: filtro di
  contesto su M30→M5, testato una variabile alla volta.
- **[[NEXUS EA - 50 Maestri del Trading, Sintesi e Confronto col Nucleo (14-08)]]**
  — i 5 pilastri (trend/breakout, price action/asta, macro, quant/rischio,
  momentum/mean-reversion) incrociati col nucleo: gran parte già presente
  (SMC/ICT = teoria dell'asta, TURTLE_SOUP = Raschke, HTF gate = filtro
  regime), il pilastro macro/fondamentale quasi tutto non applicabile a un
  EA tecnico su oro. 3 candidati nuovi testati (Donchian Turtle, Darvas
  Box, Z-Score breakout) — tutti con lo stesso pattern sospetto (IS debole,
  OOS gonfiato): probabile artefatto di regime (trend recente dell'oro),
  non edge confermato. Nessuno promuovibile senza riverifica IS/OOS
  scambiati.
- **[[NEXUS EA - Motore Costi e Riverifica Nucleo (14-08)]]** — scoperto che
  nessun test della sessione (CRT inclusa) aveva mai applicato costi
  realistici; trovato e corretto un bug reale (`spread_r = spread/risk_dist`
  senza cap, equity negativa su stop stretti). CRT chiusa in modo
  definitivo dopo aver testato ogni combinazione floor/breakeven/trailing
  sotto costi (mai sopra DD 100%). Riverifica nucleo-wide (flat poi ricetta
  corretta, stesso errore metodologico trovato e fissato): solo 5
  sopravvivono (SAR, LONDON_BO, MACD, EMA_PULLBACK, FVG_CONT). 4 strategie
  disattivate nel codice e compilate (CRT, TURTLE_SOUP, SH_BMS_RTO_V2,
  FVG_MIT_WINDOW). Variante SAR flip-only promettente (PF 1.96 vs 1.38
  baseline, DD 4.2% vs 10.2%), ADX gate invece peggiora.
- **[[NEXUS EA - Riverifica Walk-Forward 5 Finestre e Dipendenza da Regime (15-08)]]**
  — le 5 "sopravvissute ai costi" del 14/08 NON sono walk-forward stabili:
  stesso pattern su tutte (PF cresce dalla finestra più vecchia alla più
  recente, 3-4/5 finestre sotto pareggio), `regime_filter` ADX-based non
  risolve, TF più bassi peggiorano sistematicamente (ipotesi utente
  testata e smentita: 15m sempre 0/5 finestre). Diagnosi confermata senza
  bug: `avg_loss_mfe_r=0.78`, `near_miss_loss_pct=55.8%` su SAR 15m — la
  direzione è spesso giusta ma il rumore a TF basso fa girare il prezzo
  prima del TP. Nessuna delle 5 è pronta per live/demo in size.
- **[[NEXUS EA - Audit Coerenza Catalogo Completo 67 Strategie (16-08)]]** —
  debug esteso a tutte le 67 strategie registrate (dopo il nucleo, già
  verificato con scenari sintetici formali): 46 pulite, 2 senza segnali
  nel campione (non bug), **2 bug reali trovati** — CRT/CRT_MINSTOP_FILTER
  (22-33% dei trade con target già dietro l'entry, nessun controllo
  floor sul lato TP a differenza dello SL) e famiglia FVG_MIT/
  FVG_MIT_WINDOW/IFVG_CHOCH_WINDOW/ORDER_BLOCK_V2/SILVER_BULLET_V2 (SL
  calcolato dal bordo della zona assumendo prossimità all'entry, che non
  sempre regge). Nessuna delle strategie coinvolte è nel nucleo live,
  nessuna azione urgente.
- **[[NEXUS EA - Filtro di Regime e Portafoglio 5 Strategie (16-08)]]** —
  prima risposta concreta a "come creiamo un sistema profittevole":
  filtro di regime vero (Efficiency Ratio di Kaufman, lookback ~167
  giorni) migliora 4 finestre su 5 su 4 strategie indipendenti (limite
  noto ai punti di svolta, capito e documentato, non aggirabile).
  Portafoglio a 5 strategie con questo filtro: **primo risultato netto
  positivo su 7 anni di tutta l'indagine**, sia a costi retail che ECN,
  ma richiede capitale ≥€500-1000 (a €300 il conto può fallire per il
  pavimento del lotto minimo) e drawdown resta severo (50-93%) — non
  ancora pronto per soldi veri. **Aggiornamento stesso giorno**: trovato
  che il lotto minimo (non il target di rischio) era il vero vincolo,
  fino a €61 di rischio reale per trade indipendente dal capitale;
  aggiunto un tetto diretto in € sul rischio per trade (non solo sui
  lotti) — risultato: DD sotto 11% (da 33-93%) E profitto più alto
  insieme, non un compromesso, validato su due metà della storia
  separate. Il candidato più solido di tutta l'indagine ad oggi.
- **[[NEXUS EA - Stop Strutturale M5 su Segnali H1 (16-08)]]** — stop
  ancorato al minimo/massimo delle ultime 12 candele M5 (invece di un
  multiplo ATR) su 16 strategie diverse: SAR/MACD confermate, ICHIMOKU
  nuova candidata. Ipotesi "serve uno stop diverso per famiglia" (sweep/
  rejection/divergenza, già nel motore) testata e chiusa in negativo su
  tutte e 6 le strategie riprovate — incluso LIQ_SWEEP/TURTLE_SOUP_CHOCH,
  lo "Spring" di Wyckoff, chiuso anche da questo lato. **Addendum 17/08**:
  il portafoglio in euro col nuovo stop risolve meccanicamente il vincolo
  del lotto minimo (rischio reale mediana $23→$6.84) ma esplode comunque
  (DD100%+) — o R:R eccessivo (serie di 159-172 perdite consecutive) se
  il target resta ATR-largo, o costi dominanti (stessa lezione di CRT)
  se il target si restringe col nuovo stop. Nessuna delle due varianti
  batte il candidato del pomeriggio (stop ATR + tetto-€). Sottoprodotto:
  catalogo esteso a 30 strategie in più, **Z_SCORE_BREAKOUT nuova
  scoperta solida** (retail PF1.29/4/5, ECN PF1.71/5/5).
- **[[NEXUS EA - Idee da Script TradingView Esterni (17-08)]]** — triage
  di una decina di script TradingView condivisi dall'utente: la
  maggior parte duplica concetti già nel catalogo o richiede volume
  reale (assente su XAUUSD OTC). Due idee nuove testate: MACD+SMA200
  (ChartArt) promettente su 4h (PF1.39/4/5) ma campione troppo sottile
  (34 trade); falso breakout su swing MAGGIORE (20/15 barre, non
  sessione/giornaliero come i 3 tentativi precedenti di sweep) — il
  candidato migliore, 234 trade su 1h, ECN PF1.57 su 5/5 finestre,
  retail borderline. **Addendum 24/08**: falso breakout su swing maggiore
  validato due-metà-storia (nessuna metà negativa) → promosso e portato
  in MQL5 come `SWING_FALSEBREAK`. Altri 4 script testati: Hull Suite e
  ML Adaptive SuperTrend (k-means su ATR) entrambe bocciate (retail
  a/sotto pari, ECN marginale senza plateau); HHLL già bocciato il 17/08;
  KZP non testato (indicator puro, nessuna regola di ingresso propria).
  `Z_SCORE_BREAKOUT` (scoperto il 17/08, vedi nota Stop Strutturale M5)
  portato in MQL5 lo stesso giorno.
- **[[NEXUS EA - CRT Range H4 con Conferma M5 (24-08)]]** — ipotesi
  dell'utente: range da candela H4 chiusa, conferma di falso breakout su
  candele M5 (non stessa TF come il CRT classico), uscita fissa 1:2.
  Edge grezzo reale ma sottilissimo (PF1.08 senza costi, win rate 35%
  contro 33.3% di pareggio) — collassa con i costi (retail PF0.04, ECN
  PF0.23, 15.197 trade) perché lo stop mediano è ~$1.22: la stessa
  candela di sweep può restare valida per più barre M5 consecutive,
  producendo trade ripetuti a rischio quasi nullo sullo stesso livello.
  Il floor 0.3×ATR (che salva il CRT classico) qui NON basta: scarta il
  93% dei trade e i superstiti restano negativi. Bocciata, causa
  diagnosticata non solo osservata.
- **[[NEXUS EA - Attacco alla Dipendenza dal Rally 2023-2026 (24-08)]]** —
  la prima correzione REALE trovata (dopo settimane di sola diagnosi) al
  problema più vecchio dell'indagine. Tre leve testate su SAR/MACD (4h):
  breakeven sul near-miss **rigettato** (peggiora sempre — uccide i
  vincenti che ritracciano e poi continuano, più di quanto salvi i
  perdenti); soglia ER adattiva a percentile mobile migliora ma con
  finestre rumorose, più debole del floor; **floor di volatilità
  assoluta (percentile ATR mobile, ortogonale al filtro ER di forma) —
  la scoperta**: MACD retail meta1 1.27→1.39-1.41, SAR 1.01→1.09 (5/5
  finestre), FVG_CONT 1.15→1.19, tutti confermati su un plateau
  0.2-0.5, non un picco isolato. Non universale (LONDON_BO non ne ha
  bisogno, verificato non assunto). Combinare floor+soglia-adattiva
  peggiora, non si sommano. Divario meta1/meta2 ridotto sostanzialmente,
  non eliminato — finestra 2020-11→2022-04 resta la più debole in
  assoluto.
- **[[NEXUS EA - Screening Catalogo Completo e Confluenze (24-08)]]** -
  applicata la ricetta ER+floor a tutte le 67 strategie del catalogo:
  9 nuove baseline verificate due-meta-storia (DONCHIAN_TURTLE quasi
  identica tra le due meta, ADX_RSI non dipende nemmeno dal rally,
  MALAYSIAN_SNR_BREAKOUT/DARVAS_BOX/AMD_CONT/SAR_FLIP/EMA_PULLBACK/
  SAR_ADX20/BREAKOUT_ACC) - EMA_PULLBACK ribalta il verdetto negativo del
  16/08. LIQ_VOID scartata dal conteggio (segnale identico a FVG_CONT).
  Poi confluenze tra strategie/indicatori diversi (richiesta esplicita):
  MACD come conferma di momentum funziona bene su ADX_RSI (PF1.27->1.48
  retail, entrambe le meta migliorano) ma NON generalizza a
  DONCHIAN_TURTLE (nessun effetto) - confermata l'avvertenza dell'utente,
  un filtro buono per una non lo e' per un'altra. Zona di ritracciamento
  Fibonacci su EMA_PULLBACK inconcludente (campione crolla a 9 trade,
  troppi filtri impilati) - non una tesi falsificata, un disegno da
  rifare.
- **[[NEXUS EA - Espansione Baseline con Ricetta Variabile (24-08)]]** -
  su richiesta dell'utente, ricetta VARIABILE per strategia (griglia
  SL/TP + stop nativo con floor mai provato sopra) invece della ricetta
  unica. 4 candidati forti nuovi: OTE_CONT (il migliore della giornata,
  PF1.61/entrambe le meta forti - il verdetto "fragile" di prima era un
  problema di SL/TP non di segnale), FVG_CONT_V2, TSI (molto piu' solida
  con SL1.0/TP6.0), TURTLE_SOUP (**ribalta 3+ rifiuti precedenti** - il
  floor ATR non era mai stato provato sopra il suo stop nativo, da
  riverificare vista la storia). CRT/CRT_MINSTOP_FILTER confermate
  definitivamente rotte anche col floor. Trailing stop (chandelier,
  nessun target fisso) testato sulle deboli residue: LIQ_SWEEP
  **doppiamente confermata** (PF1.07, meta 1.06/1.08 - quasi identico al
  risultato SL fisso con un meccanismo di uscita indipendente, la
  conferma piu' solida della giornata). STRUCT_REACT peggiora col
  trailing (era ok col target fisso) - il tipo di gestione va scelto per
  strategia. Totale: 14 nuove baseline verificate due-meta-storia oltre
  alle 4 gia' solide.
- **[[NEXUS EA - Famiglia Sessione e SCALP su M15-M30 (24-08)]]** -
  JUDAS_SWING/SILVER_BULLET/NY_REVERSAL/AMD_REVERSAL/PO3/WEEKLY_EXP/
  SCALP_* testate sul loro TF nativo (M15/M30) con uscita a fine
  giornata invece del target multi-ATR usato altrove: **negativo su
  tutta la linea**, 26 combinazioni (13 strategie x 2 TF), zero baseline
  profittevoli, retail PF mai sopra 0.59 nemmeno allargando lo stop.
  Tre assi indipendenti provati (TF, ampiezza stop, timing di uscita) -
  nessuno risolve. Nessuna aggiunta al totale di 14.
- **[[NEXUS EA - Split BUY-SELL e Timeframe D1 (24-08)]]** - probabilmente
  la scoperta piu' grande della giornata: split BUY/SELL su 10 strategie
  bocciate/marginali - **pattern quasi universale**, BUY nettamente sopra
  SELL ovunque (BOLLINGER e STRUCT_REACT superano PF2.7 con 5/5 finestre
  SOLO sul lato long). 7 baseline rescue genuine (BOLLINGER/STRUCT_REACT/
  FVG_MIT/BJORGUM/ICHIMOKU/TSI_EXTREME/RSI_DIV). Interpretazione onesta:
  quasi certamente un'altra faccia della dipendenza dal rally/trend
  rialzista secolare, non un edge indipendente - una leva di esposizione,
  non una nuova tesi. Poi timeframe D1 (mai testato prima oggi): 4
  baseline nuove/rafforzate solide (LIQ_SWEEP il salto piu' netto,
  EMA_PULLBACK l'unica senza dipendenza dal rally, BREAKOUT_ACC, TSI) +
  alcune con aggregato ottimo ma prima meta' fragile (OTE_CONT m1=0.30!)
  da non contare senza riverifica. **Totale giornata: 25 baseline**.
- **[[NEXUS EA - Diagnosi Onesta del BUY-only (24-08)]]** - l'utente ha
  giustamente obiettato che BUY-only profittevole durante un rally puo'
  essere solo beta, non edge. Verificato con PF per-finestra CON LE DATE
  (non solo il conteggio): **scoperta metodologica** - le finestre
  "equal-count" su segnali rari NON sono equal-calendario, una finestra
  puo' coprire 4 anni con 14 trade mentre le altre 4 coprono meno di 2
  anni. Verdetto differenziato, non piu' uniforme: STRUCT_REACT e' la
  piu' genuina (SELL era ECCELLENTE, PF2.85, nella finestra vecchia
  laterale, poi flip verso BUY nel rally recente - vera logica
  bidirezionale). BJORGUM **rimossa dalla lista baseline** - BUY e SELL
  sostanzialmente pari e sotto pareggio nella finestra vecchia, il PF
  alto aggregato e' beta mascherato, sospetto dell'utente confermato dai
  dati. BOLLINGER declassata a "watch". Combinazione BUY-only+D1
  deliberatamente NON eseguita (D1 avrebbe lo stesso problema, peggiore).
- **[[NEXUS EA - Nuovi Ingredienti (Stop Struttura, Allineamento D1, Giorno) 24-08]]** -
  FVG_MIT con allineamento D1 al posto del filtro ER e' la scoperta piu'
  pulita della giornata: retail PF1.48, **tutte e 5 le finestre** tra
  1.35 e 1.83 (nessuna debole), copertura genuina 2020-2026. LDN_REVERSAL
  con stop strutturale (swing 10 barre) da' il primo risultato pulito di
  tutta la giornata per questa strategia ma campione sottile (31).
  Filtro giorno-della-settimana: nessun miglioramento su nessuna delle 6
  strategie riprovate.
- **[[NEXUS EA - Portafoglio a 20 Strategie (24-08)]]** - prima
  simulazione di portafoglio con la lista aggiornata (stessa disciplina
  del 16/08: euro reali, tetto €40, max 2 concorrenti). Risultato
  headline positivo (+€2.725 retail, +€4.383 ECN su conto €1000) ma
  **trainato quasi solo da SAR** (contributo maggiore del netPnL totale)
  - 6-4 strategie su 16-20 sono NETTE PERDENTI dentro il portafoglio pur
  essendo profittevoli da sole (LIQ_SWEEP la peggiore, -€207, nonostante
  fosse "doppiamente confermata" in isolamento). Causa: bucket FIFO a 2
  slot penalizza le strategie a bassa frequenza quando competono con
  SAR/MACD/ADX_RSI (migliaia di segnali grezzi). Sweep max_concorrenti:
  piu' slot = piu' profitto ma DD esplosivo non-lineare (a 20 slot il
  portafoglio VA IN PERDITA, DD100%) - prova diretta che molte delle 20
  strategie sono correlate, non indipendenti. Il problema ora non e'
  piu' "quali strategie sono buone" ma **come allocare il rischio tra
  loro** - analisi di correlazione e criterio di priorita' nel bucket
  ancora da fare.
- **[[NEXUS EA - Correlazione tra le 20 Strategie (24-08)]]** - spiega
  la causa del portafoglio squilibrato: DARVAS_BOX e DONCHIAN_TURTLE
  correlate al **99.7%** (praticamente la stessa strategia), un cluster
  trend-following {SAR/SAR_ADX20/MACD/ADX_RSI/BREAKOUT_ACC/DARVAS_BOX/
  DONCHIAN_TURTLE/FVG_CONT} correlato 0.45-0.84 tra loro. Solo 5 vere
  diversificatrici: STRUCT_REACT (correlazione NEGATIVA con SAR/
  SAR_ADX20 - hedge naturale genuino), EMA_PULLBACK, FVG_MIT, OTE_CONT,
  LIQ_SWEEP - non a caso le stesse che il portafoglio a 2 slot escludeva
  o penalizzava. Due tentativi di correzione (slot dedicati
  cluster/diversificatrici, deduplicazione semplice) NON risolvono -
  serve un budget di rischio indipendente per strategia, non un
  aggiustamento di parametri. Su richiesta dell'utente, in pausa per ora
  a favore dell'ottimizzazione per-strategia.
- **[[NEXUS EA - STRUCT_REACT con Fibonacci Esaurimento-Reverse (24-08)]]** -
  prima ottimizzazione individuale (su richiesta dell'utente, dopo la
  correlazione). Fibonacci come USCITA/reverse (non filtro d'ingresso,
  idea esplicita dell'utente): livello di esaurimento a estensione
  1.618 dello swing 20 barre, chiude il trade li' e apre un reverse a
  lotto ridotto. Non promosso - la baseline gia' fortissima (PF2.65,
  5/5 finestre) non migliora: il trigger scatta raramente (8/50, il TP
  a 6xATR e' gia' competitivo) e i pochi reverse isolati mostrano PF
  esattamente 1.00 pre-costi (nessun edge nemmeno grezzo, ma campione
  troppo sottile per un verdetto definitivo).
- **[[NEXUS EA - Ottimizzazione LIQ_SWEEP (24-08)]]** - seconda
  ottimizzazione individuale. Stop nativo dello sweep peggiora (a
  differenza di TURTLE_SOUP). Allineamento D1 migliora un po'. **BUY-only
  e' la scoperta pulita**: retail PF1.73, le due meta' IDENTICHE
  (1.73/1.73), tutte e 5 le finestre positive, verificato con le date -
  la finestra piu' vecchia (2020-2024) e' gia' forte da sola (PF1.42),
  diverso dai rescue BUY-only bocciati ieri sera (li' la finestra vecchia
  era debole/beta). LIQ_SWEEP promossa da borderline a candidata solida.
- **[[NEXUS EA - Ottimizzazione OTE_CONT (24-08)]]** - terza
  ottimizzazione individuale. Allineamento D1 (sostituisce ER) e' di
  nuovo il piu' pulito: retail PF1.61->1.83, **tutte e 5 le finestre
  positive** (erano 3/5), campione quasi raddoppiato. Trailing e
  BUY-only migliorano ma con piu' instabilita' tra finestre; SELL-only
  scartata. **Seconda vittoria di fila per l'allineamento D1** (dopo
  FVG_MIT ieri sera) - da provare sistematicamente sulle altre baseline.
- **[[NEXUS EA - Sweep Sistematico Allineamento D1 (24-08)]]** - testato
  su 14 baseline non ancora provate: **NON generalizza**, solo 3/14
  migliorano (LONDON_BO, TSI, EMA_PULLBACK - tutte gia' con filtro ER
  borderline). Le 11 gia' forti con ER (SAR/MACD/FVG_CONT/
  DONCHIAN_TURTLE/ADX_RSI/ecc, tutte 5/5 o 4/5 finestre pulite)
  **peggiorano sistematicamente** col D1-alignment - il campione quasi
  raddoppia ma la qualita' cala (m1 crolla quasi ovunque). L'allineamento
  D1 e' uno strumento di SALVATAGGIO per strategie con filtro debole, non
  un upgrade universale - stessa lezione del floor ATR di ieri.
- **[[NEXUS EA - Sweep Sistematico BUY-SELL (24-08)]]** - split BUY/SELL
  su altre 14 baseline: **13/14 migliorano nettamente sul lato BUY**,
  verificato con campioni ampi (60-1471 trade, non i pochi trade dei
  rescue bocciati ieri sera) e finestra piu' vecchia genuinamente sopra
  pareggio (ADX_RSI-BUY: F0 2020-2024, n=145, PF1.27 - controllato con
  le date, non solo il conteggio). TSI-BUY il migliore (PF2.03), MACD
  l'unica dove il miglioramento non vale la pena (SELL resta
  marginalmente positivo). Tabella master aggiornata con tutte le nuove
  config.
- **[[NEXUS EA - CORREZIONE Il BUY-only e Regime-Dipendente non Universale (24-08)]]** -
  l'utente ha giustamente rimesso in dubbio lo sweep BUY/SELL di prima.
  Isolata la finestra genuinamente laterale (2020-11→2023-10, gia'
  classificata il 15/08): **il verdetto si RIBALTA** - SELL domina su
  tutte le 6 strategie controllate (ADX_RSI: BUY PF0.23 vs SELL PF2.53!).
  Il "13/14 migliorano con BUY-only" di prima era vero solo
  nell'aggregato 2019-2026 (a maggioranza rialzista) - un flip di
  regime reale (BUY vince nei trend, SELL nel laterale), non un lato
  strutturalmente migliore. Stessa trappola equal-count-non-equal-
  calendario di ieri sera, qui su campioni piu' grandi (145 trade)
  quindi piu' ingannevole. Verifica su altro mercato tentata ma
  inconcludente (solo 2 anni via Yahoo per BTCUSD/EURUSD, dati non
  comparabili). Prossimo passo naturale: direction-lock CONDIZIONATO al
  regime (BUY se trend, SELL se laterale), non BUY-only statico.
- **[[NEXUS EA - Verdetto Finale SCALP (24-08)]]** - su richiesta
  dell'utente, altri 2 ingredienti provati per rendere profittevoli le
  SCALP_*. Filtro ER lungo (167gg, standard del catalogo): uccide il
  99.9%+ dei segnali (contraddizione di scala - un trend di mesi quasi
  mai coincide con un trigger di microstruttura M15). ER a finestra
  corta (12.5-50h) + target stretto da scalp (0.5/1.0xATR): PF
  catastrofico 0.05-0.12 (costi dominanti, stessa saga CRT). **5
  ingredienti indipendenti provati su due sessioni, nessuno funziona** -
  non piu' un problema di ricetta, verdetto finale: le SCALP_* cosi'
  come codificate non hanno edge sfruttabile, servirebbe un segnale
  nuovo, fuori scope.
- **[[NEXUS EA - Riscrittura SCALP con Ricerca Esterna (24-08)]]** - su
  richiesta dell'utente, riscrittura vera (non un filtro) informata da
  ricerca web (overlap London-NY 12-16 UTC, liquidity sweep reversal -
  fonti citate). Restringere le SCALP_* esistenti all'overlap aiuta ma
  non basta (resta sotto pareggio). Segnale NUOVO (sweep swing M15 +
  rientro, R:R 1:2, overlap-only): **peggio delle originali**, PF
  0.15-0.61. Diagnosi quantificata: risk_dist mediano $3.45, costo
  tipico $2.37 (69% dello stop!), win rate grezzo 32.3% contro 33.3% di
  pareggio - il segnale non ha edge nemmeno prima dei costi. Stesso
  meccanismo (sweep+rientro) funziona su H1 (SWING_FALSEBREAK, PF1.29)
  ma non su M15 - non e' l'idea, e' la SCALA: costi fissi retail non
  permettono economia su stop di pochi dollari/minuti. **7 tentativi
  indipendenti su due sessioni, tutti falliti** - chiuso definitivamente,
  servirebbe uno strumento con spread molto piu' piccolo (fuori scope,
  nessun dato reale per altri simboli).
- **[[NEXUS EA - Drawdown per Strategia e Sizing Dinamico (24-08)]]** -
  drawdown massimo per strategia (in R): scala con la FREQUENZA dei
  trade, non solo col PF - SAR ha PF piu' basso del gruppo diversificatrici
  ma DD piu' alto (98.3R vs 7.5R di STRUCT_REACT) semplicemente perche'
  fa 30x piu' trade. Aumentare la size in drawdown contenuto (1.5-2.0x
  quando DD<3-5R): funziona su STRUCT_REACT (+55% rendimento, DD solo
  7.5R->9.6R) ma va calibrato (2.0x peggiora LIQ_SWEEP rispetto a 1.5x).
  **Stesso meccanismo su SCALP_RANGE_BRK (PF0.71) non cambia quasi
  nulla** (-691R baseline -> -675/-685R con leva) - dimostrato con i
  numeri, non solo spiegato: il sizing scala l'ampiezza dei trade, non
  l'aspettativa - su un sistema a valore atteso negativo moltiplica
  proporzionalmente le stesse perdite, non le recupera.
- **[[NEXUS EA - Ottimizzazione EMA_PULLBACK (24-08)]]** - quarta
  ottimizzazione individuale, risolve la tensione D1(pochi trade)/
  4h(PF modesto). Due leve, entrambe migliorano invece di scambiare:
  D1 SENZA floor (mai verificato su questa strategia) porta n da 32 a
  39 E il PF sale (2.41->2.57, 5/5 finestre) - il floor ATR era
  leggermente controproducente qui, terzo caso di un ingrediente non
  universale. 4h+D1-align+trailing 3.0xATR (mai provato) porta il PF
  da 1.42 a 1.87 sullo stesso campione ampio (241). Due config
  complementari ora nella tabella master, non piu' un compromesso.
- **[[NEXUS EA - Ottimizzazione FVG_MIT (24-08)]]** - quinta
  ottimizzazione individuale, il salto piu' grande trovato oggi su una
  singola strategia: trailing 3.0xATR (mai provato) quasi raddoppia il
  PF rispetto al miglior target fisso (1.58->2.72), tutte e 5 le
  finestre positive, stesso campione (79). EMA100 D1 batte EMA50 in
  modo consistente (segnale di trend piu' lento si adatta meglio alla
  tesi "mitigation" che aspetta gia' un ritorno) - non ancora combinato
  col trailing.
- **[[NEXUS EA - Ottimizzazione Z_SCORE_BREAKOUT (24-08)]]** - sesta
  ottimizzazione individuale, su una delle 2 strategie gia' in MQL5.
  BUY-only sembrava pulitissimo (m1=1.57/m2=1.71, quasi identiche) ma
  la verifica laterale immediata rivela **zero trade prima del
  2024-04** - il filtro di regime GIA' incorporato nel segnale
  (bull_regime=close>SMA200) lo rende strutturalmente ancora piu'
  dipendente dal rally delle altre 6 corrette prima, non promosso.
  Trailing 3.0xATR invece e' un miglioramento reale e pulito (1.35->
  1.38, simmetrico, su tutto lo storico) - non ancora applicato al
  codice MQL5 gia' in produzione, richiede modifica separata.
- **[[NEXUS EA - Ottimizzazione MALAYSIAN_SNR_BREAKOUT (24-08)]]** -
  settima ottimizzazione individuale, risultato onesto: **nessun
  miglioramento trovato**. Trailing si avvicina ma non supera mai il
  target fisso gia' noto (PF1.93, 5/5 finestre); D1-align peggiora
  nettamente (stessa firma di "non aiuta chi e' gia' ben filtrato con
  ER"). Verifica laterale fatta subito: stessa direzione delle altre
  ma campione troppo sottile (n=6) per confermare. Config invariata.
- **[[NEXUS EA - Ottimizzazione TSI (24-08)]]** - ottava ottimizzazione
  individuale, la piu' forte del blocco "altre solide" (BUY-only
  PF2.03, n=134). Verifica laterale fatta subito: n=13, PF0.39,
  sumR=-8.9 - stessa direzione delle altre gia' viste ma campione
  troppo sottile per confermare. Trailing provato (2.0/2.5/3.0xATR):
  peggiora sempre rispetto al target fisso 6.0xATR gia' in uso -
  nessun cambiamento, config invariata.
- **[[NEXUS EA - Ottimizzazione SAR_FLIP (24-08)]]** - nona
  ottimizzazione individuale. Verifica laterale: n=8, PF0.31, sumR=-5.5
  - stessa direzione delle altre, campione troppo sottile. Trailing
  2.0xATR adottato al posto del target fisso: PF1.78->1.82, ma
  soprattutto riequilibra le due meta' della storia (m1 1.40->1.64,
  prima dipendeva troppo dalla seconda meta').
- **[[NEXUS EA - Ottimizzazione FVG_CONT_V2 (24-08)]]** - decima
  ottimizzazione individuale. Verifica laterale non informativa (n=2,
  campione troppo piccolo anche solo per indicare una direzione).
  Trailing 2.0xATR sullo stop nativo (strutturale, legato alla FVG) e'
  un miglioramento pulito: PF1.68->2.03, 5/5 finestre in entrambi i
  casi, due meta' equilibrate. 3.0xATR ha PF piu' alto ma solo 3/5
  finestre e sbilanciato verso fine storico - non promosso.
- **[[NEXUS EA - Ottimizzazione AMD_CONT (24-08)]]** - undicesima
  ottimizzazione, chiude il blocco "altre solide". Verifica laterale:
  n=14, PF0.37, sumR=-8.5 - stessa direzione delle altre. Trailing
  (peggiora in modo monotono col multiplo) e D1-align (peggiora
  nonostante campione quasi raddoppiato) entrambi scartati - nessun
  cambiamento. Bilancio del blocco: solo SAR_FLIP e FVG_CONT_V2 hanno
  trovato un miglioramento reale col trailing, TSI e MALAYSIAN_SNR
  no - non e' un ingrediente universale nemmeno dentro lo stesso blocco.
- **[[NEXUS EA - Ottimizzazione SAR e Tentativo Direction-Lock (24-08)]]** -
  dodicesima ottimizzazione, prima del nucleo storico. Trailing
  2.0xATR adottato (PF1.51->1.64, campione piu' grande della giornata,
  n=1471). Primo tentativo concreto dell'idea "direction-lock per
  regime" citata nella correzione BUY-only: classificatore D1 (ER a
  120gg) etichetta bene il laterale 2021-2023, ma il generatore di
  segnale SAR produce quasi solo BUY anche li' (94.6% del campione) -
  un gate esterno non basta, serve un segnale SELL nativo distinto.
  Tentativo onestamente documentato come fallito.
- **[[NEXUS EA - Ottimizzazione MACD (24-08)]]** - tredicesima
  ottimizzazione. Unica del nucleo storico rimasta simmetrica (BUY-only
  non conveniva), quindi nessuna verifica laterale necessaria. Trailing
  2.0xATR e' uno dei miglioramenti piu' netti della giornata: PF1.46->
  1.72 (+18%), campione grande (n=1498), 5/5 finestre in entrambi i
  casi, completamente simmetrico - nessun rischio di beta di rally.
- **[[NEXUS EA - Ottimizzazione FVG_CONT (24-08)]]** - quattordicesima
  ottimizzazione. Verifica laterale: n=25, PF0.43, coerente con le
  altre. Trailing 2.0xATR adottato: PF1.51->1.63 e riequilibra quasi
  perfettamente le due meta' (1.64/1.63), ma perde una finestra su
  cinque (l'ultima, PF0.82, sotto breakeven) - segnalato onestamente
  invece di nasconderlo dietro il PF aggregato.
- **[[NEXUS EA - Ottimizzazione LONDON_BO (24-08)]]** - quindicesima
  ottimizzazione, chiude il nucleo storico (5/5). Verifica laterale:
  n=8, PF0.0 (nessun trade vincente li'), coerente con le altre.
  Trailing 2.0xATR e' un miglioramento su entrambi gli assi: PF1.69->
  1.83 E finestre piu' solide (5/5 contro 4/5) - adottato. 2.5xATR ha
  PF piu' alto (2.18) ma solo 3/5 finestre, scartato per lo stesso
  motivo gia' visto oggi su FVG_CONT_V2/MALAYSIAN_SNR_BREAKOUT.
  **Bilancio nucleo storico**: tutte e 5 le strategie ora hanno
  trailing 2.0xATR come miglioramento adottato (SAR, MACD, FVG_CONT,
  LONDON_BO, gia' Z_SCORE_BREAKOUT con 3.0xATR) - il trailing e'
  risultato l'ingrediente piu' consistente su questo blocco, anche se
  non universale sull'intero portafoglio (vedi blocco "altre solide"
  dove ha funzionato solo su 2/5).
- **[[NEXUS EA - Ottimizzazione ADX_RSI (24-08)]]** - sedicesima
  ottimizzazione, prima del cluster trend-following. Verifica laterale
  gia' fatta (il flip piu' netto della giornata: BUY0.23/SELL2.53).
  Trailing 2.5xATR e' il miglioramento piu' pulito visto finora: PF
  1.77->2.20 (+24%), 5/5 finestre, le due meta' praticamente identiche
  (2.20/2.21) - nessun compromesso da segnalare.
- **[[NEXUS EA - Ottimizzazione SAR_ADX20 (24-08)]]** - diciassettesima
  ottimizzazione, cluster trend-following. Verifica laterale: campione
  ampio n=83, PF0.34, sumR=-54.3 - conferma solida della stessa
  direzione. Trailing 2.0xATR adottato: PF1.49->1.61, 5/5 finestre
  come il baseline, su un campione enorme (n=1000).
- **[[NEXUS EA - Ottimizzazione BREAKOUT_ACC (24-08)]]** - diciottesima
  ottimizzazione. Verifica laterale: n=18, PF0.64, coerente con le
  altre. Trailing scartato: ogni variante peggiora la robustezza delle
  finestre (3/5 o 2/5 contro il 4/5 del target fisso) nonostante
  qualche PF aggregato piu' alto - config invariata.
- **[[NEXUS EA - Ottimizzazione DONCHIAN_TURTLE e DARVAS_BOX (24-08)]]** -
  diciannovesima/ventesima ottimizzazione, chiudono il cluster
  trend-following. Testate insieme (correlate 99.7%, numeri quasi
  identici come atteso). Trailing scartato per entrambe: collassa le
  finestre (5/5->2-4/5) su tutti i multipli provati. **Chiude il
  ciclo di ottimizzazione individuale sulle 19 strategie verificate**:
  11/19 hanno trovato un miglioramento reale (quasi sempre trailing),
  8/19 nessuno (config invariata) - vedi il bilancio aggiornato in
  [[NEXUS EA - Tabella Master Strategie Verificate (24-08)]]. Restano
  solo le 2 provvisorie (TURTLE_SOUP, LDN_REVERSAL) da riverificare.
- **[[NEXUS EA - Riverifica TURTLE_SOUP e LDN_REVERSAL (24-25-08)]]** -
  primo plateau-check (sensibilita' ai parametri) su entrambe le
  provvisorie rimaste. **LDN_REVERSAL promossa**: plateau su 16
  combinazioni swing x RR, e la config nota (swing10/RR3.0) e' anche
  il punto piu' bilanciato della griglia, non il PF piu' alto -
  buon segno anti-overfitting. **TURTLE_SOUP resta provvisoria**:
  plateau sul target confermato ma 3 finestre su 5 sono flat-o-negative
  (0.68/0.99/0.94) e c'e' un'asimmetria BUY1.75/SELL0.70 non ancora
  spiegata. Chiude la revisione di tutte le 21 strategie candidate.
- **[[NEXUS EA - Correzione Trailing Z_SCORE_BREAKOUT, il TP fisso lo annullava (25-08)]]** -
  tentativo di portare il trailing trovato ieri nel codice MQL5 gia' in
  produzione, fermato prima di scrivere codice. Il motore live
  (`NXS_TrailingATR.mqh`) sposta solo lo SL, il TP resta un ordine
  fisso - un meccanismo diverso dal chandelier puro (nessun TP) testato
  ieri. Verificato: con il TP fisso ancora attivo il trailing e' PIATTO
  o leggermente peggiorativo (PF1.32-1.34 contro 1.35 baseline), NON
  1.38 come sembrava ieri. Il miglioramento vero richiede rimuovere il
  TP fisso - un cambio di rischio piu' consequenziale, non fatto senza
  conferma esplicita dell'utente. Nessuna modifica al codice in questo
  turno.
- **[[NEXUS EA - Riverifica Hull Suite e ML Adaptive SuperTrend con BUY-SELL e Laterale (25-08)]]** -
  riapertura di 2 verdetti "chiusi" prima della disciplina laterale di
  oggi (script TradingView esterni, erano "borderline ECN-only, non
  promosse"). Con floor+BUY-SELL+verifica laterale: **Hull Suite
  resta non promossa** (SELL laterale vicino al pareggio, PF0.99,
  pattern debole). **ML Adaptive SuperTrend promossa**: SELL laterale
  PF1.88 (n=11) - un flip genuino nella stessa fascia di SAR/ADX_RSI,
  non solo beta mascherato. Primo caso in cui riaprire un verdetto
  pre-disciplina-laterale produce una vera promozione - da considerare
  per altri "borderline ECN-only" archiviati con la stessa firma.
- **[[NEXUS EA - Riapertura BOLLINGER RSI_DIV ICHIMOKU TSI_EXTREME (25-08)]]** -
  seguito diretto della riapertura Hull Suite/ML SuperTrend: queste 4
  erano state scartate SOLO in forma simmetrica, mai testate BUY/SELL.
  **BOLLINGER(=RANGE_FADE) e RSI_DIV promosse** (SELL laterale forte:
  PF3.34 n=10 e PF1.36 n=21 rispettivamente - flip genuini). ICHIMOKU
  inconcludente (campioni n=2-6). TSI_EXTREME resta rifiutata (BUY-only
  aggregato gia' sotto pareggio). **3 nuove promozioni in totale oggi**
  dal filone "riapertura verdetti pre-disciplina-laterale" - bilancio
  finale: 23 strategie solide, aggiornato nella tabella master.
- **[[NEXUS EA - Filtro Elliott Wave Multi-Timeframe, il nuovo ingrediente universale (25-08)]]** -
  prima implementazione concreta dell'idea Elliott Wave dell'utente:
  ZigZag + regole classiche a 5 onde (onda2 non ritraccia sotto onda1,
  onda3 non e' la piu' corta, onda4 non sovrappone onda1) su 4h, usato
  come filtro per sopprimere segnali quando un impulso appena si e'
  esaurito. Su richiesta dell'utente ("il sistema e' frattale, si
  ripete da TF piu' grande a piu' piccoli") esteso a multi-timeframe:
  **unione 4h+D1** (basta un timeframe esaurito, non serve la
  confluenza di entrambi - l'AND e' quasi inerte) e' la combinazione
  vincente, la terza scala 1h non aggiunge nulla (troppo rumorosa).
  Validato su 8 strategie: **7/8 migliorano** (ADX_RSI 1.77->2.04, SAR
  1.51->1.65, TSI 2.03->2.25, ecc.), quasi sempre senza contropartite -
  il candidato piu' vicino a un ingrediente universale trovato finora.
  Unica eccezione STRUCT_REACT (peggiora, coerente col suo pattern di
  resistere a ogni filtro extra). **Esteso a tutte le 25 strategie del
  catalogo (copertura completa)**: 21/25 migliorano (14 nettamente,
  incluse 3 - BREAKOUT_ACC/DONCHIAN_TURTLE/DARVAS_BOX - che avevano
  resistito al trailing, e TURTLE_SOUP dove risolve proprio la
  debolezza - finestre instabili 2/5->3/5 - che la teneva
  "provvisoria"), 2 neutre, 1 marginale, 1 peggiora (STRUCT_REACT) - il
  tasso di successo piu' alto di ogni ingrediente trovato in 2 giorni.
  Nessuna modifica al codice MQL5, solo ricerca.
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
