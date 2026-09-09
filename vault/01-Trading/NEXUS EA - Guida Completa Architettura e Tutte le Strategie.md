---
type: reference
domain: trading
status: active
tags: [trading, nexus-ea, architettura, strategie, riferimento]
created: 2026-09-09
updated: 2026-09-09
---

# NEXUS EA — Guida completa: architettura e tutte le strategie

Riferimento tecnico su come funziona davvero il codice (non un verdetto di
trading — per quello vedi le note vault datate e il "Piano di Test Master").
Scritto leggendo `MQL5/Experts/NEXUS_EA_v2.mq5` e tutti gli include in
`MQL5/Include/NEXUS_v1/` così come sono oggi (09/09/2026).

---

# PARTE 1 — Architettura generale

## 1.1 Ciclo di vita

**`OnInit()`** (`NEXUS_EA_v2.mq5:630`): in ordine — rifiuta l'avvio su conto
non-hedging (il modello "1 position = 1 trade logico" non regge su netting),
verifica il token del bridge web, azzera il pool di handle indicatore,
carica il registro degli intenti/learner, imposta il magic base, calcola il
saldo di inizio giornata, costruisce il profilo simbolo (rifiuta se il
simbolo non è in whitelist), crea gli handle indicatore, inizializza i
runtime settings e applica il preset di rischio (`NXS_ApplyPreset`, vedi
§1.7 sul bug storico), verifica la licenza, carica lo stato persistito,
fa un audit di coerenza registro/selettore, e solo alla fine armazza la
sincronizzazione web (non blocca l'avvio con chiamate di rete).

**`OnTick()`** (riga 981): guardia tick-stantio → aggiorna spread/Virtual SL →
rollover giornaliero (`NXS_Prot_OnNewDay` se cambia giorno) → protezioni →
aggiorna indicatori → calcola regime/sessione/HTF-bias/velocity/AMD/sweep →
gestisce TUTTE le posizioni aperte (breakeven, trailing, split, grid,
piramide, SLReclaim, ProfitReclaim — vedi §1.6, girano ad OGNI tick,
indipendentemente da quale strategia le abbia aperte) → **poi**, solo su
una NUOVA barra del timeframe di ingresso, valuta i segnali delle
strategie e prova ad aprire. La valutazione segnali/apertura ha **tre
modalità mutuamente esclusive** selezionate dagli input (`InpDataCollectionMode`,
`InpUseInstitutionalCore`, `InpUseStrategyProfiles` — controllate in
quest'ordine, la prima vera vince e la funzione esce subito dopo):

1. **Raccolta dati** (`InpDataCollectionMode`): apre OGNI segnale valido a
   lotto fisso piccolo, una posizione per strategia alla volta, solo
   sicurezza dura (preflight). Serve a vedere quali strategie hanno edge
   senza escluderne nessuna. Solo demo.
2. **Modello istituzionale** (`InpUseInstitutionalCore`): raggruppa i
   segnali per direzione in un'unica decisione (`NXS_Institutional_Decide`)
   e apre 1 posizione con SL/TP scalati sul "tier" di conferma.
3. **Profili per-strategia** (`InpUseStrategyProfiles`, **questa è la
   modalità usata da tutti i test isolati fatti finora nel progetto**):
   ogni strategia apre in indipendenza col SUO profilo (SL/TP/HTF/TF,
   da `NXS_StrategyProfiles.mqh`), una posizione alla volta, senza i gate
   soft (MTF/velocity/exhaustion/confluenza) e senza grid/recovery — la
   stessa logica "pulita" con cui è stato calibrato il motore Python del
   sito.

Se **nessuna** delle tre è attiva, si cade nel percorso legacy
"best-per-bar" (righe 1312+): un solo trade per barra, il migliore tra
tutti i segnali dopo MTF/velocity/chain/score, passato per
`NXS_TryExecuteRC` (§1.4).

**`OnTimer()`** (ogni 1s, riga 924): fuori dal Tester gestisce con un
budget di tempo (400ms) le attività di rete (outbox, pull impostazioni,
push web throttled, poll comandi dashboard, bridge visuale) in ordine di
priorità — quelle che restano fuori budget slittano al secondo successivo.
**Il circuit-breaker Sharpe per-strategia (`NXS_RS_Breaker_Update`) gira
qui**, non nel tick, perché scansiona lo storico dei deal (costoso).
Anche licenza, salvataggio stato e dashboard girano qui.

**`OnDeinit()`** (riga 788): ferma il timer, scarica il ledger in coda,
esporta le statistiche finali, salva stato/Virtual SL su disco, rilascia
tutti gli handle indicatore.

**`OnTradeTransaction()`** (riga 1561): riconciliazione post-esecuzione
(non descritta in dettaglio qui — il grosso della logica di
identificazione/gestione post-apertura vive nei moduli del tick, §1.6).

## 1.2 Come nasce un segnale

Ogni strategia produce una `SNXSSignal` (`NXS_Defines.mqh:58`):

```cpp
struct SNXSSignal {
   ENUM_NXS_DIR    dir;        // DIR_NONE / DIR_BUY / DIR_SELL
   double          score;      // punteggio qualità del segnale
   ENUM_NXS_STRAT  strat;      // enum LEGACY, solo 16 valori (vedi §1.7)
   string          stratName;  // nome vero, usato ovunque nel sistema moderno
   string          reason;     // spiegazione testuale del trigger
   double          slPrice;
   double          tpPrice;
   double          entryRef;
   ENUM_TIMEFRAMES sourceTF;
};
```

Ogni funzione `NXS_Strat_<Nome>()` (una per strategia, sparse in
`NXS_Strategies.mqh`, `NXS_Strategies_SMC.mqh`,
`NXS_Strategies_Institutional.mqh`, `NXS_Strategies_Elliott.mqh`) calcola
la propria logica e ritorna una `SNXSSignal` — quasi tutte iniziano con
`if(!InpStrat_X || !NXS_SelectorAllows(N)) return s;` (segnale vuoto,
`dir=DIR_NONE`) se disabilitata o non selezionata. `NXS_CollectAllSignals`
chiama tutte le funzioni abilitate e le raccoglie in un array; da lì il
segnale entra nel percorso di esecuzione scelto (§1.1).

## 1.3 I quattro cancelli per aprire un trade

Una strategia deve passare **quattro controlli indipendenti**, mantenuti
in file diversi, senza un'unica fonte di verità (tema già segnalato più
volte nel vault):

1. **`InpStrat_X` / `InpUseX`** (`NXS_Inputs.mqh`) — il flag "voglio
   provarla", controllato dentro la funzione della strategia stessa.
2. **`InpStrategySelector` + `NXS_SelectorAllows(idx)`**
   (`NXS_Globals.mqh:11`) — un indice numerico assegnato a mano nell'ordine
   storico di introduzione nel codice (0 = nessun filtro, altrimenti solo
   quell'indice apre). **Non è lo stesso indice del registro** (§1.7).
3. **`NXS_Profile_Enabled(name)`** (`NXS_StrategyProfiles.mqh`) — una
   whitelist testuale separata (`if(name=="X") return true;` per ogni
   strategia consentita, `return false;` di default a fine funzione). Una
   strategia con flag e selettore giusti ma assente da questa whitelist
   dà **zero trade silenziosi** (nessun errore, solo `profile_disabled`).
   Bug della stessa classe già corretto più volte (PMAX, BB_SQUEEZE,
   ORDER_BLOCK, BOLLINGER, STRUCT_REACT +6 altre — vedi vault).
4. **`NXR_ZoneStrategyEnabled(type)`** (`NXS_ReusePerformancePack.mqh:1041`)
   — un QUARTO gate indipendente, solo per IFVG/FVG_MIT/OB_MIT/
   MALAYSIAN_SNR. **Scoperta importante fatta leggendo il codice per
   intero (non deducibile dal nome delle funzioni)**: per queste 4
   identità esiste un **motore "NXR" completamente separato e parallelo**
   alle funzioni `NXS_Strat_IFVG_Reversal()`/`NXS_Strat_FVG_Mitigation()`/
   `NXS_Strat_OB_Mitigation_Structural()`/`NXS_Strat_MalaysianSNR_Rejection()`
   documentate in Parte 2 (§2.29/2.30/2.32/2.39) — ed è quel motore
   parallelo, non le funzioni legacy, a produrre i trade REALI quando
   `InpNXR_Enable` è attivo. Il commento nel codice lo dichiara
   esplicitamente: *"this is the gate for the path that ACTUALLY
   executes live for these 4 (the NXR shadow engine, not the legacy
   functions in NXS_Strategies_SMC.mqh)"*.
   - **Meccanica**: il motore NXR mantiene un proprio registro di
     "zone" (`g_nxrZones[]`, tipi `NXR_ZONE_IFVG_BULL/BEAR`,
     `NXR_ZONE_FVG_BULL/BEAR`, `NXR_ZONE_OB_BULL/BEAR`,
     `NXR_ZONE_BREAKER_BULL/BEAR`, `NXR_ZONE_SNR_SUPPORT/RESISTANCE`),
     ognuna con stato (fresh/tested/broken), forza, e contatore di
     tocchi. Ogni volta che si chiude una barra sul timeframe di
     trigger (`InpNXR_TriggerTF`), `NXR_DetectClosedBarTrigger()`
     scansiona tutte le zone attive, verifica il quarto gate
     (`NXR_ZoneStrategyEnabled`, che a sua volta richiama sia il flag
     `InpStrat_X`/`InpUseX` sia `NXS_SelectorAllows(idx)` — **quindi il
     quarto gate non sostituisce il primo e il secondo cancello, li
     richiama di nuovo per lo stesso indice/flag**, se
     `InpNXR_RespectNexusSwitches` è attivo; altrimenti li ignora e
     lascia passare tutto), calcola una qualità di reazione
     (`NXR_ReactionQuality`: sweep+reclaim, engulfing, rejection candle)
     e sceglie la MIGLIOR zona/reazione del turno con un punteggio
     combinato (forza zona × 0.55 + qualità reazione × 0.45, con bonus
     per zone fresh/TF medio/sweep). Il segnale risultante
     (`NXR_BuildSignalFromZone`) usa `stratName` con suffisso **"_NXR"**
     esplicito: **IFVG_NXR, FVG_MIT_NXR, OB_MIT_NXR,
     MALAYSIAN_SNR_NXR** — nomi diversi da quelli usati dalle funzioni
     legacy (IFVG, FVG_MIT, OB_MIT, MALAYSIAN_SNR), utili per distinguere
     nei log/telemetria quale motore ha davvero aperto il trade.
   - **Esecuzione diretta, non tramite il router normale**: se
     `InpNXR_DirectM5Execution` è attivo, il segnale non passa dal
     ciclo normale di raccolta segnali (`NXS_CollectRaw`) — viene
     "armato" come `g_nxrTrigger` con una scadenza
     (`InpNXR_TriggerExpiryMinutes`) e poi eseguito direttamente da
     `NXR_ProcessPendingM5Trigger()` (chiamata da un hook diagnostico
     ogni tick, non da OnTick principale) attraverso
     `NXR_TryExecuteRC()` — che comunque passa per i controlli di
     protezione (`NXS_Prot_EntryBlocked`), spread, notizie e licenza
     prima di eseguire. Se `InpNXR_DirectM5Execution` è spento, il
     segnale confluisce invece nel motore di reazione generico tramite
     `NXR_ReactionFromTrigger()`/`NXR_DetectReactionHook()`, dando
     priorità al trigger NXR sopra la reazione strutturale legacy
     quando presente.
   - **Perché questo conta per chi legge il codice**: isolare "IFVG" o
     "MALAYSIAN_SNR" per un test guardando solo `NXS_Strategies_SMC.mqh`
     dà un quadro incompleto — se `InpNXR_Enable` è attivo (default da
     verificare in `NXS_Inputs.mqh`), il comportamento realmente
     osservato in live/backtest viene da questo motore a zone in
     `NXS_ReusePerformancePack.mqh`, non dalla funzione con lo stesso
     nome "umano" nel file di strategie. Questo è anche la causa diretta
     del bug MALAYSIAN_SNR_NXR da 17.218 aperture citato in §1.6: un
     gate mancante "una posizione per strategia" in Data Collection
     Mode, applicato a un segnale persistente prodotto proprio da questo
     motore a zone.

## 1.4 Come si apre davvero un trade

Percorso comune (usato dalla modalità "profili per-strategia" e da quella
legacy): `NXS_OpenTrade()` / `NXS_TryExecuteRC()` (`NXS_Execution.mqh`) →
**`NXS_CommonExposurePreflight()`** — l'unica funzione che TUTTI i
percorsi di apertura (ingresso primario, grid, piramide, SLReclaim,
ProfitReclaim, istituzionale) sono obbligati ad attraversare, in ordine:

1. Licenza (`NXS_License_Enforce`)
2. Kill-switch risk-of-ruin (`NXS_RuinFrozen`)
3. Protezioni giornaliere/pausa (`NXS_Prot_EntryBlocked` — ESL, DPT,
   **MaxTotalDD** dal 09/09, flatten pendente)
4. Stop obbligatorio (nessun ordine può avere `sl=0`)
5. Stato incerto → blocca (ledger anti-doppione degradato, snapshot di
   stato non ripristinato, indicatori illeggibili) e durabilità del
   Virtual SL
6. RiskShield per-strategia (`NXS_RS_BlockEntry` — il circuit-breaker
   Sharpe, §1.6)
7. Cap di esposizione direzionale (`NXS_DirExposureLots` vs
   `NXS_EffectiveMaxDirExposureLots`)
8. Margine proiettato (`InpMinMarginLevelPct`)
9. Preflight broker (`NXS_PreFlight` — spread, distanza minima stop,
   normalizzazione volume)

Solo dopo tutto questo: `NXS_TradeSetMagic(InpMagic + MAGIC_CORE/GRID/
PYRAMID/SPLIT)` (offset da `NXS_Defines.mqh`: CORE=0, GRID=1000,
PYRAMID=2000, SPLIT=3000 — `IsCoreMagic`/`IsGridMagic`/`IsPyrMagic` in
`NXS_Globals.mqh` classificano una posizione già aperta guardando in
quale fascia cade il suo magic) → `NXS_SafeBuy`/`NXS_SafeSell`
(`NXS_SafeOrder.mqh`, retry su REQUOTE/OFF_QUOTES/PRICE_CHANGED senza
bloccare il thread).

## 1.5 Registro degli intenti (`NXS_Intent.mqh`)

Perché esiste: **il commento del deal DI CHIUSURA viene riscritto da MT5**
con "sl X.XX"/"tp X.XX"/vuoto quando una posizione chiude per stop/target
nativi — qualunque fosse il commento messo in apertura. Un bug reale
trovato il 09/09 (vedi vault "A2+A3+A4" e "breaker Sharpe"): qualunque
codice leggesse l'identità della strategia dal commento del deal di
CHIUSURA la classificava sempre male. Il registro intenti risolve questo
registrando (ticket-ordine → nome strategia, score, rischio deciso, ATR
d'ingresso) al momento dell'APERTURA, quando il commento è ancora
affidabile:

- **`NXS_Intent_ByOrder(orderTicket, &out)`** — indicizzato direttamente
  per ticket-ordine, impostato incondizionatamente da `NXS_Intent_Record`.
  **Affidabile**, non dipende da nient'altro.
- **`NXS_Intent_ByPosition(posId, &out)`** — indicizzato per position ID,
  ma questo campo viene popolato SOLO da una chiamata successiva
  (`NXS_Intent_BindPosition`, dentro `NXS_TradeLedger.mqh`) legata alla
  ricostruzione del ledger. **Meno affidabile** — un fix del 09/09 basato
  su questa funzione non ha risolto il bug del breaker Sharpe proprio
  perché quel binding non scattava sempre; il fix definitivo è passato a
  `ByOrder`.

## 1.6 Gestione dopo l'apertura — moduli condivisi da TUTTE le strategie

Questi girano ad ogni tick su OGNI posizione aperta, indipendentemente da
quale strategia l'abbia generata — non sono ripetuti nella Parte 2:

- **Split** (`NXS_ManageSplit`, `NXS_SplitTrade.mqh`) — chiusura parziale
  P1 a +1.5×ATR (30% del volume), P2 a +3.0×ATR (50% del rimanente).
  Attivo di default (`InpEnableSplit=true`).
- **Grid** (`NXS_ManageGrid`, `NXS_GridRecovery.mqh`) — disattivato di
  default.
- **Piramide** (`NXS_ManagePyramid`, `NXS_Pyramiding.mqh`) — aggiunge una
  gamba su una posizione CORE già in profitto ≥1×ATR, poi richiede un
  livello ATR intero superiore per il prossimo add (1×→2×→3×, max 3
  gambe). Corretto il 09/09 da tre bug in sequenza: re-innesco senza
  freno dopo uno stop, poi retry infinito ad ogni tick quando un gate
  blocca il tentativo. Disattivato di default.
- **SLReclaim / ProfitReclaim** (`NXS_ManageSLReclaim`/
  `NXS_ManageProfitReclaim`) — rientro dopo che una posizione è stata
  stoppata (SLReclaim, riapre nella direzione originale se il prezzo
  riconquista il livello) o dopo aver incassato un profitto e essere
  tornati vicino all'entrata originale (ProfitReclaim). Entrambi ora
  passano da `NXS_CheckProtections()` + `NXS_CommonExposurePreflight()`
  (corretto il 09/09 — prima bypassavano le protezioni di conto,
  potendo riaprire anche a conto congelato).
- **Trailing ATR** (`NXS_TrailATR`, `NXS_TrailingATR.mqh`) — modifica lo
  stop solo per stringerlo, mai per allargarlo.
- **Protezioni di conto** (`NXS_Protections.mqh`, tutte passano da
  `NXS_Prot_OnTick`):
  - **ESL** (Equity Stop Loss) — PnL flottante vs balance corrente.
  - **DPT** (Daily Profit Target) — chiude tutto se il profitto del
    giorno supera un target.
  - **`InpMaxDailyDDPct`** — cap giornaliero, **si azzera ogni
    mezzanotte** (`NXS_Prot_OnNewDay`) — per costruzione non può fermare
    un drawdown che si accumula su più giorni consecutivi.
  - **`NXS_Prot_CheckMaxTotalDD`** (aggiunta il 09/09) — drawdown dal
    picco storico di equity, **non si azzera mai da solo**, si sblocca
    solo via comando dashboard esplicito (`reset_protections`). Colma il
    buco lasciato dal cap giornaliero.
- **Circuit-breaker Sharpe per-strategia** (`NXS_RiskShield.mqh`,
  `NXS_RS_Breaker_Update`, gira in `OnTimer` ogni 5 minuti) — ricostruisce
  lo Sharpe rolling di ogni strategia dallo storico deal e mette in pausa
  24h le nuove entrate di quella strategia se scende sotto soglia
  (default 0.30, finestra 50 trade). Corretto il 09/09: classificava
  sempre "UNKNOWN" (leggeva il commento del deal di chiusura, riscritto
  da MT5) invece di riconoscere la strategia vera — ora usa il registro
  intenti (§1.5).

## 1.7 Due numerazioni diverse, non intercambiabili

- **`NXS_StrategyRegistry.mqh`** — elenco canonico di 49 strategie
  (`NXS_LIVE_STRATEGY_COUNT`), indicizzato alfabeticamente per
  nome↔stringa (`NXS_StrategyIdAt(i)`), usato dalla telemetria. **Nota**:
  `LEVEL_CONFLUENCE` è riconosciuta da `NXS_StrategyKnown()` ma **manca**
  da `NXS_StrategyIdAt()` — sparisce da qualunque validazione basata su
  quella lista (bug già noto, non ancora corretto).
- **`ENUM_NXS_STRAT`** (`NXS_Defines.mqh:39`) — enum LEGACY con solo 16
  valori (ADX_RSI…STRUCT_REACT), usato solo nel campo `.strat` di
  `SNXSSignal` per compatibilità storica.
- **`InpStrategySelector` + `NXS_SelectorAllows(idx)`** — un TERZO indice,
  assegnato a mano nell'ordine di introduzione nel codice, **che non
  corrisponde a nessuno dei due sopra**. Esempio verificato: FVG_CONT ha
  `NXS_SelectorAllows(8)`, ma nell'`ENUM_NXS_STRAT` legacy
  `STRAT_FVG_CONT` vale 7 (ottavo elemento a partire da 0, ma l'ordine
  interno differisce). Prima di isolare una strategia per un test, va
  sempre cercato il numero vero con
  `grep 'NXS_SelectorAllows' NXS_Strategies*.mqh`, mai assunto dal
  registro o dall'enum.

---

# PARTE 2 — Le strategie

Per ogni strategia: famiglia (dedotta dal codice, non dal nome), timeframe,
dipendenze, trigger BUY, trigger SELL, gestione post-apertura oltre ai
moduli condivisi (§1.6), e una nota di stato senza farne il focus — il
focus è come funziona il codice, non il verdetto di trading.

## 2.1 ADX_RSI

- **File/funzione**: `NXS_Strat_ADXRSI()`, `NXS_Strategies.mqh:261`.
- **Gate**: `InpStrat_ADXRSI` + `NXS_SelectorAllows(1)`.
- **Famiglia**: trend-following con filtro di forza del trend (ADX) +
  filtro di momentum in fascia (RSI), non un semplice incrocio.
- **Timeframe**: `NXS_EffTF()` (timeframe effettivo del profilo attivo).
- **Dipendenze**: ADX (periodo 14 implicito in `g_adx`), EMA50, RSI(14).
- **Trigger BUY**: `g_adx >= 20` AND EMA50 in salita (EMA50 barra corrente
  > EMA50 barra precedente) AND RSI(14) compreso tra 45 e 65 (fascia di
  momentum "sano", né ipercomprato né in scarico) AND prezzo > EMA50.
- **Trigger SELL**: speculare — `g_adx >= 20` AND EMA50 in discesa AND
  RSI(14) tra 35 e 55 AND prezzo < EMA50. Simmetrica, nessuna asimmetria
  storica documentata.
- **Score**: 62 su entrambi i lati.
- **Post-apertura**: solo SL/TP nativi da `NXS_DefaultSLTP(s)` (ATR
  standard del profilo); nessuna gestione specifica oltre ai moduli
  condivisi di §1.6.
- **Stato**: nessuna nota storica di verdetto trovata nel codice per
  questa strategia specifica.

## 2.2 BOLLINGER

- **File/funzione**: `NXS_Strat_Bollinger()`, `NXS_Strategies.mqh:286`.
- **Gate**: `InpStrat_Bollinger` + `NXS_SelectorAllows(2)`.
- **Famiglia**: mean-reversion — tocco e rientro delle bande di
  Bollinger, non breakout.
- **Timeframe**: `NXS_EffTF()`, gate a chiusura barra (`lastEvalBar`) per
  evitare rivalutazioni infra-barra — pattern esplicitamente ripreso da
  un fix analogo già applicato su PivotWick.
- **Dipendenze**: bande di Bollinger, opzionalmente RSI (filtro
  divergenza, `InpBollingerUseRSIFilter`) e pattern candela
  (`InpBollingerUseCandleFilter`: hammer/engulfing).
- **Trigger BUY**: prezzo che tocca/rompe la banda inferiore alla barra
  shift2 e rientra sopra di essa alla barra shift1 (confronto shift1 vs
  shift2 — un bug di allineamento temporale su questo confronto è stato
  corretto in passato, documentato nel codice). Se attivi, i filtri
  RSI/candela devono confermare.
- **Trigger SELL**: speculare sulla banda superiore, MA **disattivabile
  a monte** da `InpBollingerBuyOnly` — quando attivo, il lato SELL non
  viene mai generato. Motivazione storica nel codice: nei backtest reali
  il lato BUY ha reso PF 1.33 su 71 trade mentre il lato SELL ha reso
  PF 0.61 su 138 trade, trascinando in negativo l'aggregato — quindi il
  blocco SELL è una scelta empirica, non strutturale del pattern.
- **Post-apertura**: SL/TP nativi da profilo; nessun modulo
  strategia-specifico oltre a §1.6.
- **Stato**: verdetto storico asimmetrico BUY/SELL documentato nel
  codice stesso (vedi sopra) — è l'unica strategia finora dove il
  commento storico coincide con una nota di merito, riportata perché
  spiega DIRETTAMENTE una scelta architetturale (flag BuyOnly), non come
  giudizio di trading a sé.

## 2.3 MACD

- **File/funzione**: `NXS_Strat_MACD()`, `NXS_Strategies.mqh:358`.
- **Gate**: `InpStrat_MACD` + `NXS_SelectorAllows(3)`.
- **Famiglia**: trend-following classico su MACD nativo (EMA-based via
  `iMACD`), con filtro di trend EMA200.
- **Timeframe**: `NXS_EffTF()`.
- **Dipendenze**: MACD nativo (iMACD), EMA200.
- **Trigger BUY**: MACD > signal AND MACD > 0 AND prezzo > EMA200.
- **Trigger SELL**: speculare — MACD < signal AND MACD < 0 AND prezzo <
  EMA200. Completamente simmetrica.
- **Post-apertura**: solo SL/TP nativi; nessuna gestione specifica.
- **Stato**: nessuna nota storica di verdetto nel codice.
- **Nota**: da non confondere con **MACD_SMA200** (§2.7), che è una
  strategia distinta e più complessa basata su medie mobili SEMPLICI
  invece che esponenziali, portata da uno script Pine Script pubblico.

## 2.4 SAR

- **File/funzione**: `NXS_Strat_SAR()`, `NXS_Strategies.mqh:406`, con
  due helper: `NXS_SAR_CandleAligned()` (:380) e
  `NXS_SAR_PressureContrary()` (:394).
- **Gate**: `InpStrat_SAR` + `NXS_SelectorAllows(4)`.
- **Famiglia**: trend-following stop-and-reverse — Parabolic SAR nativo
  combinato con un incrocio EMA9/EMA21, più due filtri opzionali
  empirici sovrapposti.
- **Timeframe**: `NXS_EffTF()`.
- **Dipendenze**: Parabolic SAR nativo, EMA9, EMA21; filtro candela
  (ultima candela allineata alla direzione) e filtro "pressure" (analisi
  delle ultime 8 barre M15).
- **Trigger BUY (base)**: SAR sotto il prezzo AND EMA9 incrocia sopra
  EMA21 (o è già sopra, a seconda della lettura esatta del codice).
- **Trigger SELL (base)**: speculare — SAR sopra il prezzo AND EMA9 sotto
  EMA21.
- **Filtri opzionali, sovrapposti al trigger base**:
  - `NXS_SAR_CandleAligned()`: richiede che l'ultima candela chiusa sia
    coerente con la direzione del segnale. Risultato storico
    documentato nel codice: win rate 69%→77% e PF 1.33→1.92 filtrando
    solo i segnali "allineati"; i segnali non allineati restano
    46%→50% win rate.
  - `NXS_SAR_PressureContrary()`: guarda la "pressione" direzionale delle
    ultime 8 barre M15 e filtra i segnali che vanno CONTRO quella
    pressione recente. Risultato storico documentato: PF 1.00 quando
    allineato alla pressione da solo, PF 1.69 quando contrarian da solo;
    combinando i due filtri, PF 3.47 quando entrambi concordano contro
    PF 0.04 quando sono in disaccordo — la combinazione è quindi molto
    più informativa dei singoli filtri.
- **Post-apertura**: SL/TP nativi da profilo; nessun modulo
  strategia-specifico oltre a §1.6.
- **Stato**: nota storica nel codice — sul motore reale SAR "puro" (base,
  senza filtri) è risultata negativa (PF 0.92), il che ha motivato lo
  sviluppo di PMax (§2.6) come alternativa concettualmente più robusta.
  I due filtri qui sopra sono i tentativi di recuperare SAR con
  condizioni aggiuntive derivate empiricamente dai dati storici.

## 2.5 BAR_UPDN

- **File/funzione**: `NXS_Strat_BarUpDn()`, `NXS_Strategies.mqh:~450`.
- **Gate**: `InpStrat_BarUpDn` + `NXS_SelectorAllows(43)`.
- **Famiglia**: price action pura su 3 candele consecutive (nessun
  indicatore) — porting diretto di uno script pubblico TradingView Pine.
- **Timeframe**: `NXS_EffTF()`.
- **Dipendenze**: solo OHLC, nessun indicatore.
- **Trigger BUY**: pattern rialzista sulle ultime 3 candele — `close[1] >
  open[1]` AND `open[1] > close[2]` (candela precedente chiusa rialzista
  e apertasi sopra la chiusura di due barre fa).
- **Trigger SELL**: pattern speculare ribassista.
- **Score**: 58 su entrambi i lati.
- **Gestione anti-inseguimento (cooldown)**: la strategia soffriva di un
  bug di "chasing" documentato nel codice — su un singolo movimento di
  mercato, 134 trade su 210 totali erano ingressi duplicati/raggruppati
  sullo stesso movimento, perché il pattern di 3 candele può ripetersi
  su barre consecutive dello stesso trend. Un primo tentativo di fix
  (reset one-shot dopo il primo trigger) ha ridotto il conteggio solo da
  210 a 207 — insufficiente. Il fix che ha funzionato usa un cooldown
  per-direzione basato sul NUMERO DI BARRE (`InpBarUpDnCooldownBars`,
  convertito in secondi tramite il period del TF), tracciato in
  `SNXSBarUpDnState.lastFireTime[2]` (indice 0=buy, 1=sell): dopo un
  trigger BUY, un nuovo BUY è permesso solo se sono passate almeno
  `cooldownSec` dall'ultimo (verificato tramite `curBar0 -
  lastFireTime[0] >= cooldownSec`); stessa logica indipendente per SELL.
- **Post-apertura**: SL/TP nativi da profilo; nessun modulo
  strategia-specifico oltre al cooldown stesso e a §1.6.
- **Stato**: bug di chasing risolto (vedi sopra); nessun verdetto
  finale di merito documentato nel codice oltre alla correzione del bug.

## 2.6 PMAX

- **File/funzione**: `NXS_Strat_PMax()`, `NXS_Strategies.mqh:497`.
- **Gate**: `InpStrat_PMax` + `NXS_SelectorAllows(44)`.
- **Famiglia**: trend-following stop-and-reverse, concettualmente un SAR
  "adattivo" — SuperTrend con stop ancorato a EMA ± ATR invece di
  step/max fissi come il Parabolic SAR nativo. Porting fedele di
  "PMax Explorer" (Pine Script pubblico, KivancOzbilgic; funzione
  `Pmax_Func` replicata).
- **Timeframe**: `NXS_EffTF()`, aggiornamento una volta per barra chiusa
  (mai per tick — necessario perché il flip di direzione deve essere
  univoco, stesso pattern usato in TSI).
- **Dipendenze**: ATR (`InpPMax_ATRPeriod`), EMA (`InpPMax_MALength`),
  moltiplicatore ATR (`InpPMax_ATRMult`).
- **Meccanica**: `longStop = EMA - mult*ATR`, `shortStop = EMA +
  mult*ATR`, entrambi "agganciati" (si muovono solo nella direzione
  favorevole finché il trend regge, mai contro). La direzione flip
  SOLO quando l'EMA rompe lo stop opposto (dir passa da -1 a +1 se
  `EMA > shortStop`, o da +1 a -1 se `EMA < longStop`).
- **Trigger BUY**: flip di direzione da -1 a +1 (non un livello statico,
  un evento di attraversamento).
- **Trigger SELL**: flip di direzione da +1 a -1. Simmetrica per
  costruzione (è lo stesso stato, letto nei due versi).
- **Score**: 60 su entrambi i lati.
- **Post-apertura**: SL/TP nativi da profilo; nessun modulo
  strategia-specifico oltre a §1.6.
- **Stato**: nota storica nel codice — sviluppata deliberatamente come
  candidato "migliore di SAR" dopo che SAR puro è risultato negativo
  (PF 0.92) sul motore reale; nessun verdetto proprio ancora documentato
  nel codice per PMax stessa.

## 2.7 MACD_SMA200

- **File/funzione**: `NXS_Strat_MacdSma200()`, `NXS_Strategies.mqh:567`,
  con helper `_nxs_macdsma_hist()` (:555).
- **Gate**: `InpStrat_MacdSma200` + `NXS_SelectorAllows(45)`.
- **Famiglia**: trend-following su un MACD costruito con medie SEMPLICI
  (SMA), non esponenziali come il MACD nativo (§2.3) — porting fedele di
  "MACD + SMA 200 Strategy" (Pine Script pubblico, ChartArt), con filtro
  di trend SMA200 aggiuntivo.
- **Timeframe**: `NXS_EffTF()`, gate a chiusura barra (ricostruire il
  signal richiede una media manuale su più barre, troppo costosa da
  ricalcolare ad ogni tick).
- **Dipendenze**: SMA a 4 lunghezze diverse — fast=12, slow=26, segnale
  costruito come media di 9 valori dell'istogramma (fastSMA-slowSMA), e
  SMA200 come filtro di trend di fondo.
- **Trigger BUY**: l'istogramma (macd-signal) attraversa lo zero verso
  l'alto (`histPrev <= 0 && histCur > 0`) AND `macd > 0` AND `fastMA >
  slowMA` AND la chiusura di "slowLength" barre fa (26 barre) era SOPRA
  la SMA200 — replica esatta della condizione originale
  `close[slowLength] > veryslowMA`, non semplificata.
- **Trigger SELL**: speculare — cross verso il basso, macd<0, fastMA<
  slowMA, chiusura storica sotto SMA200.
- **Score**: 60 su entrambi i lati.
- **Post-apertura**: SL/TP nativi da profilo; nessun modulo
  strategia-specifico oltre a §1.6.
- **Stato**: nessun verdetto storico di merito documentato nel codice
  per questa strategia; distinta e non da confondere con MACD (§2.3).

## 2.8 ICHIMOKU_HULL_MACD

- **File/funzione**: `NXS_Strat_IchimokuHullMacd()`,
  `NXS_Strategies.mqh:623`.
- **Gate**: `InpStrat_IchimokuHull` + `NXS_SelectorAllows(47)`.
- **Famiglia**: trend-following multi-filtro (5 condizioni in AND) —
  porting di uno script Pine Script pubblico ("Ichimoku +
  Daily-Candle_X + HULL-MA_X + MacD"). Nota storica nel codice:
  inizialmente scartata per sospetto di repaint, poi rivalutata perché
  la revisione originale (set. 2020) usa `barmerge.lookahead_off` su
  ogni `security()` ed include commissione/slippage — quindi giudicata
  meritevole di un vero test MT5 invece di uno scarto a priori.
- **Timeframe**: `NXS_EffTF()` per la maggior parte delle condizioni,
  PERIOD_D1 per il filtro di trend giornaliero, gate a chiusura barra.
- **Dipendenze**: Hull MA (`NXS_HMAv`, lunghezza 14), aperture D1,
  cloud Ichimoku (leadLine1/leadLine2, buffer già cachati per il TF
  attivo), MACD costruito su Hull MA (non EMA).
- **Trigger BUY** (tutte e 5 in AND):
  1. Hull MA in salita (confronto shift1 vs shift2 — matematicamente
     equivalente a "hma(price[1]) di 1 barra fa" grazie alla linearità
     del filtro Hull, semplificazione dichiarata come esatta nel commento).
  2. Trend giornaliero: apertura D1 di ieri > apertura D1 di l'altro ieri.
  3. Prezzo (apertura, fonte di default dello script originale) sopra
     la Hull MA di 1 barra fa.
  4. Cloud Ichimoku rialzista (leadLine1 > leadLine2).
  5. MACD (Hull-based) sopra la sua signal line — la signal line
     dell'originale è anch'essa una Hull MA (`hma(MACD,9)`); qui
     approssimata con una media semplice del MACD sulle ultime
     round(sqrt(9))=3 barre per limitare il costo di calcolo — unica
     semplificazione dichiarata rispetto all'originale, il resto è fedele.
- **Trigger SELL**: le 5 condizioni speculari, tutte in AND.
- **Score**: 62 su entrambi i lati.
- **Post-apertura**: SL/TP nativi da profilo; nessun modulo
  strategia-specifico oltre a §1.6.
- **Stato**: nota storica di rivalutazione (non scarto) riportata sopra;
  nessun verdetto empirico proprio ancora documentato nel codice.

## 2.9 3COMMAS_BOT

- **File/funzione**: `NXS_Strat_3CommasBot()`, `NXS_Strategies.mqh:676`.
- **Gate**: `InpStrat_3CommasBot` + `NXS_SelectorAllows(48)`.
- **Famiglia**: trend-following su incrocio EMA con stop/target
  STRUTTURATI (non ATR generico) — porting di uno script Pine Script
  pubblico ("3Commas Bot" / "Bj Bot"). Concettualmente vicino a SAR
  (§2.4, anch'esso basato su incrocio EMA9/21) ma con periodo diverso
  (EMA21/EMA50) e un meccanismo di stop/target ancorato a swing
  high/low invece che ad ATR puro — un secondo meccanismo pensato per
  essere confrontato con SAR.
- **Timeframe**: `NXS_EffTF()`, gate a chiusura barra.
- **Dipendenze**: EMA21, EMA50, ATR(14), swing high/low su lookback 5
  barre (`iLowest`/`iHighest`).
- **Trigger BUY**: incrocio EMA21 sopra EMA50 (`ma1prev <= ma2prev &&
  ma1cur > ma2cur`). Stop = minimo delle ultime 5 barre − 1×ATR(14);
  se il rischio risultante (close−stop) è ≤0 il segnale viene scartato.
  Target = entry + rischio (R:R 1:1, valore di default dello script
  originale, non alterato).
- **Trigger SELL**: speculare — incrocio EMA21 sotto EMA50, stop =
  massimo delle ultime 5 barre + 1×ATR, target a R:R 1:1.
- **Score**: 58 su entrambi i lati.
- **Post-apertura**: SL/TP **strutturali propri** (swing ± ATR, non i
  moltiplicatori ATR standard di `NXS_DefaultSLTP`) impostati
  direttamente nel segnale (`s.slPrice`/`s.tpPrice`); nessun trailing
  proprio — l'opzione era OFF di default nello script originale e non è
  stata replicata. Oltre a questo, si applicano comunque i moduli
  condivisi di §1.6 (split, grid, pyramid, trailing ATR generico se
  abilitato a livello di conto, protezioni).
- **Stato**: nessun verdetto storico di merito documentato nel codice.

## 2.10 PIVOT_WICK

- **File/funzione**: `NXS_Strat_PivotWick()`, `NXS_Strategies.mqh:801`,
  con helper `_nxs_pivotwick_scan_tf()` (:779) e
  `_nxs_pivotwick_push_row()` (:768).
- **Gate**: `InpStrat_PivotWick` + `NXS_SelectorAllows(49)`.
- **Famiglia**: mean-reversion su livelli — pivot frattali multi-timeframe
  con rigetto a wick opzionale. Idea originale dell'utente (vista a mano
  su TradingView, GOLD, linee orizzontali estese dai pivot di swing).
- **Timeframe**: pool di pivot scansionato su 5 TF insieme
  (M15/M30/H1/H4/D1), ma il trigger viene valutato SOLO sulla barra
  chiusa M15 di esecuzione — un pool multi-TF, un solo trigger intraday.
  Deliberatamente fuori scope il caso "rompe invece di rimbalzare"
  (già coperto da BREAKOUT_ACC e altre strategie di rottura).
- **Dipendenze**: pivot frattali (N barre a sinistra/destra più
  basse/alte, `InpPivotWickLookback`), ATR(14) per tolleranza tocco e
  wick minimo, cooldown per direzione in barre
  (`InpPivotWickCooldownBars`).
- **Trigger BUY**: la barra chiusa M15 tocca (entro tolleranza ATR) un
  livello pivot-minimo non ancora "consumato" (se
  `InpPivotWickOneShotLevel` attivo) di QUALSIASI dei 5 TF del pool.
  Il wick di rigetto è opzionale (`InpPivotWickRequireWick`, default
  OFF su richiesta dell'utente dopo che la versione con wick
  obbligatorio non produceva trade): se richiesto, serve un vero wick
  inferiore proporzionato al corpo e al wick opposto, con chiusura
  rialzista. Filtro anti-buildup opzionale (Rayner Teo, 03/09): scarta
  il tocco se il range delle N barre precedenti è troppo stretto
  rispetto all'ATR (segno di consolidamento debole, probabile rottura
  non rigetto). Conferma su chiusura opzionale
  (`InpPivotWickRequireCloseConfirm`, 03/09, anch'essa da Rayner Teo: un
  tocco solo intrabar può essere uno stop-hunt che inverte subito).
- **Trigger SELL**: speculare sui livelli pivot-massimo.
- **Score**: 60 su entrambi i lati.
- **Post-apertura**: SL/TP nativi da profilo; nessun modulo
  strategia-specifico oltre al cooldown e a §1.6.
- **Stato**: mai verificata su MT5 (dichiarato esplicitamente nel
  codice). Diversa da MALAYSIAN_SNR (che usa massimo/minimo di
  CHIUSURA su finestra fissa H4/W1 + filtro storyline direzionale) —
  qui sono veri pivot frattali multi-TF senza filtro di trend.

## 2.11 LEVEL_CONFLUENCE / LEVEL_CONFLUENCE_M5

- **File/funzioni**: core condiviso `_nxs_levelconf_core()`,
  `NXS_Strategies.mqh:923`; wrapper `NXS_Strat_LevelConfluence()` (:1069,
  esecuzione M15, `NXS_SelectorAllows(50)`, gate `InpStrat_LevelConfluence`)
  e `NXS_Strat_LevelConfluence_M5()` (:1086, esecuzione M5,
  `NXS_SelectorAllows(51)`, gate `InpStrat_LevelConfluenceM5`) — due
  strategie "gemelle" (nomi/selettori diversi) che condividono la stessa
  logica core perché il sistema di profili supporta un solo TF di
  esecuzione per strategia.
- **Famiglia**: mean-reversion su livelli, con conferma a N barre invece
  di trigger istantaneo. Nasce come merge esplicito di PIVOT_WICK,
  STRUCT_REACT e MALAYSIAN_SNR — l'utente ha osservato che sono la
  stessa idea (reazione a un livello chiave) implementata tre volte con
  fonti/conferme diverse mai incrociate.
- **Timeframe**: livelli presi SOLO da H1/H4/D1 del pool pivot condiviso
  con PIVOT_WICK (indici 2/3/4 — "le TF alte segnano il livello");
  esecuzione/conferma su M15 (variante base) o M5 (variante gemella,
  "entriamo sulle TF basse").
- **Dipendenze**: pool pivot condiviso `g_pivotWickState` (alimentato
  indipendentemente da PIVOT_WICK, funziona anche se quella strategia è
  disattivata), ATR per tolleranze.
- **Meccanica di conferma (non istantanea)**: un candidato non spara
  subito al primo tocco — viene messo "in osservazione"
  (`pendingDir`/`pendingLevel`/`pendingBars`) e spara solo se la
  direzione regge per `InpLevelConfConfirmBars` chiusure consecutive
  (se il parametro è ≤1, spara comunque al primo tocco). Motivazione
  documentata nel codice: nel primo test, sparare al primo tocco
  scommetteva su una reversal immediata che nel 58% dei casi si
  chiudeva a SL (win rate 34%) — osservazione con dati a supporto: sotto
  i 50 pip di sfondamento il prezzo torna sempre nella zona, sopra i 50
  pip spesso continua per un bel po' prima di tornare (se torna).
- **Trigger BUY**: tocco ("touch": tocco + chiusura di conferma) o sweep
  ("sweep": il prezzo perfora il livello oltre tolleranza e poi
  riconquista chiudendo dall'altra parte — liquidity grab) di un livello
  pivot-minimo H1/H4/D1, con bonus di score se il livello è confluente
  con un pivot di un'altra TF alta (`InpLevelConfRequireConfluence` può
  renderlo obbligatorio). Score = 55 + 8 (se sweep) + 20 (se confluente).
- **Trigger SELL**: speculare sui pivot-massimo. Nessun direction-lock —
  testata simmetrica BUY+SELL per principio di progetto (non si assume
  a priori quale lato regge).
- **Post-apertura**: SL/TP nativi da profilo; nessun modulo
  strategia-specifico oltre a §1.6.
- **Stato**: nota nel codice stesso — LEVEL_CONFLUENCE risulta "chiusa
  negativa il 06/09" (citata così nel commento storico di LEVEL_REACTION,
  la sua strategia successore, vedi sotto) — riportato perché è il
  codice stesso a dichiararlo come motivazione per la strategia
  successiva, non un giudizio esterno aggiunto qui.

## 2.12 LEVEL_REACTION / LEVEL_REACTION_M5

- **File/funzioni**: core condiviso `_nxs_levelreact_core()`,
  `NXS_Strategies.mqh:1179`, con helper
  `_nxs_levelreact_confluent()` (:1158); wrapper
  `NXS_Strat_LevelReaction()` (:1325, esecuzione M15,
  `NXS_SelectorAllows(52)`, gate `InpStrat_LevelReaction`) e
  `NXS_Strat_LevelReaction_M5()` (:1335, esecuzione M5,
  `NXS_SelectorAllows(53)`, gate `InpStrat_LevelReactionM5`).
- **Famiglia**: mean-reversion su livelli, evoluzione diretta di
  LEVEL_CONFLUENCE — merge VERO di PIVOT_WICK + STRUCT_REACT +
  MALAYSIAN_SNR + l'ossatura di LEVEL_CONFLUENCE, con due fonti di
  livello indipendenti invece di una sola.
- **Timeframe**: esecuzione M15 (base) o M5 (gemella); i livelli vengono
  da due fonti indipendenti: (a) pivot frattali H1/H4/D1 (wick-based,
  stesso pool di PIVOT_WICK), (b) supporti/resistenze "a corpo" H4 stile
  MALAYSIAN_SNR (chiusura delle ultime 12 barre H4, non wick — un
  secondo tipo di livello reale, non un duplicato della fonte 1).
- **Dipendenze**: pool pivot condiviso, livelli SNR H4 a corpo, zone SMC
  attive (Order Block/FVG di STRUCT_REACT, `g_reaction`) come bonus di
  confluenza aggiuntivo.
- **Ingrediente nuovo rispetto a LEVEL_CONFLUENCE — gate di profondità
  di sfondamento**: analisi rifatta da zero il 06/09 su 7402 pivot
  dell'intera storia GOLD M15 (2019-2026, zigzag K=3×ATR14): il livello
  riconquista il prezzo (reversal) nel 99.5% dei casi quando lo
  sfondamento resta sotto i 50 pip, nel 78.9% tra 50 e 100 pip, ma solo
  nel 69.1% oltre i 100 pip — oltre quella soglia è probabile rottura
  strutturale, non liquidity grab. Sopra `InpLevelReactMaxBreachPips`
  (default 100) il candidato viene scartato PRIMA di aprire
  l'osservazione, non solo penalizzato nello score. Sfondamenti "profondi"
  (≥ `InpLevelReactDeepBreachPips`, default 50) richiedono
  `InpLevelReactExtraConfirmBarsDeep` barre di conferma IN PIÙ (tempo
  mediano di richiusura per uno sfondamento ≥50 pip: ~20h/79 barre M15 —
  la sola conferma a N barre di LEVEL_CONFLUENCE, 30 min/2 barre, non
  bastava da sola).
- **Trigger BUY**: tocco/sweep di un livello (pivot H1/H4/D1 O S/R a
  corpo H4) con sfondamento entro `InpLevelReactMaxBreachPips`,
  confermato per `pendingReqBars` barre (base + extra se sfondamento
  profondo); bonus di score se confluente con un'altra fonte
  indipendente (altro pivot HTF, il livello SNR, o una zona SMC nella
  stessa direzione) e bonus aggiuntivo se lo sfondamento è piccolo
  (<50 pip, storicamente più affidabile).
- **Trigger SELL**: speculare sui livelli massimi. Nessun direction-lock
  e nessun filtro di trend "storyline" (a differenza di MALAYSIAN_SNR
  originale) — motivazione esplicita nel codice: la sessione ha già
  mostrato più volte che un filtro di trend in un mercato fortemente
  direzionale maschera l'esposizione al trend come "edge".
- **Nota unità di misura**: pip qui = $0.10 (convenzione vault per GOLD,
  confermata dall'utente), NON il `pipSize` di profilo simbolo usato da
  `InpFixedBEPips` altrove — attenzione a non confondere le due scale
  se si modificano questi parametri.
- **Post-apertura**: SL/TP nativi da profilo; nessun modulo
  strategia-specifico oltre a §1.6.
- **Stato**: successore diretto di LEVEL_CONFLUENCE (chiusa negativa il
  06/09); nessun verdetto proprio ancora documentato per LEVEL_REACTION
  stessa nel codice.

## 2.13 TSI

- **File/funzione**: `NXS_Strat_TSI()`, `NXS_Strategies.mqh:1366`.
- **Gate**: `InpStrat_TSI` + `NXS_SelectorAllows(5)`.
- **Famiglia**: momentum — vero True Strength Index (Blau), non un
  proxy RSI+EMA come nelle versioni precedenti.
- **Timeframe**: `NXS_EffTF()`, aggiornamento del doppio smoothing una
  sola volta per barra chiusa (calcolo iterativo, non ricalcolato
  sull'intera serie storica ad ogni tick).
- **Dipendenze**: nessun indicatore nativo — TSI calcolato a mano come
  `100 × doppioEMA(variazione prezzo) / doppioEMA(|variazione prezzo|)`,
  confrontato con una signal line (EMA del TSI).
- **Storia documentata nel codice**: la versione precedente NON
  calcolava un vero TSI — era un filtro RSI(>52)+EMA20(in salita) con il
  nome sbagliato (RSI>52 + prezzo sopra EMA20 in salita, short
  speculare), il che causava una divergenza di risultati tra sito e
  broker (PF 0.40 sul broker contro un edge forte dichiarato dal sito).
  Un audit esterno (17/07 notte) ha identificato il problema e portato
  al vero calcolo TSI (Blau) attuale.
- **Trigger BUY**: incrocio del TSI sopra la sua signal line
  (`tsiPrev <= signalPrev` E `tsi > signal` alla barra corrente).
- **Trigger SELL**: incrocio opposto. Simmetrica.
- **Score**: 66 su entrambi i lati.
- **Warmup**: nessun segnale finché non sono trascorse almeno
  `InpTSI_LongPeriod × 3` barre dall'avvio, perché il doppio EMA non è
  inizializzato con la media storica reale e parte da 0 — serve tempo
  per convergere.
- **Post-apertura**: SL/TP nativi da profilo; nessun modulo
  strategia-specifico oltre a §1.6.
- **Stato**: verdetto storico della vecchia versione (PF 0.40) riportato
  sopra perché spiega DIRETTAMENTE la riscrittura del calcolo, non come
  giudizio sulla strategia attuale (mai validata di nuovo dopo il fix).

## 2.14 BJORGUM

- **File/funzione**: `NXS_Strat_Bjorgum()`, `NXS_Strategies.mqh:1417`.
- **Gate**: `InpStrat_BJORGUM` + `NXS_SelectorAllows(6)`.
- **Famiglia**: mean-reversion semplice — rimbalzo/rigetto su
  massimo/minimo delle ultime 30 barre.
- **Timeframe**: `NXS_EffTF()`.
- **Dipendenze**: massimo e minimo delle 30 barre precedenti (shift 2 in
  poi), ATR per la distanza di tolleranza (0.5×ATR).
- **Trigger BUY**: chiusura della barra precedente entro 0.5×ATR dal
  minimo di 30 barre E sopra di esso (rimbalzo dal minimo).
- **Trigger SELL**: chiusura entro 0.5×ATR dal massimo di 30 barre E
  sotto di esso (rigetto dal massimo).
- **Score**: 68 su entrambi i lati.
- **Post-apertura**: SL/TP nativi da profilo; nessun modulo
  strategia-specifico oltre a §1.6.
- **Stato**: nessuna nota storica di verdetto nel codice.

## 2.15 LIQ_SWEEP

- **File/funzione**: `NXS_Strat_LiqSweep(SNXSSweepExt &sw)`,
  `NXS_Strategies.mqh:1454`.
- **Gate**: `InpStrat_LIQ_SWEEP` + `NXS_SelectorAllows(7)`.
- **Famiglia**: reversal su manipolazione di liquidità (ICT) — sweep di
  un livello di riferimento reale (non un estremo generico) seguito da
  rigetto.
- **Timeframe**: `NXS_EffTF()`; usa `NXS_DetectSweepExt()` che copre
  daily/weekly/monthly.
- **Dipendenze**: motore condiviso `SNXSSweepExt` (stesso motore di
  TURTLE_SOUP/SH_BMS_RTO/JUDAS_SWING/LDN_REVERSAL/PO3/AMD_REVERSAL/
  SILVER_BULLET), che riconosce PDH/PDL/Asia High-Low/equal High-Low
  come veri riferimenti di liquidità ICT.
- **Storia documentata nel codice**: prima (16/07) usava
  `NXS_DetectSweep()` generico (estremo di 20 barre qualsiasi) — l'unica
  strategia rimasta su quella definizione debole mentre le altre sette
  strategie citate sopra erano già passate al motore esteso. Dopo il
  passaggio a `SNXSSweepExt`: test A/B sul sito (config reale
  SL1.5/TP3.0) — su H4 senza HTF, PF 0.86→1.32 con DD quasi dimezzato
  (20.37%→8.71%); su D1+HTF (config profilo attuale) il campione cresce
  da 14 a 141 trade restando positivo (PF 3.30→1.27), risolvendo un
  problema di campione troppo piccolo mai risolto in 8 anni di dati
  reali (26 trade totali). Non uniformemente migliore su ogni TF.
  Aggiunto poi (16/07, seguito) un filtro "candela delivery": l'utente
  ha mostrato screenshot di setup ICT reali dove lo sweep coincide
  sempre con una vera candela Order Block (corpo forte), non un
  rimbalzo qualsiasi — filtro corpo≥0.7×ATR aggiunto, con miglioramento
  già provato sul sito (PF 1.27→1.63, DD quasi dimezzato su D1+HTF).
- **Trigger BUY**: sweep confermato (`sw.confirmed`) direzione BUY, corpo
  della barra precedente ≥0.7×ATR, chiusura sopra apertura (candela di
  rigetto rialzista).
- **Trigger SELL**: speculare — sweep SELL confermato, corpo ≥0.7×ATR,
  chiusura sotto apertura.
- **Score**: 72 su entrambi i lati. Il campo `reason` riporta
  esplicitamente quale livello ha scatenato il segnale
  (`sw.levelTag`: Daily/Weekly/Monthly-High/Low, Asia-High/Low,
  Equal-High/Low) — diagnostica per capire quale livello produce
  l'edge, senza duplicare la strategia per ogni tipo di livello.
- **Post-apertura**: SL/TP nativi da profilo; nessun modulo
  strategia-specifico oltre a §1.6.
- **Stato**: mai validata su MT5 (dichiarato nel codice); i miglioramenti
  A/B citati sopra vengono da test sul "sito" (motore Python esterno),
  non dal Tester MT5.

## 2.16 FVG_CONT

- **File/funzione**: `NXS_Strat_FVG()`, `NXS_Strategies.mqh:1481` —
  nome funzione `FVG` ma `stratName = "FVG_CONT"` (da non confondere con
  FVG_MIT, strategia distinta di mitigazione FVG, vedi altrove).
- **Gate**: `InpStrat_FVG_CONT` + `NXS_SelectorAllows(8)`.
- **Famiglia**: continuazione su Fair Value Gap — un gap a 3 candele
  nella direzione del trend ESTERNO (non locale).
- **Timeframe**: `NXS_EffTF()` per il gap, H1 (`g_structH1`) per il
  filtro di trend.
- **Dipendenze**: gap OHLC a 3 candele, struttura esterna H1
  (`g_structH1.trend`), opzionalmente il motore di reazione SMC
  (`NXS_SMCReactionOK`, gate `InpUseSMCReactionGate`).
- **Storia documentata nel codice**: il 16/07 il filtro di trend è stato
  cambiato da un proxy EMA50 locale al trend ESTERNO vero
  (`g_structH1`, mai letto prima da nessuna strategia) — test A/B sul
  sito (config reale H4+HTF): PF 1.45→2.07, DD 18.31%→12.48%, campione
  ~40% più piccolo. Non ancora validato su MT5 reale. In v2.4.2 aggiunta
  una conferma di reazione (structure+react engine) per filtrare i gap
  in cui il prezzo passa senza reagire — causa storica di perdite SMC.
- **Trigger BUY**: gap rialzista (`low` barra 1 > `high` barra 3) AND
  trend H1 esterno rialzista (`g_structH1.trend == 1`); se
  `InpUseSMCReactionGate` attivo, deve anche passare `NXS_SMCReactionOK`.
- **Trigger SELL**: speculare — gap ribassista (`high` barra 1 < `low`
  barra 3) AND trend H1 esterno ribassista.
- **Score**: 70 su entrambi i lati.
- **Post-apertura**: SL/TP nativi da profilo; nessun modulo
  strategia-specifico oltre a §1.6.
- **Stato**: nota di miglioramento A/B su sito (sopra); mai validata su
  MT5 reale (dichiarato nel codice).

## 2.17 BREAKOUT_ACC

- **File/funzione**: `NXS_Strat_BreakoutAcc()`, `NXS_Strategies.mqh:1528`.
- **Gate**: `InpStrat_BREAKOUT_ACC` + `NXS_SelectorAllows(9)`.
- **Famiglia**: breakout con accettazione (2 chiusure consecutive oltre
  il range) — non un semplice tocco/rottura istantanea.
- **Timeframe**: `NXS_EffTF()`, gate a chiusura barra.
- **Dipendenze**: range di 20 barre (massimo/minimo, shift 3+), cooldown
  per direzione in barre (`InpBreakoutAccCooldownBars`).
- **Storia documentata nel codice — bug di inseguimento identico a
  BAR_UPDN (§2.5)**: ipotesi dell'utente confermata sui dati (02/09) —
  nessuno stato "già tradato questo breakout", quindi la condizione di
  accettazione restava vera per ogni barra finché il prezzo non
  rientrava nel range, facendo aprire un nuovo trade a ogni barra
  invece che una volta sola. Verificato: 106 dei 201 trade nudi (M15,
  2024) erano raggruppati (stesso verso, entro 6h) — esempio citato: 7
  sell consecutivi tra il 3 e il 5 gennaio 2024 sullo stesso movimento,
  solo il primo (+$20.36) in profitto, i 6 inseguimenti tutti in
  perdita (-$2/-5 ciascuno). Su D1 nativo il danno era diluito (una
  barra al giorno); su M15 lo stesso bug spara decine di volte in più.
  Il PRIMO TENTATIVO di fix (one-shot che si resetta appena
  l'accettazione non è più vera, stesso schema fallito su BAR_UPDN) è
  risultato inefficace perché il rientro nel range è spesso
  intermittente. La CORREZIONE finale è lo stesso pattern di cooldown
  per direzione a numero di barre usato in BAR_UPDN.
- **Trigger BUY**: 2 chiusure consecutive (barra 1 e barra 2) sopra il
  massimo delle 20 barre precedenti (accettazione, non solo tocco), con
  cooldown BUY scaduto.
- **Trigger SELL**: speculare — 2 chiusure consecutive sotto il minimo
  di 20 barre, cooldown SELL scaduto.
- **Score**: 68 su entrambi i lati.
- **Post-apertura**: SL/TP nativi da profilo; nessun modulo
  strategia-specifico oltre al cooldown e a §1.6.
- **Stato**: bug di chasing risolto (vedi sopra), stesso pattern di
  BAR_UPDN; nessun verdetto finale di merito documentato oltre al fix.

## 2.18 Z_SCORE_BREAKOUT

- **File/funzione**: `NXS_Strat_ZScoreBreakout()`,
  `NXS_Strategies.mqh:1609`, con helper `_zsb_smaN()`, `_zsb_stdN()`,
  `_zsb_m5StructStop()` (:1578-1607). Porting da
  `server/backtest.py::sig_z_score_breakout` (24/08).
- **Gate**: `InpStrat_ZScoreBreakout` + `NXS_SelectorAllows(42)`.
- **Famiglia**: quant — breakout statistico (Z-score su bande a 2
  deviazioni standard), interpretazione OPPOSTA a BOLLINGER (§2.2), che
  usa le stesse bande statistiche ma per mean-reversion. Qui si
  scommette sulla CONTINUAZIONE, non sul ritorno alla media.
- **Timeframe**: `NXS_EffTF()` per lo z-score e il regime, PERIOD_M5 per
  lo stop strutturale.
- **Dipendenze**: media/deviazione standard su finestra di 20 barre
  (calcolate a mano, non da indicatore nativo), SMA200 come filtro di
  regime, minimo/massimo delle 12 candele M5 chiuse più recenti per lo
  stop strutturale (richiede almeno 3 candele valide).
- **Trigger BUY**: regime rialzista (chiusura > SMA200 sullo stesso TF)
  AND z-score > 2.0 (prezzo a più di 2 deviazioni standard sopra la
  media a 20 barre) — scommette che il movimento continui.
- **Trigger SELL**: regime ribassista (chiusura < SMA200) AND z-score <
  -2.0.
- **Score**: 71 su entrambi i lati.
- **Post-apertura**: SL/TP **strutturali propri**, non i moltiplicatori
  ATR standard del profilo — stop sul minimo/massimo delle 12 candele M5
  chiuse prima dell'ingresso, con un pavimento minimo di 0.3×ATR(H1);
  target fisso a 4.0×ATR. Stessa famiglia di stop già validata su
  SAR/MACD/ICHIMOKU (vedi vault "Stop Strutturale M5 su Segnali H1").
- **Validazione documentata nel codice**: validata su H1 il 17/08
  (`full_catalog_native_stop_17-08.py`) — retail PF 1.29 (4 finestre su
  5), ECN PF 1.71 (5/5), 557 trade: il miglior risultato retail
  dell'intera indagine citata.
- **Gap noto dichiarato nel codice**: il filtro di regime ER (Efficiency
  Ratio, lookback lungo) usato in validazione NON è un gate live qui —
  stesso gap dichiarato per SWING_FALSEBREAK.
- **Stato**: risultato di validazione offline positivo riportato sopra
  (fonte: script Python esterno, non Tester MT5).

## 2.19 LONDON_BO

- **File/funzione**: `NXS_Strat_LondonBO()`, `NXS_Strategies.mqh:1654`.
- **Gate**: `InpStrat_LONDON_BO` + `NXS_SelectorAllows(10)`.
- **Famiglia**: breakout di sessione — rottura del range asiatico durante
  la sessione di Londra, con filtro di convinzione sulla candela.
- **Timeframe**: `NXS_EffTF()`; attiva solo durante `SESS_LONDON`
  (`g_session`).
- **Dipendenze**: range asiatico (`NXS_GetAMD().asianHigh/asianLow`),
  ATR per corpo minimo e buffer, close location value (CLV) per
  convinzione direzionale.
- **Storia documentata nel codice**: validazione del breakout aggiunta
  il 17/07 notte da audit esterno — prima qualsiasi chiusura marginale
  oltre l'Asia contava come breakout. La gestione timezone/DST della
  sessione è centralizzata e condivisa con NY_REVERSAL, non duplicata.
- **Trigger BUY**: corpo della barra precedente ≥0.5×ATR
  (`InpLondonBO_MinBodyATR`) AND chiusura oltre il massimo asiatico +
  buffer (0.15×ATR) AND CLV rialzista (chiusura vicina al massimo di
  barra) ≥0.6 (`InpLondonBO_MinCLV`) — non un tocco marginale, una vera
  rottura con convinzione.
- **Trigger SELL**: speculare sul minimo asiatico con CLV ribassista.
- **Score**: 70 su entrambi i lati.
- **Post-apertura**: SL/TP nativi da profilo; nessun modulo
  strategia-specifico oltre a §1.6.
- **Stato**: nessun verdetto storico di merito documentato nel codice.

## 2.20 EMA_PULLBACK

- **File/funzione**: `NXS_Strat_EMAPullback()`, `NXS_Strategies.mqh:1725`,
  con helper `NXS_EMAPB_PressureAligned()` (:1713).
- **Gate**: `InpStrat_EMA_PULLBACK` + `NXS_SelectorAllows(11)`.
- **Famiglia**: continuazione di trend — pullback su EMA20 con vera
  rejection, non un semplice cross.
- **Timeframe**: `NXS_EffTF()` per il segnale, M15 fisso per il filtro
  di pressione opzionale.
- **Dipendenze**: EMA20, EMA50, ATR; filtro di pressione opzionale
  (ultime 8 barre M15).
- **Storia documentata nel codice — da semplice reclaim a vero
  pullback (17/07 notte, audit esterno)**: prima bastava un cross
  istantaneo di EMA20 con EMA20>EMA50 nel tick corrente — non dimostrava
  un trend persistente né un vero impulso precedente né una rejection.
  Ora richiede 4 condizioni: (1) trend persistente per
  `InpEMAPB_TrendPersistBars` barre (non solo l'istante attuale), (2) un
  impulso precedente che si sia allontanato dall'EMA20 di almeno
  `InpEMAPB_MinDistATR`×ATR nelle 10 barre prima del pullback, (3)
  pullback con vera rejection sulla barra chiusa (tocco EMA20 + chiusura
  che la riconquista nella direzione del trend), (4) niente entry se
  EMA50 viene rotta.
- **Filtro di pressione (`InpEMAPB_RequirePressureAligned`, default
  false) — storia documentata nel codice**: analisi su 80 trade nudi
  reali (ott 2023–ago 2026) ha trovato che qui — a differenza di SAR,
  dove vinceva la pressione CONTRARIA — vince la pressione ALLINEATA
  alla direzione del segnale, coerente con la natura di continuazione
  della strategia (il trend deve essere ancora vivo, non esaurito).
  Confermato anche su campione esteso (PF 1.61 allineata vs 0.72
  contraria). MA testato sul vero Tester MT5 (01/09, periodo 2023-2026):
  NON migliora — PF 1.42→1.35, netto $698.88→$581.97, quasi nessuna
  riduzione dei trade (84→83 contro il 21% di blocco atteso offline).
  Confermato con diagnostica che il gate funziona correttamente a
  livello di codice (non è un bug) — stessa lezione di SAR: bloccare un
  segnale sposta il timing di tutti i successivi, un effetto a cascata
  che l'analisi offline (righe fisse di tabella) non cattura. Lasciato
  come input disattivabile per riferimento, ma NON adottato — la
  baseline nuda estesa (PF 1.42, $698.88, 84 trade) resta il
  riferimento.
- **Trigger BUY**: le 4 condizioni sopra, lato rialzista; opzionalmente
  anche pressione allineata se il filtro è attivo.
- **Trigger SELL**: speculare.
- **Score**: 64 su entrambi i lati.
- **Post-apertura**: SL/TP nativi da profilo; nessun modulo
  strategia-specifico oltre a §1.6.
- **Stato**: risultato negativo del filtro di pressione sul Tester reale
  documentato sopra (lezione di metodo, non solo verdetto) — la
  strategia base (senza filtro) resta quella di riferimento.

## 2.21 BB_SQUEEZE

- **File/funzione**: `NXS_Strat_BBSqueeze()`, `NXS_Strategies.mqh:1793`.
- **Gate**: `InpStrat_BB_SQUEEZE` + `NXS_SelectorAllows(12)`.
- **Famiglia**: breakout da contrazione di volatilità — squeeze relativo
  alla propria storia (percentile), non una soglia assoluta.
- **Timeframe**: `NXS_EffTF()`, gate a chiusura barra.
- **Dipendenze**: bande di Bollinger (buffer 0/1/2 = mid/upper/lower),
  finestra di 150 barre per il percentile della bandwidth.
- **Storia documentata nel codice (17/07 notte, audit esterno)**: prima
  "width ≤ 2.5×ATR" era una soglia assoluta debole — con parametri
  standard la bandwidth può spesso rientrarci senza che sia una vera
  contrazione. Ora usa il percentile della bandwidth sulla finestra di
  150 barre (`InpBBSQ_PercentileMax`, default 20), richiede che lo
  squeeze sia durato almeno `InpBBSQ_MinSqueezeBars` barre consecutive,
  e il breakout scatta solo se la bandwidth sta già riespandendo.
- **Trigger BUY**: squeeze attivo da almeno N barre, non ancora
  "consumato" (one-shot per squeeze — niente segnali ripetuti sullo
  stesso squeeze), bandwidth in riespansione (bw corrente > bw
  precedente), chiusura sopra la banda superiore.
- **Trigger SELL**: speculare — chiusura sotto la banda inferiore.
- **Score**: 70 su entrambi i lati.
- **Post-apertura**: SL/TP nativi da profilo; nessun modulo
  strategia-specifico oltre a §1.6 (il one-shot per-squeeze è interno
  al trigger stesso, non una gestione post-apertura).
- **Stato**: nessun verdetto storico di merito documentato nel codice.

## 2.22 ICHIMOKU

- **File/funzione**: `NXS_Strat_Ichimoku()`, `NXS_Strategies.mqh:1852`.
- **Gate**: `InpStrat_ICHIMOKU` + `NXS_SelectorAllows(13)`.
- **Famiglia**: breakout di trend — rottura della cloud (Kumo) con
  conferma Tenkan/Kijun.
- **Timeframe**: `NXS_EffTF()`.
- **Dipendenze**: indicatore Ichimoku nativo (`g_hICHI`, buffer
  Tenkan/Kijun/SpanA/SpanB).
- **Storia documentata nel codice (17/07 notte, audit esterno) —
  allineamento temporale corretto**: `g_ichiSpanA/B/Tenkan/Kijun` sono
  cache globali valide SOLO a shift1 — il "prev" (chiusura a shift2)
  veniva confrontato per errore con la cloud di shift1 invece che con
  quella di shift2 (i buffer Senkou di MT5 sono già pre-shiftati
  internamente per il rendering "26 barre avanti", ma vanno comunque
  letti allo shift coerente con la barra valutata). Ora legge
  esplicitamente entrambi gli shift via `CopyBuffer`.
- **Trigger BUY**: chiusura a shift2 era dentro/sotto la cloud
  (`prev <= kumoTop2`) AND chiusura a shift1 sopra la cloud corrente
  (`price > kumoTop1`) AND Tenkan > Kijun — vera rottura, non solo
  prezzo già sopra la cloud.
- **Trigger SELL**: speculare sulla rottura verso il basso.
- **Score**: 65 su entrambi i lati.
- **Post-apertura**: SL/TP nativi da profilo; nessun modulo
  strategia-specifico oltre a §1.6.
- **Stato**: nessun verdetto storico di merito documentato nel codice.

## 2.23 RSI_DIV_PINE

- **File/funzione**: `NXS_Strat_RsiDivPine()`, `NXS_Strategies.mqh:1901`,
  con helper `_nxs_rsidivpine_pivot_low/high()` (:1888-1899). Porting da
  uno script Pine Script pubblico ("RSI Divergence Indicator", 28/08).
- **Gate**: `InpStrat_RsiDivPine` + `NXS_SelectorAllows(46)`.
- **Famiglia**: divergenza — RSI vs prezzo su PIVOT VERI (minimo/massimo
  locale confermato da lbL/lbR barre), metodo diverso da RSI_DIV nativo
  (§2.x, finestra fissa di 8 barre). Non un sostituto: un secondo
  meccanismo da confrontare, visto che il nativo è già forte (PF 1.21
  reale, citato nel codice).
- **Timeframe**: `NXS_EffTF()`, gate a chiusura barra.
- **Dipendenze**: buffer RSI nativo (`g_hRSI`), pivot a lbL=1/lbR=3
  barre, distanza tra due pivot consecutivi vincolata a un range
  (5-60 barre, fedele allo script originale).
- **Trigger BUY (divergenza bullish regular)**: il pivot RSI più recente
  (fresco, confermato ora) è più alto del pivot RSI precedente, MA il
  minimo di prezzo corrispondente è più basso del minimo precedente —
  prezzo fa un minimo più basso mentre il momentum (RSI) fa un minimo
  più alto, con la distanza tra i due pivot entro il range valido.
- **Trigger SELL**: divergenza bearish regular speculare (pivot RSI più
  basso, massimo di prezzo più alto).
- **Score**: 60 su entrambi i lati.
- **Post-apertura**: SL/TP nativi da profilo; nessun modulo
  strategia-specifico oltre a §1.6.
- **Stato**: nessun verdetto proprio documentato; citata solo come
  confronto contro RSI_DIV nativo (PF 1.21).

## 2.24 RSI_DIV

- **File/funzione**: `NXS_Strat_RSIDiv()`, `NXS_Strategies.mqh:1948`.
- **Gate**: `InpStrat_RSI_DIV` + `NXS_SelectorAllows(14)`.
- **Famiglia**: divergenza — RSI vs prezzo su finestra FISSA di 8 barre
  (non pivot veri come RSI_DIV_PINE, §2.23), con filtro di zona
  ipercomprato/ipervenduto.
- **Timeframe**: `NXS_EffTF()`.
- **Dipendenze**: buffer RSI nativo (`g_hRSI`).
- **Trigger BUY**: minimo di prezzo a 1 barra fa < minimo a 8 barre fa
  (lower low) AND RSI a 1 barra fa > RSI a 8 barre fa (higher low nel
  momentum — divergenza) AND RSI attuale < 40 (zona di ipervenduto).
- **Trigger SELL**: speculare — higher high in prezzo, lower high in
  RSI, RSI > 60.
- **Score**: 68 su entrambi i lati.
- **Post-apertura**: SL/TP nativi da profilo; nessun modulo
  strategia-specifico oltre a §1.6.
- **Stato**: citata (nel commento di RSI_DIV_PINE) come "già forte, PF
  1.21 reale" — unico dato di merito trovato nel codice per questa
  strategia, riportato come riferimento del confronto, non come verdetto
  a sé.

## 2.25 ORDER_BLOCK (e nota su FVG_MIT/OB_MIT)

- **File/funzioni**: `NXS_Strat_OrderBlock()`, `NXS_Strategies.mqh:2064`,
  con motore condiviso `NXS_OB_UpdateSide()` (:2000) e stato
  `SNXSOBState g_obBuy, g_obSell` (:1998).
- **Gate**: `InpStrat_ORDER_BLOCK` + `NXS_SelectorAllows(15)`.
- **Famiglia**: SMC — retest di un vero Order Block ICT (non la candela
  di displacement stessa).
- **Timeframe**: `NXS_EffTF()`.
- **Dipendenze**: ATR per la soglia di displacement (≥1.2×ATR), swing
  di riferimento a `InpOB_SwingLookback` barre per il Break of Structure
  (BOS), struttura esterna H1 (`g_structH1.trend`), motore di reazione
  SMC opzionale (`NXS_SMCReactionOK`).
- **Storia documentata nel codice — origine della zona corretta (17/07
  notte, audit esterno ICT/SMC)**: un order block bullish è l'ULTIMA
  candela bearish prima del displacement che rompe struttura (BOS), non
  il corpo del displacement stesso. La versione precedente usava la
  candela impulso come se fosse l'OB ("displacement body zone", non un
  vero order block). Corretto con tre cambi: (1) il displacement deve
  rompere uno swing precedente (BOS, prima mancava questo controllo),
  (2) la zona è l'ultima candela di colore opposto prima dell'impulso
  (cercata fino a 6 barre indietro), (3) la zona è persistente e
  "fresh" fino al primo retest o invalidazione (prima si ricalcolava
  tutto da zero ogni tick, senza nozione di zona già usata). In 16/07 è
  stata aggiunta anche la conferma di struttura esterna H1
  (`g_structH1`, calcolata ogni tick da `NXS_UpdateStructureH1` ma prima
  letta da zero strategie) — test A/B sul sito: PF migliora su quasi
  ogni TF/config (es. D1+HTF, config reale: 1.50→1.77, DD 5.85%→3.94%),
  campione si dimezza circa. Nota di fedeltà dichiarata: sul sito il
  test verificava il trend esterno AL MOMENTO dell'impulso (serie
  storica); in MQL5 `g_structH1` è solo lo stato CORRENTE, quindi qui il
  controllo equivale a "il trend H1 conferma ORA la direzione del
  retest" — stessa idea, punto di verifica leggermente diverso per
  limite strutturale di MQL5. Non ancora validata su MT5 reale.
- **Meccanica**: per ciascun lato (BUY/SELL) uno stato dedicato
  (`g_obBuy`/`g_obSell`) cerca un displacement valido tra 3 e 10 barre
  fa con corpo ≥1.2×ATR che rompa uno swing di `InpOB_SwingLookback`
  barre (BOS); trovato il BOS, la zona OB è definita dall'ultima candela
  di colore opposto prima dell'impulso. La zona resta "attiva" fino al
  primo retest o fino a `InpOB_MaxWaitBars` barre di attesa (poi scade),
  o fino a un'invalidazione (chiusura che attraversa completamente la
  zona nel verso sbagliato).
- **Trigger BUY**: prezzo (bid) rientra nella zona OB bullish attiva E
  la barra chiusa più recente è di rigetto (chiusura > apertura) E il
  trend H1 esterno conferma rialzista E (se attivo) `NXS_SMCReactionOK`
  conferma. Zona consumata (one-shot) dopo il primo retest.
- **Trigger SELL**: speculare sulla zona OB bearish, con trend H1
  esterno ribassista richiesto.
- **Score**: 70 su entrambi i lati.
- **Post-apertura**: SL/TP nativi da profilo; nessun modulo
  strategia-specifico oltre a §1.6.
- **Nota architetturale importante — riuso per OB_MIT**: il commento nel
  codice (v2.4.2) dichiara esplicitamente "vale anche per OB_MIT (usa
  questa funzione)" riferendosi al gate di conferma-reazione — cioè
  **OB_MIT non ha una funzione `NXS_Strat_` propria separata trovata in
  questo file: riusa `NXS_OB_UpdateSide()`/lo stato di
  `NXS_Strat_OrderBlock()`** con un gate/nome diverso a valle. Questo va
  verificato incrociando `NXS_StrategyProfiles.mqh` e
  `NXS_ReusePerformancePack.mqh` per capire dove esattamente OB_MIT
  applica la sua identità/selettore separati — non risolto in modo
  definitivo in questa lettura (vedi nota finale sulle strategie NXR).
- **Stato**: miglioramenti A/B su sito documentati sopra; mai validata
  su MT5 reale (dichiarato nel codice).

## 2.26 STRUCT_REACT

- **File/funzione**: `NXS_Strat_StructureReaction()`,
  `NXS_Strategies.mqh:2087`.
- **Gate**: `InpUseStructReact` (non `InpStrat_...`, nome diverso dal
  pattern standard) + `NXS_SelectorAllows(16)`.
- **Famiglia**: SMC — reazione generica a una struttura di mercato
  (livello + BOS/CHOCH), motore condiviso con LEVEL_CONFLUENCE e
  LEVEL_REACTION (bonus di confluenza zona SMC in quelle strategie usa
  proprio `g_reaction`, popolato qui).
- **Timeframe**: `NXS_EffTF()` (implicito nel motore di reazione
  esterno `g_reaction`/`g_struct`, non ricalcolato in questa funzione).
- **Dipendenze**: motore di reazione strutturale esterno (`g_reaction`:
  detected/direction/quality/levelType; `g_struct`: trend/bosUp/bosDown/
  chochUp/chochDown) — la logica di rilevamento vera e propria vive
  altrove (probabilmente nel motore SMC condiviso), qui si legge solo il
  suo output.
- **Trigger BUY**: `g_reaction.detected == true` AND
  `g_reaction.direction == 1`. Nessun'altra condizione di cancello
  binario — tutto il resto (allineamento col trend, conferma BOS/CHOCH)
  è modulazione dello SCORE, non un filtro on/off.
- **Trigger SELL**: speculare, `g_reaction.direction == -1`.
- **Score**: dinamico, non fisso — parte da 55 + `quality × 0.35`
  (quindi ~55..~90 in base alla qualità della reazione rilevata), +6 se
  la direzione della reazione è allineata al trend strutturale generale
  (`g_struct.trend`), +5 se c'è conferma di Break of Structure o Change
  of Character nella stessa direzione; tetto massimo 95.
- **Post-apertura**: SL/TP nativi da profilo; nessun modulo
  strategia-specifico oltre a §1.6.
- **Stato**: nessun verdetto storico di merito documentato in questa
  funzione specifica.

---

## 2.27 TURTLE_SOUP

- **File/funzione**: `NXS_Strat_TurtleSoup(SNXSSweepExt &sw)`,
  `NXS_Strategies_SMC.mqh:24`.
- **Gate**: `InpStrat_TurtleSoup` + `NXS_SelectorAllows(17)` — applicati
  ESTERNAMENTE dal chiamante in `NXS_CollectRaw()`
  (`NEXUS_EA_v2.mq5:453`), non dentro la funzione stessa. Vedi nota
  architetturale a fine SMC (dopo §2.40) sul pattern a due stili di
  gate.
- **Famiglia**: SMC/ICT — liquidity sweep con rientro ("Turtle Soup"
  classico) e candela di rigetto a corpo forte.
- **Timeframe**: `NXS_EffTF()`.
- **Dipendenze**: motore condiviso `SNXSSweepExt` (passato per
  riferimento, popolato altrove), ATR.
- **Nota versione (v2.0.6)**: richiede corpo della candela di rigetto
  ≥0.4×ATR "per evitare noise" — filtro aggiunto rispetto a versioni
  precedenti.
- **Trigger SELL**: sweep confermato del massimo del giorno precedente o
  di un equal-high (`sw.sweptPDH || sw.sweptEQH`) AND chiusura ribassista
  (close<open) AND chiusura sotto il riferimento sweepato (`c1 <
  sw.refHigh`) AND corpo ≥0.4×ATR.
- **Trigger BUY**: speculare sul minimo del giorno precedente/equal-low.
- **Score**: 72 su entrambi i lati.
- **Post-apertura**: SL/TP **propri**, non ATR-multiplo di profilo — SL
  oltre il livello sweepato ±0.5×ATR, TP a distanza 2× il rischio (R:R
  2:1 implicito, calcolato dalla distanza SL-entry).
- **Stato**: nessun verdetto storico di merito documentato in questa
  funzione.

## 2.28 SWING_FALSEBREAK

- **File/funzione**: `NXS_Strat_SwingFalseBreak()`,
  `NXS_Strategies_SMC.mqh:119`, con helper
  `_sfb_isPivotHigh/Low()`, `_sfb_lastPivotHigh/Low()` (:83-117). Spunto
  da script TradingView "Bjorgum Key Levels" condiviso dall'utente
  (24/08).
- **Gate**: `InpStrat_SwingFalseBreak` + `NXS_SelectorAllows(41)`.
- **Famiglia**: SMC — stesso concetto sweep+rientro di TURTLE_SOUP, ma
  con un ancoraggio mai provato prima: pivot di swing MAGGIORE
  (left=20/right=15 barre, confermato solo 15 barre dopo essersi
  formato, nessun lookahead) invece dei livelli intraday/sessione
  (PDH/PDL/Asia) usati da TURTLE_SOUP/LIQ_SWEEP. Zona larga
  min(prezzo×2%, 0.5×ATR) intorno al pivot.
- **Timeframe**: `NXS_EffTF()`.
- **Dipendenze**: pivot frattali propri (non condivisi col pool di
  PIVOT_WICK), lookback massimo 300 barre per la ricerca del pivot più
  recente confermato.
- **Trigger BUY**: il pivot low confermato più recente è stato rotto
  nelle ultime 3 barre chiuse MA la barra corrente chiude sopra la zona
  (rientro) E la chiusura è rialzista.
- **Trigger SELL**: speculare sul pivot high.
- **Score**: 70 su entrambi i lati.
- **Post-apertura**: SL/TP nativi da profilo (`NXS_DefaultSLTP`, profilo
  "SWING_FALSEBREAK": 1.5/4.0×ATR) — a differenza di TURTLE_SOUP, qui lo
  stop NON è un ancoraggio strutturale ma un multiplo ATR fisso, identico
  ai valori usati nel backtest Python.
- **Validazione documentata nel codice**: validata in Python su H1 con
  verifica due-metà-storia (nessuna metà negativa) — retail PF
  1.14→1.46, ECN PF 1.42→1.74 (234 trade grezzi nel campione).
- **Gap noto dichiarato nel codice**: il filtro di regime (Efficiency
  Ratio, lookback lungo) usato nella validazione Python NON è ancora
  portato in MQL5 come gate live — stesso gap dell'intero portafoglio
  SAR/MACD/LONDON_BO/FVG_CONT. Senza quel filtro il comportamento live
  può differire da quello validato, in particolare nei mercati laterali.
- **Stato**: validazione Python positiva (sopra); gap del filtro di
  regime non ancora chiuso.

## 2.29 IFVG

- **File/funzione**: `NXS_Strat_IFVG_Reversal()`,
  `NXS_Strategies_SMC.mqh:163` — `stratName = "IFVG"`.
- **Gate**: `InpStrat_IFVG` + `NXS_SelectorAllows(18)`, esterni
  (`NEXUS_EA_v2.mq5:454`).
- **Famiglia**: SMC — reversal su Inverse Fair Value Gap (un FVG
  invalidato nella direzione opposta), non continuazione.
- **Timeframe**: `NXS_EffTF()`.
- **Dipendenze**: struttura (`g_struct.chochUp/chochDown` per il Market
  Structure Shift), ATR.
- **Nota versione (v2.0.3)**: richiede esplicitamente un MSS opposto +
  una candela di reazione, non solo l'invalidazione del gap da sola.
  Commento nel codice: "an FVG is a 3-candle imbalance. Use candle 4 and
  candle 2 around candle 3; candle 1 is then free to invalidate/reject
  the zone."
- **Trigger SELL**: gap rialzista tra barra 4 e barra 2 (`l2 > h4 +
  0.2×ATR`) invalidato verso il basso dalla chiusura di barra 1 (`c1 <
  h4`) AND candela di reazione ribassista (corpo >0.3×ATR) AND CHOCH
  ribassista confermato dalla struttura (`g_struct.chochDown`).
- **Trigger BUY**: speculare — gap ribassista invalidato verso l'alto +
  CHOCH rialzista.
- **Score**: 73 su entrambi i lati.
- **Post-apertura**: SL/TP propri — SL al bordo del gap ±0.5×ATR, TP a
  2.4×ATR (via `_smc_tp`).
- **Stato**: nessun verdetto storico di merito documentato in questa
  funzione.
- **ATTENZIONE — questa NON è la logica che esegue live**: se
  `InpNXR_Enable` è attivo (motore "NXR", vedi §1.3 punto 4), il trade
  reale con identità legata a IFVG viene aperto da un motore a zone
  separato in `NXS_ReusePerformancePack.mqh`, con `stratName =
  "IFVG_NXR"` — logica di rilevamento zona/reazione diversa da quella
  qui sopra. Questa funzione (`NXS_Strat_IFVG_Reversal`) resta comunque
  richiamabile come percorso legacy indipendente.

## 2.30 FVG_MIT

- **File/funzione**: `NXS_Strat_FVG_Mitigation()`,
  `NXS_Strategies_SMC.mqh:198` — `stratName = "FVG_MIT"`.
- **Gate**: `InpStrat_FVG_Mit` + `NXS_SelectorAllows(19)`, esterni
  (`NEXUS_EA_v2.mq5:455`).
- **Famiglia**: SMC — mitigazione di un FVG "maturo" (vecchio, non
  appena formato), distinta esplicitamente da IFVG (che gestisce
  l'INVALIDAZIONE del gap, non il ritorno a un gap ancora valido).
- **Timeframe**: `NXS_EffTF()`.
- **Dipendenze**: ATR; finestra fissa di barre (shift 5 e 7) per
  identificare il gap.
- **Nota versione (v2.0.3)**: entry SOLO quando il prezzo torna nella
  zona FVG vecchia (bars 5-7) e produce una candela di rejection (corpo
  forte + chiusura in direzione attesa) — distingue esplicitamente un
  FVG "fresh" da uno "tested".
- **Trigger BUY**: gap rialzista identificato tra barra 5 e barra 7
  (`l0(shift7) > h2(shift5) + 0.15×ATR`) E il prezzo attuale (bid) è
  rientrato nella zona del gap E la barra chiusa più recente è di
  rigetto rialzista (corpo >0.35×ATR).
- **Trigger SELL**: speculare sul gap ribassista.
- **Score**: 70 su entrambi i lati.
- **Post-apertura**: SL/TP propri — SL al bordo del gap ∓0.4×ATR, TP a
  2.5×ATR.
- **Nota — variante FVG_MIT_WINDOW**: vedi §2.31, evoluzione diretta che
  risolve un limite temporale di questa versione.
- **Stato**: nessun verdetto storico di merito proprio; vedi §2.31 per
  il confronto con la variante successiva.
- **ATTENZIONE — questa NON è la logica che esegue live**: stesso avviso
  di IFVG (§2.29) — con `InpNXR_Enable` attivo, il trade reale ha
  `stratName = "FVG_MIT_NXR"` ed è prodotto dal motore a zone separato
  descritto in §1.3 punto 4, non da questa funzione.

## 2.31 FVG_MIT_WINDOW

- **File/funzioni**: `NXS_Strat_FVG_Mitigation_Window()`,
  `NXS_Strategies_SMC.mqh:312`, con motore di registro persistente
  `NXS_FvgMitWindow_Update()` (:279) e helper di rimozione
  `_fvgMitW_removeBull/Bear()` (:266-273). **Nota**: questo nome NON
  compare nella lista dei 49 nomi di `NXS_StrategyKnown()` catturata in
  §1.7/registro — verificare se è considerata "sperimentale"/fuori dal
  registro canonico o se il nome nel registro differisce.
- **Gate**: `InpStrat_FVG_MIT_WINDOW` + `NXS_SelectorAllows(39)`, esterni
  (`NEXUS_EA_v2.mq5:457`).
- **Famiglia**: SMC — evoluzione di FVG_MIT con un vero REGISTRO di zone
  multiple invece di un controllo puntuale.
- **Timeframe**: `NXS_EffTF()`.
- **Limite dichiarato di FVG_MIT (§2.30) che questa variante risolve**:
  FVG_MIT valuta ogni gap SOLO all'istante fisso shift5-7 vs il prezzo
  di ORA — se il ritorno sulla zona non avviene esattamente in quel
  momento, il segnale è perso per sempre (nessun registro). Qui il gap
  resta "attivo" fino a `NXS_FVGMITW_MAX_WAIT` (15) barre: ogni barra
  nuova può ancora mitigarlo. Registro fino a 24 zone bull e 24 bear
  simultanee (`NXS_FVGMITW_MAX_ZONES`), con età massima per zona.
- **Validazione documentata nel codice**: confermata due volte
  indipendentemente su H4 (walk-forward 11/08 + batch grid 12/08, n=129
  robusto). Porting fedele di `_fvg_mit_window_series`/
  `sig_fvg_mit_window`/`_fvg_mit_window_sl_tp` in `server/backtest.py`:
  stessa coppia di candele (shift5/shift7), stesso registro con età
  massima, stesso SL (bordo zona ∓0.4×ATR), MA il TP è a multiplo-R
  (2.5R sulla distanza SL, non 2.5×ATR fisso come FVG_MIT — unica
  differenza di formula tra le due varianti). HTF=true e trailing
  3.0×ATR vengono dal miglior candidato del batch grezzo del 12/08 (non
  da una ricerca dedicata a griglia piena come CRT/FVG_CONT/TSI —
  trattarli con meno certezza). Tier di rischio invariato (0.5%, Tier C)
  finché non c'è storia reale su MT5.
- **Trigger BUY**: una qualunque zona bull nel registro (non consumata,
  non scaduta) viene toccata dal range della barra corrente E la barra è
  di rigetto rialzista (corpo >0.35×ATR) — la prima zona che corrisponde
  viene usata e rimossa dal registro (one-shot per zona).
- **Trigger SELL**: speculare sul registro delle zone bear.
- **Score**: 70 su entrambi i lati.
- **Post-apertura**: SL/TP propri (bordo zona ∓0.4×ATR, TP a 2.5R);
  trailing 3.0×ATR citato come parametro del miglior candidato di
  backtest, da verificare se applicato anche live o solo in fase di
  ricerca.
- **Stato**: validazione robusta doppia (walk-forward + batch grid)
  documentata sopra, ma trattata con "meno certezza" di CRT/FVG_CONT/TSI
  per esplicita ammissione nel codice; nessuna storia reale su MT5
  ancora.

## 2.32 OB_MIT

- **File/funzione**: `NXS_Strat_OB_Mitigation_Structural()`,
  `NXS_Strategies_SMC.mqh:355` — `stratName = "OB_MIT"`.
- **Gate**: `InpStrat_OB_Mit` + `NXS_SelectorAllows(20)`, esterni
  (`NEXUS_EA_v2.mq5:458`) — indipendenti dal gate di ORDER_BLOCK
  (`InpStrat_ORDER_BLOCK`+selettore 15, verificato internamente): si può
  disattivare OB_MIT senza disattivare ORDER_BLOCK e viceversa, pur
  eseguendo esattamente la stessa logica di trigger quando entrambe
  sono attive.
- **Famiglia**: SMC — **non ha logica propria**: è un wrapper che
  richiama direttamente `NXS_Strat_OrderBlock()` (§2.25) e ne riusa
  interamente il segnale.
- **Meccanica esatta**: chiama `NXS_Strat_OrderBlock()`, se non produce
  segnale ritorna nessun segnale; altrimenti copia il segnale, cambia
  `stratName` in "OB_MIT", `reason` in "OB:structuralMit", e impone un
  floor di score a 68 (se lo score originale era <68, viene alzato a
  68 — altrimenti resta invariato).
- **Trigger BUY/SELL**: identici, byte per byte, a ORDER_BLOCK (§2.25) —
  stesso motore `NXS_OB_UpdateSide`, stessa gestione di zona, stesso
  requisito di conferma H1/reazione SMC.
- **Post-apertura**: SL/TP nativi da profilo (ereditati dal segnale di
  ORDER_BLOCK, che a sua volta usa `NXS_DefaultSLTP`).
- **Conferma della nota architetturale di §2.25**: questo chiarisce
  definitivamente il dubbio lasciato aperto lì — OB_MIT non è una
  strategia indipendente a livello di logica di trigger, è ORDER_BLOCK
  con un floor di score e un'etichetta diversa. Il quarto cancello
  `NXR_ZoneStrategyEnabled` (§1.3), se si applica a OB_MIT, si applicherebbe
  quindi a un semplice re-branding di ORDER_BLOCK, non a una logica
  indipendente — punto di attenzione per chiunque tenti di isolare
  OB_MIT per un test separato da ORDER_BLOCK: il codice sorgente del
  trigger è letteralmente lo stesso.
- **Stato**: nessun verdetto proprio (eredita quello, assente, di
  ORDER_BLOCK).
- **ATTENZIONE — anche questa NON è la logica che esegue live**: con
  `InpNXR_Enable` attivo, il trade reale con identità OB_MIT (e anche i
  "breaker block") ha `stratName = "OB_MIT_NXR"` ed è prodotto dal
  motore a zone separato di §1.3 punto 4 — un terzo livello di
  indirection rispetto al nome "OB_MIT" (che a sua volta era già solo un
  wrapper di ORDER_BLOCK): il nome umano "OB_MIT" può riferirsi a QUESTO
  wrapper (percorso legacy) o al motore NXR (percorso live reale),
  logiche di rilevamento completamente diverse tra loro.

## 2.33 SH_BMS_RTO

- **File/funzioni**: `NXS_Strat_SH_BMS_RTO(SNXSSweepExt &sw)`,
  `NXS_Strategies_SMC.mqh:478`, motore a stati
  `NXS_SHBMS_UpdateSide()` (:402) con stati
  `SHBMS_IDLE/SHBMS_SWEPT/SHBMS_WAITING_RETURN` e reset
  `NXS_SHBMS_Reset()` (:397).
- **Gate**: `InpStrat_SH_BMS_RTO` + `NXS_SelectorAllows(21)`, esterni
  (`NEXUS_EA_v2.mq5:459`).
- **Famiglia**: SMC — Stop Hunt + Break of Market Structure + Return
  To Origin, macchina a stati esplicita (non condizioni collassate su
  un solo tick).
- **Timeframe**: `NXS_EffTF()`.
- **Storia documentata nel codice (17/07 notte, audit esterno ICT/SMC)
  — riscritta come macchina a stati**: la versione precedente richiedeva
  sweep + CHOCH + FVG + prezzo già dentro la zona TUTTO sullo stesso
  tick — "collassava" una sequenza che nella realtà è causale e
  temporale (sweep, POI displacement/MSS entro qualche barra, POI un
  ritorno SUCCESSIVO alla zona d'origine), senza dimostrare che gli
  eventi fossero davvero collegati fra loro. La sequenza reale ora
  implementata: IDLE → SWEPT → (entro `InpSHBMS_MaxMSSBars` barre, MSS
  confermato + origine registrata) → WAITING_RETURN → primo ritorno
  nella zona = entry. Vincolo causale garantito per costruzione:
  sweepTime < mssTime < retestTime (si avanza di stato solo su barre
  chiuse successive).
- **Meccanica**: dopo un LIQ_SWEEP confermato nella direzione voluta
  (stato SWEPT), attende un Market Structure Shift (chiusura oltre lo
  swing di riferimento con corpo ≥`InpSHBMS_DispBodyATR`×ATR) entro
  `InpSHBMS_MaxMSSBars` barre; se confermato, registra la zona d'origine
  (ultima candela di colore opposto prima del displacement, cercata fino
  a 6 barre indietro) e passa a WAITING_RETURN, attendendo fino a
  `InpSHBMS_MaxWaitBars` barre un ritorno del prezzo in quella zona.
  Invalidazione a ogni fase se il prezzo chiude oltre il livello
  sweepato nel verso sbagliato.
- **Trigger BUY/SELL**: il primo ritorno del prezzo (bid) nella zona
  d'origine dopo un MSS confermato in quella direzione — one-shot,
  reset immediato dopo l'entry.
- **Score**: 74 su entrambi i lati.
- **Post-apertura**: SL/TP propri — SL al minimo/massimo tra livello
  sweepato e bordo zona d'origine ±0.5×ATR, TP a 2.6×ATR.
- **Stato**: nessun verdetto storico di merito proprio (la nota storica
  riguarda la riscrittura architetturale, non un risultato di trading).

## 2.34 SH_BMS_RTO_V2

- **File/funzioni**: `NXS_Strat_SH_BMS_RTO_V2(SNXSSweepExt &sw)`,
  `NXS_Strategies_SMC.mqh:556`, con step-motore
  `NXS_SHBMSV2_StepSide()` (:515) e reset `NXS_SHBMSV2_Reset()` (:511).
- **Gate**: `InpStrat_SH_BMS_RTO_V2` + `NXS_SelectorAllows(40)`, esterni
  (`NEXUS_EA_v2.mq5:461`), indipendenti dal gate della v1 (§2.33).
- **Famiglia**: SMC — variante INDIPENDENTE (non un refactor) di
  SH_BMS_RTO, esistente separatamente lato Python dall'08/08. Porting
  fedele di `_shbms_v2_series`/`sig_sh_bms_rto_v2` in
  `server/backtest.py`.
- **Timeframe**: `NXS_EffTF()`.
- **Differenze dichiarate rispetto alla v1 (§2.33)**: nessuna soglia
  body-ATR sull'MSS (basta chiusura oltre lo swing, in qualunque
  direzione col corpo giusto); zona di ritorno definita come
  `[sweepLevel..mssLevel]` invece della "candela opposta
  pre-displacement"; rejection valutata a 0.3×ATR sul PUNTO MEDIO della
  zona (non sul bordo); timeout di 12 barre condiviso da entrambe le
  fasi (SWEPT e WAITING); gate `ADX≥20` + trend di struttura ≠0 che
  blocca l'AVANZAMENTO DI STATO stesso (non solo l'ingresso) — un bar
  "gated-out" non fa avanzare `barsWaited` per nessuna delle due
  direzioni, fedele al `continue` Python che salta l'intera barra.
- **Trigger BUY/SELL**: sweep→MSS morbido→tocco della zona
  sweepLevel..mssLevel al punto medio con rejection ≥0.3×ATR. Se
  entrambe le direzioni segnalano nello stesso giro (raro), vince
  l'ultima valutata (SELL), fedele all'ordine del ciclo Python originale
  che sovrascrive l'array di output.
- **Score**: 70 su entrambi i lati.
- **Post-apertura**: SL/TP propri — SL al livello sweepato ∓0.3×ATR, TP
  a R:R 2:1 sulla distanza SL-entry.
- **Validazione documentata nel codice**: walk-forward 5/5 su H1 il
  14/08 — "il più robusto della sessione" (vedi vault "50 Maestri del
  Trading, Sintesi e Confronto col Nucleo").
- **Stato**: validazione walk-forward 5/5 positiva, citata come la più
  robusta della sessione di ricerca in questione.

## 2.35 SMS_BMS_RTO

- **File/funzione**: `NXS_Strat_SMS_BMS_RTO()`,
  `NXS_Strategies_SMC.mqh:590`.
- **Gate**: `InpStrat_SMS_BMS_RTO` + `NXS_SelectorAllows(22)`, esterni
  (`NEXUS_EA_v2.mq5:462`).
- **Famiglia**: SMC — failure swing reale (Smart Money Structure) con
  vera etichettatura HH/LH/LL/HL, poi BMS opposto e ritorno alla zona di
  sconto/premio.
- **Timeframe**: `NXS_EffTF()`.
- **Meccanica**: rileva gli ultimi 2 swing high (confronto max di 10
  barre recenti vs max delle 20 precedenti — se il recente è più basso è
  un Lower High, "failure to make HH") e gli ultimi 2 swing low
  (simmetrico, Higher Low = "failure to make LL"). Dopo un failure swing
  bull (HL) richiede un CHOCH rialzista di struttura (`g_struct.chochUp`)
  e una candela di rigetto rialzista (corpo >0.3×ATR); l'ingresso è
  ammesso solo se il prezzo (bid) è ancora nella metà "a sconto" della
  gamba (`bid <= midpoint`) — proxy dell'idea "ritorno a OB/FVG entro il
  60% del corpo dello swing" citata nel commento.
- **Trigger BUY**: failure low (HL) + CHOCH rialzista + rigetto
  rialzista + prezzo nella metà a sconto.
- **Trigger SELL**: speculare — failure high (LH) + CHOCH ribassista +
  rigetto ribassista + prezzo nella metà a premio.
- **Score**: 72 su entrambi i lati.
- **Post-apertura**: SL/TP propri — SL oltre lo swing recente ±0.5×ATR,
  TP a 2.6×ATR.
- **Stato**: nessun verdetto storico di merito documentato nel codice.

## 2.36 SILVER_BULLET

- **File/funzioni**: `NXS_Strat_SilverBullet(SNXSSweepExt &sw)`,
  `NXS_Strategies_SMC.mqh:726`, motore a stati
  `NXS_SB_UpdateSide()` (:660) con stati
  `SB_IDLE/SB_SWEPT/SB_WAITING_RETURN`.
- **Gate**: `InpStrat_SilverBullet` + `NXS_SelectorAllows(23)`, esterni
  (`NEXUS_EA_v2.mq5:463`); più un gate temporale interno proprio (vedi
  sotto).
- **Famiglia**: SMC — modello "Silver Bullet" ICT (killzone oraria +
  sweep + displacement/BOS + FVG + ritorno), macchina a stati come
  SH_BMS_RTO.
- **Timeframe**: `NXS_EffTF()`; finestre orarie GMT-corrette
  (`InpServerGMTOffset`): London killzone 10-11 GMT, NY killzone 14-15
  GMT — attiva solo dentro queste finestre.
- **Storia documentata nel codice (17/07 notte, audit esterno)**: prima
  era solo "sweep dentro una finestra oraria" — mancavano displacement,
  FVG e un ritorno successivo nella zona, gli elementi centrali del
  modello Silver Bullet reale. Riscritta come macchina a stati con la
  sequenza completa. Nota dichiarata: il calcolo delle killzone usa un
  numero massimo di barre, non un calcolo preciso del termine sessione
  in timezone reale — quel lavoro resta a parte, condiviso con
  NY_REVERSAL (già in coda separatamente).
- **Meccanica**: dentro la killzone, un sweep confermato porta a
  SB_SWEPT; entro `InpSB_MaxBars` barre deve seguire un displacement con
  corpo ≥`InpSB_DispBodyATR`×ATR che rompa uno swing di
  `InpSB_SwingLookback` barre (BOS), formando un FVG a 3 candele; il
  prezzo deve poi tornare dentro quel FVG entro altre `InpSB_MaxBars`
  barre per l'entry.
- **Trigger BUY/SELL**: primo tocco del prezzo (bid) dentro il FVG
  formato dal displacement, nella direzione dello sweep iniziale —
  one-shot.
- **Score**: 76 su entrambi i lati — tra i più alti del catalogo.
- **Post-apertura**: SL/TP propri — SL al livello sweepato ∓0.6×ATR, TP
  a 2.8×ATR.
- **Stato**: nessun verdetto storico di merito documentato nel codice
  oltre alla riscrittura architetturale.

## 2.37 AMD_REVERSAL

- **File/funzione**: `NXS_Strat_AMD_Reversal(SNXSSweepExt &sw, SNXSAMD
  &amd)`, `NXS_Strategies_SMC.mqh:745`.
- **Gate**: `InpStrat_AMD_Reversal` + `NXS_SelectorAllows(24)`, esterni
  (`NEXUS_EA_v2.mq5:464`); più un gate di fase AMD interno (vedi sotto).
- **Famiglia**: SMC — reversal su manipolazione AMD (Accumulation-
  Manipulation-Distribution): manipolazione sopra l'Asia High → SELL su
  reclaim+MSS (e speculare per il minimo).
- **Timeframe**: `NXS_EffTF()`.
- **Dipendenze**: motore AMD condiviso (`SNXSAMD`, fase corrente),
  motore sweep condiviso, struttura (`g_struct.chochUp/chochDown`).
- **Storia documentata nel codice (v2.0.34, punto 4 di un audit)**:
  ristretta a sparare SOLO nella fase di reversal confermata
  (`AMD_REVERSAL_DISTRIBUTION`) — prima sparava anche nelle fasi
  `AMD_MANIPULATION`/`AMD_DISTRIBUTION`, la STESSA condizione su cui si
  cancellava AMD_CONT (§2.4x, famiglia Institutional), rendendo le due
  strategie eleggibili sulle stesse barre e quindi in parte
  sovrapposte/concorrenti senza che fosse un disegno voluto.
- **Trigger SELL**: fase AMD = reversal/distribuzione confermata AND
  sweep del massimo asiatico confermato (`sw.sweptAsiaHigh`) AND CHOCH
  ribassista di struttura.
- **Trigger BUY**: speculare — sweep del minimo asiatico + CHOCH
  rialzista.
- **Score**: 75 su entrambi i lati.
- **Post-apertura**: SL/TP propri — SL oltre il riferimento sweepato
  ±0.5×ATR, TP a 2.5×ATR.
- **Stato**: nota storica sulla sovrapposizione con AMD_CONT (sopra) è
  l'unico dato di merito/architettura trovato; nessun verdetto di
  trading a sé.

## 2.38 OTE_CONT

- **File/funzione**: `NXS_Strat_OTE_Continuation()`,
  `NXS_Strategies_SMC.mqh:784` — `stratName = "OTE_CONT"`.
- **Gate**: `InpStrat_OTE_Cont` + `NXS_SelectorAllows(25)`, esterni
  (`NEXUS_EA_v2.mq5:465`).
- **Famiglia**: SMC — continuazione su ritracciamento OTE ("Optimal
  Trade Entry", zona Fibonacci 0.62-0.79) di una gamba dominante, non
  fallback ambiguo discount/premium.
- **Timeframe**: struttura su `InpTFMedium`, entry su `NXS_EffTF()`.
- **Dipendenze**: costruzione Fibonacci condivisa `NXS_Fib_Build`
  (usata anche da dashboard/visual bridge), struttura
  (`g_struct.trend`).
- **Storia documentata nel codice (v2.0.6, 17/07 notte, audit esterno)**:
  la zona Fibonacci in sé (62-79%, 70.5% centrale) era già corretta; il
  problema era l'ANCORAGGIO — lo swing veniva preso da un rolling
  highest/lowest generico di 30 barre su `InpTFMedium`, mai verificato
  che fosse davvero il leg che ha prodotto un BOS (poteva essere il
  punto più alto/basso di una fase lenta, non un vero impulso).
  `NXS_Fib_Build` resta invariata; aggiunto invece un gate BOS dedicato:
  il leg deve avere prodotto un vero displacement (corpo ≥
  `InpOTECont_DispBodyATR`×ATR, default 0.8) che rompe uno swing
  PRECEDENTE a quello usato come origine del leg. Rimosso anche il
  fallback ambiguo discount/premium quando il trend è laterale
  (`g_struct.trend==0` → niente trade).
- **Trigger BUY**: prezzo in zona OTE di sconto (`f.inDiscount`) di una
  gamba rialzista confermata da BOS, trend di struttura rialzista
  (`g_struct.trend==1`), chiusura sotto il punto medio del ritracciamento
  ma sopra lo swing low, e candela rialzista.
- **Trigger SELL**: speculare in zona premio con trend ribassista.
- **Score**: 69 su entrambi i lati.
- **Post-apertura**: SL/TP propri — SL oltre lo swing low/high ∓0.3×ATR,
  TP al massimo tra lo swing opposto e un target a 2.2×ATR (usa quale
  dei due è più ambizioso).
- **Stato**: nessun verdetto storico di merito documentato nel codice.

## 2.39 MALAYSIAN_SNR

- **File/funzione**: `NXS_Strat_MalaysianSNR_Rejection()`,
  `NXS_Strategies_SMC.mqh:842` — `stratName = "MALAYSIAN_SNR"`.
- **Gate**: `InpStrat_MalaysianSNR` + `NXS_SelectorAllows(26)`, esterni
  (`NEXUS_EA_v2.mq5:466`); più un gate di sessione interno (skip Asia).
  Questo risolve il quesito lasciato aperto in §1.3/§2.39 sul quarto
  cancello NXR: la lista dei gate effettivamente verificata in
  `NXS_CollectRaw()` per questa funzione contiene SOLO flag+selettore —
  nessuna chiamata a `NXR_ZoneStrategyEnabled` è comparsa in questo
  punto del dispatcher (righe 452-470 lette per intero). Se il quarto
  cancello esiste per MALAYSIAN_SNR, deve essere applicato altrove (non
  in `NXS_CollectRaw`) — punto ancora da verificare in una lettura
  dedicata di `NXS_ReusePerformancePack.mqh`.
- **Famiglia**: SMC — supporto/resistenza "a corpo" (chiusura, non wick)
  su H4, con storyline direzionale multi-TF e bonus di freschezza/
  confluenza W1. Questa è la fonte "SNR" citata come seconda fonte
  indipendente in LEVEL_REACTION (§2.12).
- **Timeframe**: livelli H4 (`InpTFHigh`) e W1 per confluenza, storyline
  su H4/D1, entry su `NXS_EffTF()`.
- **Dipendenze**: ATR del TF strategia (per il corpo della candela di
  rigetto) E ATR H4 separato (per le tolleranze sui livelli — handle
  statico locale creato una volta, perché questo file è incluso PRIMA di
  `NXS_Performance.mqh` in `NEXUS_EA_v2.mq5`, quindi non può riusare la
  funzione condivisa `NXS_iATR` non ancora dichiarata a quel punto).
- **Storia documentata nel codice (v2.0.6 + 17/07 notte, audit esterno,
  3 correzioni)**: (1) i livelli H4 sono ora confrontati con tolleranze
  in ATR H4, non più l'ATR del TF strategia attivo — unità diverse,
  distanza non dimensionalmente stabile prima; (2) il tocco del livello
  ora usa low/high della barra CHIUSA 1, non il bid live mescolato con
  la rejection su barra chiusa; (3) W1 non è più calcolato e scartato: è
  un vero bonus di confluenza (livello W1 vicino = +score). In v2.0.6
  aggiunto anche uno skip esplicito della sessione asiatica (bassa
  volatilità ⇒ falsi segnali su un S/R H4 body-based costruito per
  sessioni più liquide).
- **Trigger BUY**: sessione ≠ Asia AND low della barra chiusa 1 tocca
  (entro tolleranza ATR-H4×0.4) il supporto H4 a corpo (minimo delle
  chiusure delle ultime 12 barre H4) AND chiusura rialzista con corpo
  >0.5×ATR AND storyline rialzista (H4 attuale > H4 di 4 barre fa E D1
  di ieri ≥ D1 di l'altro ieri — contesto direzionale, non la posizione
  attuale). Bonus di score: +5 se il livello è "fresh" (non toccato
  nelle ultime 20 barre H4, salvo le 3 più recenti), +4 aggiuntivo se il
  livello coincide (entro tolleranza) con un livello W1.
- **Trigger SELL**: speculare sulla resistenza H4 a corpo (massimo delle
  chiusure) con storyline ribassista.
- **Score**: base 68 + bonus fresh/W1 come sopra (max ~77).
- **Post-apertura**: SL/TP propri — SL oltre il livello H4 ±0.5×ATR-H4,
  TP a 2.3×ATR.
- **Diversa da**: LEVEL_REACTION/LEVEL_CONFLUENCE (§2.11/2.12), che
  riusano il concetto di S/R a corpo H4 come SECONDA fonte tra diverse
  (pivot frattali + questa), e PIVOT_WICK (§2.10), che usa pivot frattali
  wick-based multi-TF invece di chiusure fisse H4/W1.
- **Stato**: nessun verdetto storico di merito proprio documentato nel
  codice.
- **ATTENZIONE — questa NON è la logica che esegue live**: con
  `InpNXR_Enable` attivo, il trade reale con identità MALAYSIAN_SNR ha
  `stratName = "MALAYSIAN_SNR_NXR"` ed è prodotto dal motore a zone
  separato di §1.3 punto 4 (tipi zona `NXR_ZONE_SNR_SUPPORT/
  RESISTANCE`, con propria logica di reazione — sweep+reclaim,
  engulfing, rejection — indipendente dalla storyline H4/D1/W1 descritta
  qui sopra). **Questo è anche il motore coinvolto nel bug storico delle
  17.218 aperture citato in §1.6**: un gate mancante "una posizione per
  strategia" nel percorso di esecuzione diretta M5 di questo stesso
  motore a zone, non nella funzione `NXS_Strat_MalaysianSNR_Rejection`
  qui documentata.

## 2.40 CRT

- **File/funzione**: `NXS_Strat_CRT()`, `NXS_Strategies_SMC.mqh:926` —
  fonte: PDF "Candle Range Theory" di Suven Raj, caricato dall'utente
  (11/08). **Nota**: "CRT" non compare nella lista dei 49 nomi catturata
  da `NXS_StrategyKnown()` in §1.7 — da verificare se rientra in un altro
  nome del registro o se è effettivamente fuori dal registro canonico
  (un altro possibile caso di "implementazione senza nome nel registro",
  simmetrico a FVG_CONT_V2/SAR_FLIP che sarebbero "nome nel registro
  senza implementazione").
- **Gate**: `InpUseStrat_CRT` + `NXS_SelectorAllows(38)`, esterni
  (`NEXUS_EA_v2.mq5:491`).
- **Famiglia**: SMC — pattern a 3 candele consecutive: RANGE (candela di
  riferimento) → SWEEP (stoppino oltre il range ma richiusura dentro) →
  entry in direzione OPPOSTA allo sweep, target il lato opposto del
  range.
- **Timeframe**: `NXS_EffTF()` (M30 di default nel profilo, vedi
  `NXS_StrategyProfiles.mqh`).
- **Meccanica esatta**: barra shift2 = RANGE, definisce CRH (high) e CRL
  (low) di riferimento. Barra shift1 = SWEEP: deve superare CRH o CRL col
  wick MA chiudere di nuovo DENTRO il range — se chiude fuori, il setup è
  invalido (il mercato sta continuando, non invertendo). Nessun filtro
  di sessione o storyline aggiuntivo — fedele esattamente a come è stata
  validata in Python (`server/backtest.py::_crt_series`).
- **Trigger SELL**: sweep del lato alto del range (wick sopra CRH,
  chiusura ≤CRH) SENZA sweep contemporaneo del lato basso — target CRL.
- **Trigger BUY**: speculare — sweep del lato basso, target CRH.
- **Score**: 68 su entrambi i lati.
- **Post-apertura**: SL/TP impostati DIRETTAMENTE dai livelli reali del
  pattern (SL = wick dello sweep, TP = lato opposto del range), NON da
  `NXS_DefaultSLTP` — stesso stile di MALAYSIAN_SNR. **Floor minimo sulla
  distanza dello stop (12/08)**: se la distanza wick-based scende sotto
  `InpCRT_MinStopATR`×ATR, lo stop viene ESTESO (mai stretto) fino al
  floor. Motivazione documentata nel codice: lo stop ancorato al wick
  della candela di sweep, quando il wick è minimo, può far esplodere il
  rischio flottante durante il trade (107% osservato in una finestra)
  prima che chiuda correttamente a -1R — non un rischio attivo con size
  fissa, ma un vincolo necessario ora che il rischio per-strategia sale
  (tier di rischio A). Allarga solo il rischio nominale per trade, non
  tocca la logica del target.
- **Validazione documentata nel codice**: walk-forward 5/5 finestre su
  4h/1h/30m dopo la riverifica sullo storico ampliato (11/08), quasi
  20.000 trade totali — descritta nel codice come "la scoperta più
  solida di tutta la sessione di ricerca".
- **Stato**: validazione walk-forward molto robusta (sopra, fonte
  backtest Python); nessuna conferma esplicita di validazione MT5 reale
  trovata in questo file.

---

**Fine di `NXS_Strategies_SMC.mqh` (967 righe).** Nota trasversale
importante — **verificata direttamente su `NEXUS_EA_v2.mq5:432-491`
(`NXS_CollectRaw()`)**: quasi tutte le funzioni di questo file
(TURTLE_SOUP, IFVG, FVG_MIT, FVG_MIT_WINDOW, SH_BMS_RTO, SH_BMS_RTO_V2,
SMS_BMS_RTO, SILVER_BULLET, AMD_REVERSAL, OTE_CONT, MALAYSIAN_SNR,
SWING_FALSEBREAK, Z_SCORE_BREAKOUT, CRT) **non espongono un gate
`InpStrat_x`/`NXS_SelectorAllows` al proprio interno**: il primo e il
secondo cancello di §1.3 per queste strategie sono applicati dal
CHIAMANTE, con un `if(...) out[n++] = NXS_Strat_x(...)` esplicito in
`NXS_CollectRaw()`, non dentro la funzione `NXS_Strat_` stessa. Le "16
classiche" (ADX_RSI...STRUCT_REACT) sono invece chiamate
INCONDIZIONATAMENTE in quello stesso punto (righe 436-451, nessun `if`)
perché il loro gate è tutto interno alla funzione (`if(!InpStrat_x ||
!NXS_SelectorAllows(n)) return s;`, come documentato per ADX_RSI,
BOLLINGER, MACD, SAR in apertura di Parte 2). **Due stili di gate
coesistono nello stesso EA**: interno (strategie "classiche", scritte
prima) ed esterno nel dispatcher (strategie SMC/ICT aggiunte dopo, v2.0.6
in poi) — chiunque cerchi di disattivare una strategia deve sapere quale
stile usa, altrimenti rischia di modificare il posto sbagliato. I numeri
di selettore reali per ciascuna strategia SMC sono riportati nella
rispettiva sezione sopra (§2.27-2.40), letti direttamente dalle righe
453-491 del dispatcher, non dedotti.

## 2.41 THREE_BAR_DELIVERY_BREAK (nome funzione: CISD)

- **File/funzione**: `NXS_Strat_CISD(SNXSSweepExt &sw)`,
  `NXS_Strategies_Institutional.mqh:83` — `stratName =
  "THREE_BAR_DELIVERY_BREAK"`. Il parametro `sw` è presente nella firma
  ma non risulta usato nel corpo della funzione in questa lettura.
- **Gate**: `InpUseStrat_CISD` (interno) + `NXS_SelectorAllows(27)`
  (esterno, `NEXUS_EA_v2.mq5:474`) — nota: pattern di naming
  `InpUseStrat_x`, diverso da `InpStrat_x` usato nel file principale —
  vedi anche §1.3.
- **Famiglia**: price action a 3 candele + rottura — NON un vero "Change
  In State of Delivery" ICT nonostante il nome della funzione.
- **Timeframe**: `NXS_EffTF()`.
- **Storia documentata nel codice — rinominata da CISD a
  THREE_BAR_DELIVERY_BREAK (17/07 notte, audit esterno canonico)**:
  esempio esplicito della regola "non usare il nome come prova": il vero
  Change in State of Delivery è normalmente identificato dalla rottura
  del LIVELLO/OPEN che sosteneva la sequenza di candele opposte, non da
  "tre candele dello stesso colore + rottura del loro massimo/minimo" —
  questo è un pattern di rottura reale e funzionante, ma non è un CISD
  canonico. Rinominata invece di riscritta: un tentativo precedente di
  versione "vera" (displacement+delivery+sweep+reclaim, v2.3.3) non
  scattava MAI (0 setup su 1067) — rischio concreto di silenziare di
  nuovo la strategia. La logica resta invariata, cambia solo l'identità
  dichiarata. Il toggle `InpUseStrat_CISD` è rimasto invariato di
  proposito per non rompere i file `.set` esistenti — quindi il nome
  dell'input NON corrisponde più al nome della strategia.
- **Trigger BUY**: le 3 barre precedenti (shift 2,3,4) sono tutte
  ribassiste (bear3) E la chiusura corrente supera il massimo delle tre
  (rottura dell'estremo della sequenza).
- **Trigger SELL**: speculare — 3 barre rialziste, chiusura sotto il
  minimo delle tre.
- **Score**: 74 su entrambi i lati.
- **Post-apertura**: SL/TP nativi da profilo (`NXS_DefaultSLTP`) — anche
  questo un cambio rispetto alla versione precedente v2.3.3, che
  hardcodava SL/TP ignorando il profilo.
- **Stato**: 0 setup su 1067 per la versione "vera" precedente (dato
  storico riportato nel codice); nessun verdetto per la versione attuale
  (3-bar) oltre alla motivazione del suo mantenimento.

## 2.42 AMD_CONT

- **File/funzione**: `NXS_Strat_AMD_Continuation(SNXSAMD &amd, SNXSHTF
  &htf)`, `NXS_Strategies_Institutional.mqh:109`.
- **Gate**: `InpUseStrat_AMD_Cont` (interno) + `NXS_SelectorAllows(28)`
  (esterno, `NEXUS_EA_v2.mq5:475`).
- **Famiglia**: SMC/ICT — continuazione (non reversal) dopo
  distribuzione oltre il range asiatico, con retest.
- **Timeframe**: `NXS_EffTF()`; attiva solo in sessione Londra/Overlap/NY
  (mai in sessione asiatica).
- **Dipendenze**: motore AMD condiviso (fase corrente), bias HTF
  condiviso.
- **Storia documentata nel codice (v2.0.34, punto 4)**: ristretta a
  sparare SOLO nella fase `AMD_CONTINUATION_DISTRIBUTION` — prima era
  `AMD_DISTRIBUTION`, la STESSA condizione su cui si cancellava
  AMD_REVERSAL (§2.37), rendendo le due eleggibili sulle stesse barre
  (stessa sovrapposizione già documentata lì, sintomo dello stesso
  problema visto da due lati). Corretto anche (17/07 notte) un mix di
  punti temporali: prima si mescolava la chiusura della barra 1
  (breakout) con il bid live (retest) — due istanti diversi sulla stessa
  condizione. Ora tutto sulla barra chiusa 1: breakout e retest devono
  appartenere alla STESSA barra.
- **Trigger BUY**: chiusura oltre il massimo asiatico (distribuzione
  fuori range) E il minimo della stessa barra rientra entro 0.6×ATR dal
  bordo (retest) E bias HTF rialzista o neutro.
- **Trigger SELL**: speculare sul minimo asiatico, bias HTF ribassista o
  neutro.
- **Score**: 72 su entrambi i lati.
- **Post-apertura**: SL/TP propri — SL al minimo tra (bordo asiatico
  ∓0.3×ATR) e il punto medio del range, TP a 2.4× il rischio.
- **Stato**: nota di sovrapposizione con AMD_REVERSAL (sopra) come unico
  dato architetturale; nessun verdetto di trading a sé.

## 2.43 JUDAS_SWING

- **File/funzione**: `NXS_Strat_JudasSwing(SNXSSweepExt &sw, SNXSAMD
  &amd)`, `NXS_Strategies_Institutional.mqh:157`.
- **Gate**: `InpUseStrat_Judas` (interno) + `NXS_SelectorAllows(29)`
  (esterno, `NEXUS_EA_v2.mq5:476`).
- **Famiglia**: SMC/ICT — falso movimento all'apertura di
  Londra/NY con reversal nel range.
- **Timeframe**: `NXS_EffTF()`; attiva solo nelle finestre di apertura
  Londra (7-10 GMT) o NY (12-15 GMT) — `_inst_inLondonOpen()`/
  `_inst_inNYOpen()`.
- **Dipendenze**: motore sweep condiviso, motore AMD condiviso,
  struttura (`g_struct.chochUp/chochDown`).
- **Trigger BUY**: wick sotto il minimo asiatico/PDL/equal-low (o
  semplicemente sotto `amd.asianLow`) E chiusura di rientro sopra il
  minimo asiatico E CHOCH rialzista confermato.
- **Trigger SELL**: speculare sul massimo asiatico/PDH/equal-high.
- **Score**: 75 su entrambi i lati.
- **Post-apertura**: SL/TP propri — SL oltre l'estremo sweepato ∓0.4×ATR,
  TP al massimo tra il lato opposto del range asiatico e un target a
  2.5× il rischio.
- **Stato**: nessun verdetto storico di merito documentato nel codice.

## 2.44 LDN_REVERSAL

- **File/funzione**: `NXS_Strat_LondonReversal(SNXSSweepExt &sw,
  SNXSAMD &amd)`, `NXS_Strategies_Institutional.mqh:195`, con helper
  di calcolo BST reale `NXS_LastSundayUTC()`/`NXS_IsLondonBST()`
  (:235-247, condivisi anche con NY_REVERSAL).
- **Gate**: `InpUseStrat_LdnReversal` (interno) + `NXS_SelectorAllows(30)`
  (esterno, `NEXUS_EA_v2.mq5:477`).
- **Famiglia**: SMC/ICT — reversal su sweep di liquidità durante la
  sessione di Londra.
- **Timeframe**: `NXS_EffTF()`; attiva solo in sessione Londra/Overlap.
- **Storia documentata nel codice (17/07 notte, audit esterno) — gestione
  del fuso orario corretta**: prima la sessione di Londra usava un
  offset GMT fisso (6-12) tutto l'anno, che in estate (BST, UTC+1)
  sbagliava la finestra di un'ora, ed era aggregata dalle barre del TF
  strategia (su H4/D1 una singola barra non rappresenta la finestra
  precisa). Corretto con: (1) calcolo reale del BST (regola
  Europe/London: dall'01:00 UTC dell'ultima domenica di marzo
  all'01:00 UTC dell'ultima domenica di ottobre — una regola che UK e
  USA NON condividono, motivo per cui un offset fisso annuale è
  strutturalmente sbagliato in certe settimane); (2) aggregazione da M5,
  indipendente dal timeframe della strategia. Questo motore di
  fuso orario è condiviso con NY_REVERSAL, non duplicato.
- **Trigger SELL**: sweep del massimo asiatico/PDH/equal-high E chiusura
  sotto il riferimento sweepato E CHOCH ribassista.
- **Trigger BUY**: speculare sul minimo.
- **Score**: 76 su entrambi i lati.
- **Post-apertura**: SL/TP propri — SL oltre il riferimento sweepato
  ±0.5×ATR, TP al minimo/massimo tra il lato opposto del range asiatico
  e un target a 2× il rischio.
- **Stato**: nessun verdetto storico di merito documentato nel codice.

## 2.45 NY_REVERSAL

- **File/funzione**: `NXS_Strat_NYReversal(SNXSSweepExt &sw)`,
  `NXS_Strategies_Institutional.mqh:252` — speculare di LDN_REVERSAL ma
  usa come riferimento il range della sessione di Londra del GIORNO
  CORRENTE (High/Low of Day di Londra), non il range asiatico.
- **Gate**: `InpUseStrat_NYReversal` (interno) + `NXS_SelectorAllows(31)`
  (esterno, `NEXUS_EA_v2.mq5:478`).
- **Famiglia**: SMC/ICT — reversal su sweep del range di Londra durante
  la sessione NY.
- **Timeframe**: `NXS_EffTF()` per il trigger, M5 per l'aggregazione
  del range di Londra (fino a 300 barre M5 di lookback, ~25h, filtrate
  per restare dentro la giornata corrente e la finestra oraria di
  Londra: 07-11 UTC in BST, 08-12 UTC in GMT).
- **Dipendenze**: stesso motore BST condiviso con LDN_REVERSAL.
- **Trigger SELL**: massimo della barra corrente supera l'High of Day di
  Londra E chiusura rientra sotto quel massimo E CHOCH ribassista.
- **Trigger BUY**: speculare sul Low of Day di Londra.
- **Score**: 75 su entrambi i lati.
- **Post-apertura**: SL/TP propri — SL oltre l'estremo della barra
  ±0.5×ATR, TP al minimo/massimo tra il lato opposto del range di
  Londra e un target a 2.5× il rischio.
- **Stato**: nessun verdetto storico di merito documentato nel codice.

## 2.46 WEEKLY_EXP

- **File/funzione**: `NXS_Strat_WeeklyRangeExp()`,
  `NXS_Strategies_Institutional.mqh:350`, macchina a stati
  `WEXP_IDLE`/`WEXP_WAITING_LTF`.
- **Gate**: `InpUseStrat_WeeklyExp` (interno) + `NXS_SelectorAllows(32)`
  (esterno, `NEXUS_EA_v2.mq5:479`).
- **Famiglia**: SMC/ICT — espansione del range settimanale (continuation
  weekly), a due stadi: trigger H4/settimanale (STAGE 1) + raffinamento
  dell'entry su M15 (STAGE 2).
- **Timeframe**: struttura su W1/H4, raffinamento entry su M15.
- **Storia documentata nel codice — due correzioni (17/07 notte, audit
  esterno) più un redesign a stadi (26/08, proposta dell'utente)**:
  correzioni iniziali: (1) il corpo H4 veniva confrontato con l'ATR D1
  (perché `g_atr` = ATR del TF di profilo di questa strategia = D1) —
  unità diverse, soglia quasi irraggiungibile, era IL bug dominante
  dietro gli zero-trade; ora usa un ATR H4 dedicato; (2) mancava del
  tutto la verifica che il displacement rompesse uno swing H4 (BOS) —
  senza quella non è "displacement che produce continuation", è solo
  "una candela H4 abbastanza grande". Redesign a stadi (26/08): scoperta
  RISK_SIZE — lo stop nativo 1.5×ATR(D1) dal livello settimanale è
  spesso $30-45, che al lotto minimo su un conto piccolo supera l'8% e
  l'ordine viene rifiutato prima ancora dello spread. Soluzione: STAGE 1
  (trigger H4/settimanale, logica di rilevamento invariata) arma uno
  stato di attesa invece di entrare subito; STAGE 2 (`WAITING_LTF`)
  attende fino a `NXS_WEXP_MAX_WAIT_M15` (8) barre M15 una vera candela
  di reazione (pin bar o chiusura direzionale) e usa il suo estremo
  (±0.2×ATR M15) come stop — molto più stretto. Risultato Python
  documentato: nativo PF1.18 (n=16, rischio mediano $38) → ingresso
  raffinato PF1.64 (n=15, rischio mediano $3.51), rifiuti RISK_SIZE a
  conto $500 dal 37.5% al 6.7%. Campione ancora piccolo, nessuna
  conferma live al momento della scrittura. **Bug aggiuntivo corretto
  (27/08)**: la barra H4 non va marcata come "già valutata"
  immediatamente al primo tick, perché `chochUp`/`chochDown` sono flag a
  cadenza M15 (veri solo per la durata di UNA barra M15 dentro le ~16
  che compongono la barra H4) — marcarla subito bloccava tutti i tick
  successivi PRIMA che il choch potesse mai diventare vero durante
  quella barra H4, risultato verificato sul Tester MT5 a tick reali (10
  mesi): 0 trade. Va marcata SOLO quando ci si arma davvero.
- **Trigger BUY (STAGE 1→2)**: bid sotto il punto medio settimanale,
  chiusura H4 rialzista con corpo ≥0.8×ATR-H4, BOS H4 rialzista
  confermato, bid sopra l'apertura settimanale, CHOCH rialzista → arma
  l'attesa; poi (STAGE 2) prima candela di reazione M15 valida entro 8
  barre determina l'entry effettivo e lo stop stretto.
- **Trigger SELL**: speculare.
- **Score**: 70 su entrambi i lati.
- **Post-apertura**: SL stretto strutturale M15 (vedi sopra); target
  Fibonacci 1.272 dell'estensione settimanale come "tetto di sicurezza"
  lontano — la gestione vera del profitto è delegata a
  `NXS_WeeklyExpManage()` (breakeven a 1.0R + trailing strutturale a
  1.5R, file `NXS_WeeklyExpManage.mqh`, non ancora letto in dettaglio in
  questa guida), che di solito chiude prima del tetto.
- **Stato**: risultato Python positivo su campione piccolo (sopra),
  prima conferma live ancora da avere per esplicita ammissione nel
  codice.

## 2.47 PO3

- **File/funzione**: `NXS_Strat_PO3(SNXSSweepExt &sw, SNXSAMD &amd)`,
  `NXS_Strategies_Institutional.mqh:468`.
- **Gate**: `InpUseStrat_PO3` (interno) + `NXS_SelectorAllows(33)`
  (esterno, `NEXUS_EA_v2.mq5:480`).
- **Famiglia**: SMC/ICT — Power of Three completo (Accumulation →
  Manipulation → Distribution) come classificatore di entry, non solo
  un singolo sweep.
- **Timeframe**: `NXS_EffTF()`.
- **Meccanica**: ACC = range asiatico; MAN = sweep oltre il range;
  DIST = candela di distribuzione (corpo ≥0.6×ATR) con reclaim e
  conferma di struttura.
- **Trigger BUY**: sweep del minimo asiatico confermato E chiusura
  rientra sopra il minimo asiatico E chiusura rialzista (candela di
  distribuzione) E CHOCH rialzista.
- **Trigger SELL**: speculare sul massimo asiatico.
- **Score**: 76 su entrambi i lati.
- **Post-apertura**: SL/TP propri — SL oltre il riferimento sweepato
  ∓0.4×ATR, TP al massimo/minimo tra il lato opposto del range asiatico
  e un target a 2.6× il rischio.
- **Stato**: nessun verdetto storico di merito documentato nel codice.

## 2.48 LIQ_VOID

- **File/funzione**: `NXS_Strat_LiquidityVoid(SNXSHTF &htf)`,
  `NXS_Strategies_Institutional.mqh:503`, con helper condiviso
  `_inst_displacementBar()` (:39).
- **Gate**: `InpUseStrat_LiqVoid` (interno) + `NXS_SelectorAllows(34)`
  (esterno, `NEXUS_EA_v2.mq5:481`).
- **Famiglia**: SMC/ICT — continuazione su retest del 50% (Consequent
  Encroachment) di un vero vuoto di liquidità/FVG lasciato da un
  displacement.
- **Timeframe**: `NXS_EffTF()`.
- **Storia documentata nel codice (17/07 notte, audit esterno) —
  geometria FVG corretta**: la versione precedente confrontava
  `high(displacement)` con `high(displacement+2)` — due massimi, non un
  vero gap — poteva classificare come "void" un normale nuovo massimo.
  Corretta con la geometria FVG a 3 candele standard ICT/SMC (bullish:
  Low(candela3) > High(candela1), zona tra High[candela1] e
  Low[candela3]) — stessa correzione di geometria applicata anche a
  DISP_REBAL (§2.49) nella stessa sessione di audit.
- **Trigger BUY**: displacement rialzista rilevato (corpo ≥1.2×ATR) nelle
  ultime 12 barre, bias HTF rialzista, gap valido (ampiezza >0.3×ATR),
  prezzo (bid) rientrato nella metà inferiore del gap (tra il bordo
  basso e il 50%, consequent encroachment) E chiusura rialzista.
- **Trigger SELL**: speculare — displacement ribassista, bias HTF
  ribassista, prezzo nella metà superiore del gap.
- **Score**: 73 su entrambi i lati.
- **Post-apertura**: SL/TP propri — SL oltre il bordo del gap ∓0.4×ATR,
  TP a 2.5× il rischio.
- **Stato**: nessun verdetto storico di merito documentato nel codice.

## 2.49 DISP_REBAL

- **File/funzione**: `NXS_Strat_DisplacementRebalance()`,
  `NXS_Strategies_Institutional.mqh:572`.
- **Gate**: `InpUseStrat_DispRebal` (interno) + `NXS_SelectorAllows(35)`
  (esterno, `NEXUS_EA_v2.mq5:482`).
- **Famiglia**: SMC/ICT — rebalance di un'inefficienza (FVG) lasciata da
  un displacement, concettualmente vicino a LIQ_VOID ma con soglie
  diverse (corpo ≥1.3×ATR, lookback 8 barre invece di 12) e target
  esplicito basato sull'estensione del gap stesso.
- **Timeframe**: `NXS_EffTF()`.
- **Storia documentata nel codice (17/07 notte, audit esterno) — CE
  (Consequent Encroachment) corretto**: la versione precedente usava il
  50% dell'INTERA candela di displacement come "CE" — questo non è il
  rebalance di un'inefficienza, è un retracement al 50% della candela
  impulso. Un vero rebalance ICT/SMC torna al 50% del FVG lasciato dal
  displacement, non della candela stessa. Corretta usando la stessa
  geometria FVG a 3 candele già sistemata per LIQ_VOID nella stessa
  sessione.
- **Trigger BUY**: displacement rialzista (corpo ≥1.3×ATR) nelle ultime
  8 barre con gap FVG valido (>0.1×ATR), prezzo rientrato tra il bordo
  basso del gap e il CE (+0.15×ATR di margine), chiusura rialzista.
- **Trigger SELL**: speculare.
- **Score**: 72 su entrambi i lati.
- **Post-apertura**: SL/TP propri — SL oltre il bordo del gap ∓0.3×ATR,
  TP al massimo tra un'estensione dell'ampiezza del gap stesso (+0.8× la
  sua ampiezza oltre il bordo lontano) e un target a 2.4× il rischio.
- **Stato**: nessun verdetto storico di merito documentato nel codice;
  nota di geometria condivisa con LIQ_VOID come unico dato tecnico
  rilevante.

## 2.50 RANGE_FADE

- **File/funzione**: `NXS_Strat_RangeFade()`,
  `NXS_Strategies_Institutional.mqh:645` (v2.0.8).
- **Gate**: `InpUseStrat_RangeFade` (interno) + `NXS_SelectorAllows(37)`
  (esterno, `NEXUS_EA_v2.mq5:485`).
- **Famiglia**: mean-reversion su range laterale QUALIFICATO — non un
  semplice ADX basso, un range validato con più criteri persistenti
  sull'intera finestra.
- **Timeframe**: `NXS_EffTF()`, gate a chiusura barra per la
  qualificazione (rivalutata una volta per barra), entry valutata sulla
  barra chiusa 1.
- **Storia documentata nel codice (17/07 notte, audit esterno) —
  qualificazione del range resa persistente**: prima bastava l'ultima
  lettura di ADX (ritardato, può essere basso anche subito dopo un
  trend) su una finestra di 40 barre presa per buona senza verificare
  che fosse DAVVERO stata laterale. Ora un range "CONFIRMED" richiede,
  su TUTTA la finestra di `InpRangeFade_Lookback` (40) barre: (1)
  persistenza ADX (≥`InpRangeFade_ADXPersistPct`, default 70%, delle
  barre sotto soglia 20, non solo l'ultima lettura); (2) ampiezza
  stabile tra prima e seconda metà della finestra (drift massimo
  `InpRangeFade_MaxWidthDrift`, default 0.35 = 35%); (3) almeno
  `InpRangeFade_MinTouches` (2) contatti per lato, separati da almeno
  `InpRangeFade_MinBarsBetweenTouches` (3) barre; (4) occupazione
  bilanciata del prezzo (chiusure sopra il midpoint tra il 30% e il
  70% del tempo — non un range dove il prezzo vive quasi sempre da un
  lato); (5) nessun breakout accettato (chiusura oltre il bordo +
  buffer) nelle ultime `InpRangeFade_NoBreakoutBars` (5) barre. Entry
  solo su barra chiusa 1 — niente più bid live per decidere la vicinanza
  al bordo (stesso principio di rigore già applicato altrove nel
  motore, es. MALAYSIAN_SNR).
- **Trigger BUY**: range confermato (i 5 criteri sopra) AND il minimo
  della barra chiusa 1 tocca il bordo basso del range (entro 0.4×ATR)
  AND chiusura rialzista sopra il bordo basso AND corpo ≥0.25×ATR
  (evita candele insignificanti).
- **Trigger SELL**: speculare sul bordo alto.
- **Score**: 68 su entrambi i lati.
- **Post-apertura**: SL/TP propri — SL oltre il bordo del range
  ±0.4×ATR, TP al punto medio del range (o un target a 2.0× il rischio,
  se più vicino — usa il minimo tra i due, cioè il più conservativo).
- **Stato**: nessun verdetto storico di merito documentato nel codice.

---

**Fine di `NXS_Strategies_Institutional.mqh` (789 righe, esclusi gli
helper di asset class alla fine del file che non sono strategie di
trading).** Nota trasversale: tutte le strategie di questo file
condividono il pattern di gate `InpUseStrat_x` (non `InpStrat_x`) — un
secondo pattern di naming per i flag del primo cancello, diverso da
quello usato nel file principale e in gran parte del file SMC.

## 2.51 ELLIOTT

- **File/funzione**: `NXS_Strat_Elliott()`, `NXS_Strategies_Elliott.mqh:37`
  (file dedicato, 151 righe, "strategia #37" secondo l'intestazione del
  file), con helper `_nxs_ell_pivots()` (:14, estrazione di fino a 8
  pivot di swing alternati) e `_nxs_ell_retrace()` (:31, calcolo
  frazione di ritracciamento Fibonacci).
- **Gate**: `InpUseStrat_Elliott` (interno) + `NXS_SelectorAllows(36)`
  (esterno, `NEXUS_EA_v2.mq5:488`).
- **Famiglia**: Elliott Wave — conteggio onde su swing high/low alternati,
  con TRE varianti di trigger distinte nella stessa funzione (non una
  sola logica): due di continuazione e una di reversal.
- **Timeframe**: `NXS_EffTF()`.
- **Dipendenze**: rilevatori di swing condivisi `NXS_IsSwingHigh`/
  `NXS_IsSwingLow` (parametro "wing", default 3, `InpEllSwingWing`), ATR.
- **Meccanica generale**: estrae fino a 8 pivot alternati (mai due dello
  stesso tipo consecutivi) partendo dal più recente, scansionando fino a
  100 barre indietro. In base a quanti pivot alternati esatti si
  susseguono (3, 5 o 6) e alla loro relazione di prezzo (impulso valido:
  onde successive non si sovrappongono nel modo sbagliato), riconosce
  tre pattern:
  1. **Continuazione fine onda 2 → onda 3** (richiede 3 pivot):
     ritracciamento dell'onda 2 tra `InpEllRetraceMin` e
     `InpEllRetraceMax` della gamba precedente, con conferma di candela
     nella direzione dell'onda 1 e prezzo ancora sotto/sopra il massimo/
     minimo dell'onda 1.
  2. **Continuazione fine onda 4 → onda 5** (richiede 5 pivot, impulso
     valido: onda 4 non entra nel territorio dell'onda 1): ritracciamento
     dell'onda 4 tra 0.236 e 0.618 (soglie fisse, non gli input
     Min/Max usati per l'onda 2).
  3. **Reversal a fine onda 5** (richiede 6 pivot, impulso a 5 onde
     completo con massimi/minimi monotoni coerenti): scommette sulla
     correzione dopo un impulso completo, direzione OPPOSTA al trend
     appena concluso.
- **Trigger BUY (tre varianti)**: W2→W3 (impulso rialzista, pivot
  L2/H1/L0 nella sequenza -1/+1/-1, ritracciamento in range, candela di
  conferma rialzista); W4→W5 (impulso rialzista a 5 pivot, ritracciamento
  onda4 in 0.236-0.618); reversal BUY dopo un impulso ribassista
  completo a 6 pivot (scommette sulla correzione verso l'alto).
- **Trigger SELL**: le tre varianti speculari.
- **Score**: variabile per variante — W2→W3: `InpEllMinScore + 4`;
  W4→W5: `InpEllMinScore` (base); reversal W5: `InpEllMinScore - 4` (il
  meno affidabile dei tre, penalizzato di proposito nello score).
- **Post-apertura**: SL/TP propri e distinti per variante — W2→W3: SL
  oltre l'onda 2/0 ∓0.4×ATR, TP a proiezione 1.618× la gamba onda1
  (obiettivo tipico dell'onda 3, la più estesa); W4→W5: SL oltre l'onda 4
  ∓0.4×ATR, TP a proiezione 1.0× (onda 5 ≈ lunghezza onda1-3); reversal
  W5: SL oltre l'estremo dell'onda 5 ∓0.5×ATR, TP a ritracciamento 50%
  dell'intero impulso.
- **Stato**: nessun verdetto storico di merito documentato nel codice
  per nessuna delle tre varianti.

---

**Fine di `NXS_Strategies_Elliott.mqh` (151 righe) — ultimo file di
implementazione strategie letto.**

## 2.52 Nota di chiusura — riconciliazione registro vs implementazioni

Le **51 funzioni `NXS_Strat_` trovate** nei quattro file di
implementazione coprono, con le identità (`stratName`) effettive lette
nel codice (non i nomi delle funzioni, spesso diversi):

ADX_RSI, BOLLINGER, MACD, SAR, BAR_UPDN, PMAX, MACD_SMA200,
ICHIMOKU_HULL_MACD, 3COMMAS_BOT, PIVOT_WICK, LEVEL_CONFLUENCE,
LEVEL_CONFLUENCE_M5, LEVEL_REACTION, LEVEL_REACTION_M5, TSI, BJORGUM,
LIQ_SWEEP, FVG_CONT, BREAKOUT_ACC, Z_SCORE_BREAKOUT, LONDON_BO,
EMA_PULLBACK, BB_SQUEEZE, ICHIMOKU, RSI_DIV_PINE, RSI_DIV, ORDER_BLOCK,
STRUCT_REACT (28, da `NXS_Strategies.mqh`) — TURTLE_SOUP,
SWING_FALSEBREAK, IFVG, FVG_MIT, FVG_MIT_WINDOW, OB_MIT, SH_BMS_RTO,
SH_BMS_RTO_V2, SMS_BMS_RTO, SILVER_BULLET, AMD_REVERSAL, OTE_CONT,
MALAYSIAN_SNR, CRT (14, da `NXS_Strategies_SMC.mqh`) —
THREE_BAR_DELIVERY_BREAK, AMD_CONT, JUDAS_SWING, LDN_REVERSAL,
NY_REVERSAL, WEEKLY_EXP, PO3, LIQ_VOID, DISP_REBAL, RANGE_FADE (10, da
`NXS_Strategies_Institutional.mqh`) — ELLIOTT (1, da
`NXS_Strategies_Elliott.mqh`).

**Confronto con i 49 nomi di `NXS_StrategyKnown()` (§1.7)**:

- **OB_MIT non è una strategia indipendente**: riusa integralmente
  `NXS_Strat_OrderBlock()`/`NXS_OB_UpdateSide()` (§2.32) — stesso
  trigger byte per byte di ORDER_BLOCK, solo `stratName` ed eventuale
  floor di score diversi. Chi cerca la "logica di OB_MIT" nel codice sta
  cercando la logica di ORDER_BLOCK.
- **FVG_MIT_WINDOW e CRT non compaiono nella lista dei 49 nomi
  catturata da `NXS_StrategyKnown()`** in questa lettura — sono
  implementazioni reali, con logica propria e in un caso (CRT)
  validazione molto robusta, ma sembrano vivere FUORI dal registro
  canonico a 49 voci. Questo potrebbe voler dire che (a) sono
  intenzionalmente escluse dalla telemetria/validazione basata sul
  registro, oppure (b) il nome nel registro è leggermente diverso da
  quello scritto in `stratName` e non è stato individuato nel testo
  grezzo catturato. Va verificato direttamente contro il contenuto
  aggiornato di `NXS_StrategyRegistry.mqh` prima di trarre conclusioni
  operative (es. prima di escluderle da un audit statistico che si
  affida al registro).
- **FVG_CONT_V2 e SAR_FLIP**, citati nella direttiva come esempi storici
  di "nome nel registro senza implementazione", **non sono stati
  incontrati né come nome nel registro né come funzione implementata**
  in nessuno dei quattro file di strategie letti in questa sessione.
  Non è possibile confermare né smentire la loro esistenza pregressa
  con i file attualmente nel repository — è plausibile che siano stati
  rimossi in una pulizia precedente, ma questo non è verificato qui (
  richiederebbe una ricerca su `git log`/vault, fuori dallo scope di
  questa lettura di codice).
- **Gate mancanti in molte funzioni SMC/Institutional**: come notato
  nella chiusura di §2.40, gran parte delle strategie SMC non espone il
  proprio gate `InpStrat_x` internamente — il flag/selettore è applicato
  dal chiamante nel dispatcher di `NEXUS_EA_v2.mq5` (non ancora letto
  riga per riga per questo scopo specifico in questa sessione). Chi
  vuole disattivare singolarmente una di queste strategie deve cercare
  il punto di chiamata nel dispatcher, non modificare la funzione
  stessa.
- **Il quarto cancello `NXR_ZoneStrategyEnabled`** (§1.3 punto 4) è stato
  risolto leggendo direttamente `NXS_ReusePerformancePack.mqh`: NON si
  applica dentro le funzioni `NXS_Strat_IFVG_Reversal`,
  `NXS_Strat_FVG_Mitigation`, `NXS_Strat_OB_Mitigation_Structural`,
  `NXS_Strat_MalaysianSNR_Rejection` perché quelle funzioni sono un
  percorso LEGACY separato — il quarto cancello protegge invece l'accesso
  a un **motore a zone parallelo ("NXR shadow engine")** che è quello
  che esegue DAVVERO i trade live per queste 4 identità (con
  `stratName` in formato "X_NXR": IFVG_NXR, FVG_MIT_NXR, OB_MIT_NXR,
  MALAYSIAN_SNR_NXR — vedi dettaglio completo in §1.3 punto 4 e le note
  "ATTENZIONE" aggiunte a §2.29/2.30/2.32/2.39). Il quarto cancello
  richiama al proprio interno anche il primo e il secondo cancello
  (flag + `NXS_SelectorAllows`) per lo stesso indice/flag della funzione
  legacy corrispondente, quando `InpNXR_RespectNexusSwitches` è attivo —
  quindi disattivare `InpStrat_IFVG` disattiva ENTRAMBI i percorsi
  (legacy e NXR) per IFVG, ma la logica di trigger dei due percorsi resta
  comunque completamente diversa quando entrambi sono attivi.


