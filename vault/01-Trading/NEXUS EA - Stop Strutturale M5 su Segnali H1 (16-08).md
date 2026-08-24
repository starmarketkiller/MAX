---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, stop-loss, m5, walk-forward]
created: 2026-08-16
updated: 2026-08-16
---

# NEXUS EA — Stop Strutturale M5 su Segnali H1 (16/08)

## Perché

Osservazione dell'utente: gli stop ATR non rispecchiano la struttura reale
del grafico, e il problema del pavimento del lotto minimo (vedi
[[NEXUS EA - Filtro di Regime e Portafoglio 5 Strategie (16-08)]]) si può
attaccare da un altro lato — non solo con un tetto in euro, ma rendendo lo
stop davvero più stretto e strutturale, come CRT già faceva col suo stop
ancorato al wick.

## Il meccanismo

Segnale H1 valutato alla chiusura della barra `i` (stessa logica `sig_*`
già auditata in `backtest.py`, nessuna reimplementazione). Entrata a
MERCATO all'apertura della barra `i+1` (lezione open-vs-close di CRT:
mai un'entrata a limite dentro la barra del segnale, quella è la fonte
dell'hindsight bias trovato lì). Stop = minimo/massimo delle ultime 12
candele M5 (~1h) STRETTAMENTE PRIMA dell'apertura della barra `i+1` (dati
`data_cache_m5/dukascopy_xauusd_m5.json`, dal 2021-11-29), con un pavimento
di 0.3×ATR(H1) per evitare stop degeneri. Target invariato: `tp_mult ×
ATR(H1)[i]` (stesso ATR noto al momento del segnale). `swing_bars=12` e
`floor_atr=0.3` sono valori di primo tentativo, **mai tarati con uno
sweep di robustezza** (a differenza del tetto-euro del pomeriggio,
validato su un plateau) — quanto segue è un primo screening pulito, non
una conferma definitiva.

## Test 1 — 16 strategie, stop generico (`m5_structural_stop_broad_16-08.py`)

H1 reale 2019-02→2026-08 (32.496 candele), filtro di regime ER attivo
(lookback 4000 barre H1 ≈ stessa finestra temporale del 4h, soglia
0.045), walk-forward a 5 finestre, costi retail_standard ed ecn scalati
al prezzo storico.

**Solide:**
- **MACD**: retail PF 1.38 (4/5 finestre), ECN 1.95 (5/5) — 2495 trade,
  robusta anche a costi retail.
- **SAR**: retail PF 0.96 (3/5, quasi pari), ECN 1.45 (5/5).
- **ICHIMOKU** (mai testata prima su questo motore): retail PF 1.18
  (3/5), ECN 1.64 (**5/5**) — pulita ma campione piccolo (135 trade), da
  confermare su campione più ampio prima di fidarsene.

**Borderline (regge solo a costi ECN):**
- DONCHIAN_TURTLE: retail 0.99, ECN 1.31 (4/5).
- ADX_RSI: retail 0.80, ECN 1.21 (4/5), campione ampio (2368) ma retail
  chiaramente sotto pari.

**Bocciate anche con lo stop migliore:** RSI_DIV, BOLLINGER,
STRUCT_REACT, SH_BMS_RTO_V2, ORDER_BLOCK (campione troppo piccolo, 26
trade), LIQ_SWEEP, TURTLE_SOUP_CHOCH — tutte PF<1 su retail. IFVG: zero
segnali col filtro di regime attivo nel campione.

**Nota**: LONDON_BO e FVG_CONT (buone nel nucleo ATR-based) qui NON
confermano un risultato "eccezionale" ipotizzato in una sessione
precedente non salvata su file — LONDON_BO retail 0.88/ECN 1.14 su soli
140 trade totali (28 a finestra, oscillazioni PF 0.19→2.92, rumore su
campione piccolo). Questo script è la versione autorevole e riproducibile.

## Test 2 — stop nativo per le 6 bocciate (`native_structural_stop_16-08.py`)

Ipotesi dell'utente: forse le bocciate hanno bisogno di un tipo di stop
diverso, non generico. Ogni famiglia ha già nel motore un livello di
invalidazione NATIVO, più specifico alla tesi del trade del generico
"minimo/massimo dell'ultima ora":
- LIQ_SWEEP / TURTLE_SOUP_CHOCH: wick dello sweep via `_sweep_ext_at()`
  ± 0.5×ATR (stessa convenzione di `_turtle_soup_sl_tp`).
- SH_BMS_RTO_V2: `ind["shbms_v2_sl"]`, già precalcolato nel motore.
- STRUCT_REACT: wick della candela di rejection stessa ± 0.3×ATR.
- RSI_DIV: estremo della divergenza (il minimo/massimo più profondo tra
  le due barre confrontate) ± 0.3×ATR.
- BOLLINGER: estremo della barra di touch ± 0.3×ATR.

**Risultato: nessun miglioramento, anzi la consistenza walk-forward
peggiora su tutte e 6.** PF aggregato si muove di pochi punti in entrambe
le direzioni (rumore), ma le finestre positive scendono quasi ovunque a
0-1/5 (contro 0-3/5 con lo stop generico). Esempio: SH_BMS_RTO_V2 ECN
passa da PF 1.15 (3/5) a PF 1.03 (4/5 finestre ma sumR solo +4.4R su 233
trade — sostanzialmente piatto). LIQ_SWEEP peggiora su entrambi i preset
(retail 0.78→0.69, ECN 1.02→0.88).

**Conclusione**: per queste 6, il problema non è il TIPO di stop — è che
il segnale grezzo non ha edge sufficiente a coprire i costi reali, con
nessuna delle due filosofie di stop provate. In particolare per
LIQ_SWEEP/TURTLE_SOUP_CHOCH questo chiude anche la domanda sollevata dal
confronto con lo "Spring" di Wyckoff (stesso pattern: sweep + rientro) —
non era lo stop ATR il problema, il pattern stesso non regge ai costi su
questo storico, con nessuno stop provato finora.

## Addendum 17/08 — il portafoglio in euro, e la ragione per cui lo stop stretto non basta

Ricostruito il portafoglio in euro (SAR+MACD+ICHIMOKU, poi anche
SAR+MACD+LONDON_BO+FVG_CONT per un secondo parere sulla diversificazione)
con lo stop M5. Confermato meccanicamente l'obiettivo: la distribuzione
di `risk_dist` scende da mediana $23 (stop ATR) a mediana **$6.84** (stop
M5), e il rischio forzato dal lotto minimo (0.01) ora COINCIDE quasi
sempre col target desiderato — il vincolo del lotto minimo è
effettivamente risolto.

**Ma il portafoglio esplode comunque** (maxDD 100%+ in quasi ogni
combinazione di conto/rischio testata, entrambi i gruppi di strategie).
Motivo trovato scomponendo win-rate/R medio/serie di perdite: lasciando
il target invariato (multiplo di ATR, indipendente dal nuovo stop
stretto), il rapporto rischio/rendimento è esploso a 7-15R medio per
vincita, il win-rate è crollato al 22%, e su ~7000 trade una serie di
**159-172 perdite consecutive** è comparsa in entrambi i gruppi testati
(non solo nel trio più correlato SAR/MACD/ICHIMOKU — anche nel gruppo
diversificato SAR/MACD/LONDON_BO/FVG_CONT) — nessun dimensionamento a
rischio fisso sopravvive a una serie così lunga su un conto piccolo.

Corretto forzando un target fisso a 3R (proporzionato al NUOVO stop,
non più ATR indipendente): la serie massima scende a 57 (molto meglio),
ma **l'edge aggregato collassa** (retail PF 0.71, ECN 1.18 appena sopra
pari) — perché lo stesso costo fisso in $ (spread+slippage) pesa molto
di più in termini di R quando il rischio reale per trade è minuscolo
($2-7 invece di $23). **È la stessa identica lezione della saga CRT**
(stop stretto = costi dominanti), tornata da un'altra porta.

**Conclusione**: lo stop strutturale M5 risolve il vincolo meccanico del
lotto minimo, ma lo scambia con uno dei due problemi già noti — R:R
eccessivo (serie di perdite ingestibili) se il target resta ATR-largo, o
dominanza dei costi (stessa lezione di CRT) se il target si restringe
proporzionalmente. Nessuna delle due varianti produce un portafoglio
euro-denominato vivibile su conto piccolo. Il candidato più solido per
un conto piccolo resta quello del pomeriggio (stop ATR + tetto-€ diretto
sul rischio, [[NEXUS EA - Filtro di Regime e Portafoglio 5 Strategie (16-08)]]),
non questo.

## Correzione 17/08 — il filtro di regime non va applicato alla cieca

L'utente ha fatto notare un problema metodologico reale: il filtro di
regime (Efficiency Ratio ≥0.045, "solo mercati in trend", calibrato oggi
pomeriggio per SAR/MACD/LONDON_BO/FVG_CONT) è stato applicato senza
distinzione a TUTTE le ~50 strategie testate in questa giornata, incluse
quelle mean-reversion (RSI_DIV/BOLLINGER/BB_SQUEEZE/TSI_EXTREME) — che
per costruzione cercano l'edge nei mercati LATERALI, l'opposto di quello
che il filtro seleziona.

Verificato con un confronto diretto (nessun filtro / solo ER<0.045
laterale / solo ER≥0.045 trend) su tutte e 5:
- **RSI_DIV, BOLLINGER, TSI, TSI_EXTREME**: PF resta negativo/piatto
  (0.64-0.85) in TUTTE e 3 le condizioni — il verdetto negativo regge,
  non era un problema di filtro.
- **BB_SQUEEZE — sì, era proprio questo il problema**: col filtro trend
  (quello usato oggi) il campione crollava a 17 trade, scartata per
  "troppo pochi trade". Col filtro **laterale** (coerente con la sua
  tesi: un breakout dopo compressione emerge tipicamente fuori da un
  trend consolidato) sale a **PF 1.45 su 4/5 finestre** (n=26, ancora
  sottile ma il verdetto cambia). Bocciata prima per il motivo sbagliato.

**Lezione**: il filtro di regime è uno strumento, non un default
universale — va scelto in base alla tesi della strategia (trend-
following → filtro trend; mean-reversion/compressione → filtro laterale
o nessun filtro), non applicato meccanicamente a tutto il catalogo.

## Addendum 17/08 (2) — griglia SL/TP + filtro HTF, confronto con MT5 reale

Richiesta dell'utente dopo aver visto un agente parallelo validare SAR su
tick MT5 reali (SL1.0/TP6.0, HTF on/off): perché non avevamo mai provato
questo asse (griglia SL/TP sistematica + filtro HTF) su SAR o sulle altre
bocciate di oggi? Risposta onesta: oggi l'asse scelto era un altro (stop
M5 vs ATR); una griglia SL/TP era già stata fatta il 12/08 per l'intero
catalogo ma non con l'HTF come leva esplicita per SAR.

**Su SAR** (`run_backtest` diretto, motore canonico, ultimo anno circa,
4h e 1h, costi retail): risultati in linea con quelli MT5 dell'agente
parallelo per la stessa config (SL1.0/TP6.0 HTF=off: PF1.29/DD18.03% qui
contro PF1.44/DD18.77% su MT5 — stesso ordine di grandezza, buona
conferma incrociata tra motori diversi). Ma la griglia ha trovato di
meglio: **SL1.5/TP4.0 HTF=off, PF1.40/DD8.89%** su 4h — il miglior
risultato per SAR di tutta l'indagine, drawdown meno della metà delle
config a stop più largo. Su 1h tutto peggiora nettamente (PF1.05-1.21,
DD 19-48%) — 4h resta il timeframe giusto per SAR, confermato.

**Sulle 9 bocciate/borderline di oggi** (SAR_ADX20, SAR_FLIP,
BREAKOUT_ACC, DARVAS_BOX, TSI, LIQ_SWEEP, TURTLE_SOUP, STRUCT_REACT,
SH_BMS_RTO — griglia 4 combinazioni SL/TP × HTF on/off, storico intero +
split a due metà): **nessuna salvata**. PF tra 0.28 e 0.77 ovunque, DD
90-100% quasi sempre, coerente su entrambe le metà — non era un problema
di parametri, l'edge non c'è. Nota: per TURTLE_SOUP e SH_BMS_RTO la
griglia SL/TP è risultata INERTE (stesso comportamento già noto per
CRT — il loro stop è sempre quello strutturale ancorato al wick, mai
quello ATR impostato dal parametro).
Script: `grid_htf_rescue_17-08.py`.

## Sottoprodotto utile: catalogo esteso con stop nativo per famiglia

Estesa la classificazione stop-nativo (sweep/rejection/nativo-precalcolato/
generico-M5, per ispezione automatica del codice sorgente di ogni
`sig_*`) a ~30 strategie del catalogo mai testate in questa indagine.
Quasi tutte restano deboli su costi retail. **Unica nuova scoperta
solida: Z_SCORE_BREAKOUT** (stop generico M5) — retail PF 1.29 (4/5
finestre), ECN PF 1.71 (5/5 finestre), 557 trade — il miglior risultato
retail di tutto il giro, meglio di SAR/ICHIMOKU su questo stesso stop.
Borderline: SAR_ADX20 (retail 0.93 quasi pari, ECN 1.39 su 5/5), SAR_FLIP
(retail esattamente 1.00, ECN 1.43 su 4/5). Confermato ancora una volta
che la famiglia sweep (TURTLE_SOUP, CISD_TRUE, SH_BMS_RTO*) non regge con
nessuno stop provato finora — tre tentativi diversi, stessa risposta.
Script: `full_catalog_native_stop_17-08.py`.

## Addendum 24/08 - Z_SCORE_BREAKOUT portata in MQL5

`NXS_Strat_ZScoreBreakout()` aggiunta a `NXS_Strategies.mqh` (bucket
STRAT_BREAKOUT_ACC, famiglia FAM_TREND - e' un breakout con filtro di
regime SMA200, non uno sweep). Stop NON via profilo ATR ma strutturale
M5 vero e proprio, come descritto sopra: minimo/massimo delle 12 candele
M5 chiuse piu' recenti lette live da `PERIOD_M5` (non dalla cache JSON
offline usata dallo script Python), pavimento 0.3xATR(H1), target
4.0xATR(H1) - stessa formula di `full_catalog_native_stop_17-08.py`.
selector_index 42 (dopo SWING_FALSEBREAK=41). Registro canonico
aggiornato (knowledge/strategy_database.json, 38->39 live) e rigenerato -
questa e' l'unica delle due porting di oggi che ha gia' una controparte
research in `server/backtest.py` (`sig_z_score_breakout`), quindi il
registro la marca `research_implementation=True,
research_parity=APPROXIMATE` invece di NOT_IMPLEMENTED.

Stesso gap dichiarato di SWING_FALSEBREAK: filtro di regime ER non
ancora live, non compilata (nessun MetaEditor in questa sessione) -
verifica locale richiesta prima di demo/live.

## Collegamenti
[[MOC - Trading]]
