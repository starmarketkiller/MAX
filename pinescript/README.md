# NEXUS EA — Pine Script (terzo motore di verifica, TradingView)

Questa cartella contiene strategie NEXUS portate su Pine Script v6, come
**terzo motore di verifica indipendente** da MT5 (l'EA reale) e dal backtest
lab interno (`server/backtest.py`, motore Python su dati Yahoo). Scopo: capire
se il segnale di queste strategie regge anche su un terzo dataset/motore
(dati e matching-engine di TradingView), non sostituire gli altri due.

**Batch 1** — le 4 peggiori del portafoglio sui 6 anni MT5 segmentati (vedi
`vault/01-Trading/NEXUS EA - Backtest 10Y Segmentato - Analisi.md`), nessuna
fonte esterna diretta trovata per loro (sono indicatori classici, non
concetti SMC/ICT):

| File | Strategia | Timeframe | Tipo |
|---|---|---|---|
| `NEXUS_SAR.pine` | SAR | H4 | Trend-following (Parabolic SAR + EMA9/21) |
| `NEXUS_MACD.pine` | MACD | H4 | Trend-following (MACD 12/26/9 + EMA200) |
| `NEXUS_ADX_RSI.pine` | ADX_RSI | D1 | Trend-following (EMA50 + banda RSI — **non usa un vero ADX**, vedi sotto) |
| `NEXUS_RSI_DIV.pine` | RSI_DIV | H1 | Reversal/divergenza (RSI vs prezzo, finestra 8 barre) |

**Batch 2** (18/07) — logica corretta il 17/07 notte da un'altra sessione
(fix reali già in MQL5, verificati prima del porting):

| File | Strategia | Timeframe | Tipo |
|---|---|---|---|
| `NEXUS_TSI.pine` | TSI | D1 | Momentum (vero True Strength Index di Blau, cross su signal line) |
| `NEXUS_LIQ_VOID.pine` | LIQ_VOID | H4 | SMC/ICT (Fair Value Gap 3 candele, retest del CE) |
| `NEXUS_DISP_REBAL.pine` | DISP_REBAL | H4 | SMC/ICT (stessa geometria FVG, entry sul CE — **disabilitata in produzione MT5**, vedi sotto) |
| `NEXUS_ORDER_BLOCK.pine` | ORDER_BLOCK | D1 | SMC/ICT (zona origine pre-displacement + BOS, macchina a stati con retest one-shot) |

**Batch 3** (30/07) — le prime due strategie SMC/ICT del portafoglio con fix
di fedeltà reali appena chiusi in MQL5 (F-05 e F-02 nel
`NEXUS_STRATEGY_FIDELITY_REPORT_01.md`), portate qui per verificarne l'edge
su un terzo motore prima ancora che la modifica MQL5 sia stata compilata:

| File | Strategia | Timeframe | Tipo |
|---|---|---|---|
| `NEXUS_MALAYSIAN_SNR.pine` | MALAYSIAN_SNR | D1 | SMC/ICT (Support/Resistance H4 con conferma W1, storyline H4, F-05: contatore utilizzi per livello) |
| `NEXUS_SILVER_BULLET.pine` | SILVER_BULLET | M15 | SMC/ICT (Silver Bullet ICT — sweep di liquidità cascata + FVG nelle killzone ET, F-02: killzone DST-aware) |

Scope di questo lavoro: le 10 strategie sopra (Batch 1+2+3). Nessuna
modifica a `server/backtest.py`. Le uniche modifiche MQL5 correlate sono i
fix F-05/F-02 già committati separatamente in `MQL5/Include/NEXUS_v1/`.

## Come usarle nello Strategy Tester di TradingView

1. Apri un chart **XAUUSD** (o il ticker gold del tuo broker/feed su
   TradingView) sul **timeframe nativo della strategia** (vedi tabelle sopra —
   H4 per SAR/MACD/LIQ_VOID/DISP_REBAL, D1 per ADX_RSI/TSI/ORDER_BLOCK, H1 per
   RSI_DIV). Ogni script mostra un avviso a schermo se il chart è su un TF
   diverso da quello previsto.
2. Apri il **Pine Editor**, incolla il contenuto del file `.pine`, premi
   "Add to chart".
3. Apri il pannello **Strategy Tester** (in basso) per vedere Net Profit,
   Profit Factor, Win Rate, Max Drawdown e la lista trade — le stesse metriche
   usate nelle analisi MT5/sito nel vault, così i numeri sono confrontabili
   direttamente.
4. **Batch 1** (SAR/MACD/ADX_RSI/RSI_DIV): ogni script ha un input
   **"Configurazione SL/TP/BE"** con due opzioni, ma il significato **non è lo
   stesso per tutte le strategie** — dipende da cosa gira davvero in
   produzione oggi:
   - **SAR e RSI_DIV**: "Baseline (config attuale)" = config live in
     `NXS_StrategyProfiles.mqh`; "Variante TP-largo(+BE)" = ipotesi
     alternativa dall'analisi MFE/MAE del 17/07, **mai applicata in
     produzione** (miglioramento marginale/ambiguo per queste due).
   - **MACD e ADX_RSI**: "Baseline (config attuale)" = il fix TP-largo+BE
     del 17/07, che è **già la config live in produzione** oggi in
     `NXS_StrategyProfiles.mqh`; "Config pre-fix (17/07, storica)" = la
     config precedente, tenuta solo come riferimento storico per il
     confronto — **non** rappresenta un'ipotesi ancora da validare.
   Esegui il test con entrambe le opzioni (stesso range di date, stesso
   capitale) e confronta PF/Drawdown/Net.
5. **Batch 2** (TSI/LIQ_VOID/DISP_REBAL/ORDER_BLOCK): una sola configurazione
   ciascuna (quella del profilo MQL5 attuale, senza distinzione baseline/
   variante — non è emersa alcuna analisi MFE/MAE per queste 4). LIQ_VOID ha
   due toggle HTF indipendenti (vedi sezione dedicata) e DISP_REBAL è
   **disabilitata in produzione MT5** oggi (portata comunque per completezza).
6. **Batch 3** (MALAYSIAN_SNR/SILVER_BULLET): una sola configurazione
   ciascuna, già col fix di fedeltà applicato (F-05 per MALAYSIAN_SNR, F-02
   per SILVER_BULLET — vedi "Riepilogo logica" sotto). Per SILVER_BULLET usa
   un chart **M15**: il TF nativo è granulare, quindi TradingView potrebbe
   offrire meno storico intraday del previsto sul piano Basic (stesso limite
   già osservato per RSI_DIV H1, vedi nota sotto).
7. Range di date di default: 2019-01-01 → oggi, per allinearsi alla finestra
   dei 6 anni "affidabili" usata nel backtest 10Y segmentato MT5. Modificabile
   dagli input in cima allo script.
7. Quantità fissa a 1 contratto per tutte (non è calibrata sul lot sizing
   MT5): l'obiettivo qui è confrontare PF/Win Rate/Drawdown% (metriche a
   rapporto, insensibili alla size) trade per trade, non riprodurre l'equity
   in $ dell'EA reale. Commissioni e slippage sono a 0 di default — aggiungili
   dalle proprietà della strategia se vuoi un test più realistico.

## Regola anti-repaint (importante, applicata in tutti gli script)

- `calc_on_every_tick = false` in ogni `strategy()`: le condizioni d'ingresso
  sono valutate sulla **barra chiusa** e l'ordine si riempie all'apertura
  della barra successiva. È lo stesso modello di MQL5, che legge
  SAR/EMA/MACD/RSI con `shift=1` (ultima barra chiusa) e apre a mercato subito
  dopo — mai sulla barra "live"/in formazione.
- Il filtro HTF di SAR/MACD/ADX_RSI/TSI/ORDER_BLOCK è EMA200 sullo **stesso**
  timeframe (non multi-TF, non serve `request.security`) — vedi sezione
  dedicata sotto per i dettagli e per la correzione fatta il 18/07.
- La divergenza RSI_DIV confronta solo barre già chiuse (`[1]` e `[8]`): nessun
  pivot ricalcolato a posteriori, quindi nessun repaint strutturale.
- **LIQ_VOID/DISP_REBAL/ORDER_BLOCK**: in MQL5 il retest della zona usa il
  prezzo BID **live** (tick-by-tick), non riproducibile senza
  `calc_on_every_tick=true` (che reintrodurrebbe repaint altrove nello
  script). Qui il "tocco" è approssimato col range low/high della barra
  appena chiusa, la stessa barra usata per la candela di rigetto —
  semplificazione documentata anche nell'intestazione di ciascuno script.

## Riepilogo logica per strategia

### SAR (H4)
- **Indicatori**: Parabolic SAR (step 0.02, max 0.2), EMA9, EMA21, ATR(14).
- **BUY**: SAR sotto il prezzo E EMA9 > EMA21. **SELL**: speculare.
- **SL/TP baseline**: SL 1.5×ATR, TP 4.0×ATR, no breakeven.
- **SL/TP variante**: stesso SL/TP, breakeven a 1.5×R (test ambiguo nel piano:
  PF sale ma net scende leggermente — disponibile solo per confronto manuale).
- **Filtro HTF**: attivo (EMA200 stesso TF, vedi sotto).
- **Nota**: nessun trailing stop reale (`trailATR=0` nel profilo attuale — il
  test MFE/MAE ha confermato che il trailing non aiuta su questa famiglia di
  strategie, la leva è SL/TP fisso + eventuale breakeven).

### MACD (H4)
- **Indicatori**: MACD line = EMA12 − EMA26, signal = **SMA9** della MACD line
  (MT5 `iMACD` usa SMA per il segnale, non EMA — differenza dal MACD
  "standard" di TradingView, riprodotta a mano nello script), EMA200, ATR(14).
- **BUY**: MACD line > signal E MACD line > 0 E close > EMA200. **SELL**: speculare.
- **SL/TP baseline (= config live oggi in produzione)**: SL 2.0×ATR,
  TP 8.0×ATR, breakeven a 1.0×R — fix reale applicato il 17/07 dopo
  l'analisi MFE/MAE (PF 1.48→2.05 sul motore sito), già in
  `NXS_StrategyProfiles.mqh`.
- **SL/TP config pre-fix (storica)**: SL 2.0×ATR, TP 3.0×ATR, no breakeven —
  la config precedente al fix del 17/07, qui solo come riferimento.
- **Filtro HTF**: attivo (EMA200 stesso TF) ma **ridondante** — il trigger
  richiede già close vs EMA200, vedi sotto.

### ADX_RSI (D1)
- **Indicatori**: EMA50 (pendenza + posizione prezzo), RSI(14), ATR(14).
  **Non calcola un vero ADX** nonostante il nome — errore storico di naming
  documentato nel vault, riprodotto fedelmente così com'è nel codice reale.
- **BUY**: EMA50 in salita E RSI in banda (45,65) E close > EMA50. **SELL**: speculare (EMA50 in discesa, RSI in banda (35,55), close < EMA50).
- **SL/TP baseline (= config live oggi in produzione)**: SL 1.0×ATR,
  TP 10.0×ATR, breakeven a 1.5×R — fix reale applicato il 17/07 dopo
  l'analisi MFE/MAE (PF 1.48→1.97 sul motore sito), già in
  `NXS_StrategyProfiles.mqh`.
- **SL/TP config pre-fix (storica)**: SL 1.0×ATR, TP 4.0×ATR, no breakeven —
  la config precedente al fix del 17/07, qui solo come riferimento.
- **Filtro HTF**: attivo (EMA200 stesso TF) — qui aggiunge un vincolo
  indipendente dal trigger (che usa EMA50, non EMA200).

### RSI_DIV (H1)
- **Indicatori**: RSI(14), finestra fissa di 8 barre (non un pivot/zigzag).
- **BUY (divergenza bullish)**: low[1] < low[8] E RSI[1] > RSI[8] E RSI[1] < 40.
- **SELL (divergenza bearish)**: high[1] > high[8] E RSI[1] < RSI[8] E RSI[1] > 60.
- **SL/TP baseline**: SL 1.0×ATR, TP 4.5×ATR, no breakeven.
- **SL/TP variante**: SL 1.0×ATR, TP 10.0×ATR — miglioramento solo marginale
  nel test del 17/07, **non applicata in produzione**; qui solo per confronto.
- **Filtro HTF**: **disattivato** — con l'HTF attivo il campione crolla a 0-4
  trade su ogni timeframe testato (vedi vault "Fix Blocco 4").

### TSI (D1)
- **Indicatori**: True Strength Index di Blau — doppio EMA (long=25, short=13)
  del price change, diviso per il doppio EMA dell'abs(price change), ×100;
  signal line = EMA a 7 periodi del TSI. ATR(14) per SL/TP.
- **BUY**: TSI incrocia sopra la signal line (crossover). **SELL**: speculare
  (crossunder).
- **SL/TP**: SL 1.5×ATR, TP 4.5×ATR, breakeven a 1.0×R. Una sola config (dal
  profilo attuale, nessuna variante nota).
- **Filtro HTF**: attivo (EMA200 stesso TF) — vincolo indipendente, il
  trigger non usa EMA200.

### LIQ_VOID (H4)
- **Indicatori**: geometria Fair Value Gap a 3 candele (displacement ≥1.2×ATR
  entro 12 barre), ATR(14).
- **BUY**: zona bullish valida (Low candela3 > High candela1, larghezza
  ≥0.3×ATR), prezzo rientra nella metà inferiore della zona (fino al CE) con
  candela di rigetto rialzista. **SELL**: speculare.
- **SL/TP**: **non** un multiplo ATR generico — SL = bordo zona ∓ 0.4×ATR,
  TP = 2.5×R fisso, calcolati dalla geometria della zona stessa. Nessun
  breakeven.
- **Filtro HTF**: **due meccanismi indipendenti**, entrambi devono passare —
  vedi sezione dedicata sotto (`requireBiasHtf` è **requisito core del
  trigger**, non un gate opzionale; in MT5 di default è spento e la
  strategia non genera mai segnali).

### DISP_REBAL (H4) — ⚠️ disabilitata in produzione MT5
- **Indicatori**: stessa geometria FVG a 3 candele di LIQ_VOID (displacement
  ≥1.3×ATR entro 8 barre), ATR(14).
- **BUY**: FVG bullish valido (gap minimo 0.1×ATR), prezzo rientra fra il
  bordo basso del FVG e poco oltre il CE (consequent encroachment, 50% del
  gap — non il 50% della candela displacement come nella versione
  pre-17/07), candela di rigetto rialzista. **SELL**: speculare.
- **SL/TP**: SL = bordo FVG ∓ 0.3×ATR; TP **dinamico** = il più lontano fra
  un'estensione dello 0.8× oltre il bordo lontano del FVG e un fisso 2.4×R.
  Nessun breakeven.
- **Filtro HTF**: nessuno (il profilo ha `htf=false`, la funzione MQL5 non
  richiede alcun bias).
- **Stato**: `NXS_Profile_Enabled()` la marca disabilitata in MQL5 ("v2.3.1
  test reale: 10 trade, -53$, WR 30%") — non è live sull'EA oggi, portata
  comunque su Pine per completezza di verifica.

### ORDER_BLOCK (D1)
- **Indicatori**: macchina a stati persistente (zona buy e zona sell
  indipendenti) — non una condizione a singola barra come le altre 7. ATR(14).
- **Ricerca zona**: displacement (corpo ≥1.2×ATR) entro 3-10 barre fa (più
  vicino prima) che rompe uno swing di riferimento su 15 barre precedenti
  (BOS) → l'origine della zona è l'ultima candela di colore **opposto**
  entro le 6 barre prima del displacement (più vicina prima).
- **Ciclo di vita zona**: attiva fino al primo retest (one-shot), scade dopo
  20 barre di attesa, si invalida se una barra chiude attraversandola
  completamente nel verso sbagliato.
- **BUY**: zona buy attiva, prezzo la tocca, ultima barra chiusa è candela
  di rigetto rialzista. **SELL**: speculare.
- **SL/TP**: SL 1.0×ATR, TP 3.0×ATR (standard, via formula ATR come nel
  Batch 1). Nessun breakeven.
- **Filtro HTF**: attivo (EMA200 stesso TF).
- **Semplificazioni note (omesse di proposito)**: il codice reale ha due
  filtri aggiuntivi non replicati qui — conferma struttura H1 esterna
  (`g_structH1.trend`, calcolo fractal/CHoCH stateful) e uno "SMC reaction
  gate" generico (`NXS_SMCReactionOK`). Entrambi attivi di default in MQL5:
  la versione Pine è quindi **meno filtrata** (più segnali) del comportamento
  MT5 reale.

### MALAYSIAN_SNR (D1)
- **Indicatori**: livelli Support/Resistance H4 (max/min 12 barre H4, offset
  1 = ultima barra H4 chiusa), confluenza opzionale con livello W1
  equivalente, "storyline" H4 (candela shift1 vs shift4, per stabilire se il
  livello è stato appena testato con momentum a favore), ATR(14) su D1 e
  ATR(14) su H4 (letto via `request.security`, serve per il fix F-05).
- **BUY**: prezzo D1 tocca/rientra nel livello H4 di supporto (± tolleranza
  ATR), storyline H4 conferma rigetto rialzista, **e il contatore utilizzi
  per quel livello non ha già raggiunto il massimo** (fix F-05, vedi sotto).
  **SELL**: speculare sul livello di resistenza.
- **F-05 — contatore utilizzi per livello** (chiude la divergenza F-05 del
  fidelity report): in MQL5 lo stesso livello S/R poteva generare segnali
  ripetuti illimitati finché il prezzo continuava a rimbalzarci; il codice
  reale ora traccia il livello H4 corrente con una tolleranza pari a
  `0.3×ATR(H4)` (stesso livello se il nuovo massimo/minimo H4 non si è
  spostato più di così) e permette **al massimo 2 utilizzi consecutivi**
  prima di richiedere che il livello H4 si aggiorni. Portato identico qui,
  con stato persistente `var float`/`var int` per livello Hi e Lo.
- **SL/TP**: **non** un multiplo ATR generico sul prezzo d'ingresso — SL
  appena oltre il livello H4 (± buffer ATR sul lato sbagliato), TP proiettato
  verso il livello opposto (pattern "pending" a due step, come LIQ_VOID/
  DISP_REBAL, perché la geometria dipende dalla barra segnale, non dalla
  barra di riempimento). Nessun breakeven/trailing dedicato (usa il fallback
  globale se il profilo non ne specifica uno — vedi "Gestione uscita" sotto).
- **Filtro HTF**: attivo (EMA200 stesso TF D1), replica il toggle `htf=true`
  del profilo MQL5 attuale.
- **Time-exit**: 40 barre D1, stessa convenzione delle altre 9.
- **Semplificazioni note (omesse di proposito)**: il bonus di score per
  livello "fresh" (mai toccato prima) è solo informativo in MQL5 — non
  condiziona l'ingresso, quindi omesso; il filtro che salta la sessione
  Asia è un concetto intraday senza significato su valutazione a barra
  D1 chiusa, quindi omesso; i livelli H4/W1 sono letti come aggregati via
  `request.security` (da un chart D1) invece che con loop barra-per-barra
  nativi H4/W1 — equivalente per come vengono usati qui (solo max/min su
  finestra fissa), ma non identico byte-per-byte al loop MQL5.

### SILVER_BULLET (M15)
- **Indicatori**: nessun indicatore classico — è un modello di **sweep di
  liquidità cascata + Fair Value Gap** nelle killzone orarie ICT. Range Asia
  (scansione M15 sulle ultime 96 barre = 24h), PDH/PDL (Previous Day
  High/Low), PWH/PWL (Previous Week), PMH/PML (Previous Month), tutti letti
  via `request.security`; priorità di override in cascata identica a
  `NXS_DetectSweepExt` (Monthly > Weekly > Daily > Asia > fallback Equal
  High/Low). ATR(14) su M15 per il buffer SL e la gestione uscita.
- **F-02 — killzone DST-aware** (chiude la divergenza F-02 del fidelity
  report): il codice reale usava due finestre a orario GMT fisso, sbagliate
  per metà dell'anno rispetto alle vere killzone ICT in orario di New York
  (3-4, 10-11, 14-15 ET). Qui la correzione usa il supporto nativo IANA di
  Pine (`hour(time, "America/New_York")`) per calcolare l'ora ET barra per
  barra — **più semplice e più affidabile** della replica manuale
  dell'algoritmo DST US fatta in MQL5 (2ª domenica di marzo → 1ª domenica di
  novembre), scelta deliberata e documentata nell'intestazione dello script.
- **BUY**: nella killzone, sweep ribassista rilevato (prezzo rompe sotto un
  livello di liquidità e richiude sopra) seguito da un FVG bullish nelle
  barre successive, macchina a stati (`IDLE → SWEPT → WAITING_RETURN →
  entry`) replica `NXS_SB_UpdateSide`/`ENUM_NXS_SB_STATE`. **SELL**:
  speculare (sweep rialzista + FVG bearish).
- **SL/TP**: SL oltre l'estremo dello sweep (± buffer ATR), TP via multiplo
  R fisso sulla distanza SL — pattern "pending" STEP1/STEP2 come
  MALAYSIAN_SNR, perché anche qui la geometria dipende dalla barra segnale.
- **Gestione uscita — l'unica delle 10 con breakeven+trailing genuini**:
  Silver Bullet non ha un profilo dedicato in `NXS_StrategyProfiles.mqh`,
  quindi in MQL5 usa il **fallback globale** di `NXS_Management.mqh`
  (diverso da tutte le altre 9, che usano SL/TP fissi da profilo). Replicato
  qui con un blocco dedicato che sposta lo stop a breakeven quando il
  profitto flottante raggiunge `beTriggerMult×ATR`, poi traila con
  `trailDistMult×ATR` (o `trailDistPostBEMult×ATR` dopo il breakeven) usando
  l'**ATR corrente/live**, non quello congelato all'apertura — a differenza
  del SL/TP iniziale (quello sì fisso all'ingresso).
- **Time-exit**: 40 barre M15 (`maxHoldBars`, stessa convenzione EA-wide di
  "~40 barre del TF della strategia" documentata in `NXS_Management.mqh`).
- **Filtro HTF**: nessuno (Silver Bullet in MQL5 non ha un gate HTF —
  la selettività viene dalle killzone + sweep + FVG, non da un bias di
  trend).
- **Semplificazioni note (omesse di proposito)**: il fallback Equal
  High/Low (usato in MQL5 quando nessuno sweep Asia/Daily/Weekly/Monthly è
  disponibile) non è replicato — se nessun livello di liquidità cascata è
  rilevato nella finestra, lo script semplicemente non genera un setup per
  quella barra, invece di cercare un pattern di doppio massimo/minimo
  approssimato.

## Filtro HTF — cos'è, e correzione del 18/07

**Corretto il 18/07** — la prima versione di questo filtro (SAR/MACD/ADX_RSI)
riproduceva `NXS_GetHTFBias`/`NXS_HTFBlocks` (EMA50 multi-timeframe H4+H1).
Verificando dove il flag `htf=true` del profilo viene davvero applicato
(`NEXUS_EA_v2.mq5`, riga ~344, dentro `InpUseStrategyProfiles=true` — il
default), è emerso che quel meccanismo **non è quello realmente attivo**:
`InpUseHTFBias` (che governa `NXS_GetHTFBias`) è **`false` di default**, un
gate opzionale mai acceso in produzione.

Il gate **davvero live** è molto più semplice: **EMA200 sullo stesso
timeframe della strategia**, confronto prezzo vs EMA200. Blocca i BUY se il
prezzo è sotto EMA200, i SELL se è sopra. Usato in SAR/MACD/ADX_RSI
(corretto il 18/07) e in TSI/ORDER_BLOCK (Batch 2, implementato corretto fin
dall'inizio). RSI_DIV e DISP_REBAL non hanno filtro HTF. LIQ_VOID è un caso a
parte — vedi sotto.

Una nota di fedeltà sul codice reale: lì il confronto è **asimmetrico**
(prezzo `shift 0`, cioè la barra ancora in formazione, vs EMA200 `shift 1`,
l'ultima barra chiusa) — probabilmente non intenzionale, ma presente. Qui in
Pine, coerentemente col resto dello script (modello a barra confermata,
anti-repaint), **entrambi i lati usano la barra confermata** — scelta
consapevole, non una replica esatta di quell'asimmetria.

**Impatto sui risultati già raccolti**: le tabelle di test più sotto sono
state generate **prima** di questa correzione, quindi con il vecchio filtro
EMA50 multi-timeframe (di fatto quasi sempre disattivo per SAR/MACD dato che
`InpUseHTFBias=false` non lo blocca comunque a livello EA — ma il
comportamento del filtro *dentro lo script Pine* era diverso da quello
descritto qui). Vale la pena rieseguire i 3 test con la versione corretta
per un confronto pulito.

### Caso speciale: LIQ_VOID ha DUE filtri HTF indipendenti

A differenza delle altre strategie, in `NXS_Strat_LiquidityVoid` il bias
multi-timeframe (EMA50 H4 + EMA50 H1, `NXS_GetHTFBias`) non è un gate
opzionale a valle — è un **requisito dentro il trigger stesso**: la funzione
riceve il risultato di `NXS_GetHTFBias()` come parametro e richiede
esplicitamente `bias==BULL` per i BUY / `bias==BEAR` per i SELL. Siccome
`InpUseHTFBias=false` di default, quel bias è sempre `NEUTRAL` in MT5 oggi —
**LIQ_VOID non genera mai segnali con le impostazioni di default reali**. Il
profilo di LIQ_VOID ha *anche* `htf=true`, quindi il gate generico EMA200
stesso-TF si applica **in aggiunta**, indipendentemente dal primo.

Lo script `NEXUS_LIQ_VOID.pine` espone entrambi come toggle separati:
`requireBiasHtf` (default ON, per rendere la strategia testabile — spegnerlo
replica il comportamento dormiente reale di oggi) e `useHtfFilter` (il gate
EMA200 generico, come le altre).

## Gestione uscita

**MALAYSIAN_SNR** (SL/TP dalla geometria del livello S/R, non ATR generico):
- Stesso pattern "pending" a due step di LIQ_VOID/DISP_REBAL: SL/TP calcolati
  una sola volta al momento del segnale come prezzi assoluti derivati dal
  livello H4 (± buffer ATR). Nessun breakeven/trailing dedicato in
  `NXS_StrategyProfiles.mqh` per questa strategia — usa il fallback globale
  se mai attivato, qui non replicato separatamente (nessuna evidenza che sia
  mai stato osservato attivo per questa strategia nei test reali).

**SILVER_BULLET** (l'unica delle 10 con breakeven+trailing genuini):
- SL iniziale fisso all'ingresso (oltre l'estremo dello sweep ± buffer ATR),
  ma poi gestito attivamente durante la vita del trade con lo stesso
  fallback globale di `NXS_Management.mqh` usato in MQL5 quando una
  strategia non ha un profilo dedicato — breakeven quando il profitto
  raggiunge `beTriggerMult×ATR(live)`, poi trailing con `trailDistMult×ATR`
  (o `trailDistPostBEMult×ATR` dopo breakeven). Vedi "Riepilogo logica" sopra
  per i dettagli — è un modello diverso da tutte le altre 9 strategie di
  questo README (che non modificano mai lo stop dopo l'apertura, a parte
  l'eventuale singolo salto a breakeven).

**SAR/MACD/ADX_RSI/RSI_DIV/TSI/ORDER_BLOCK** (SL/TP via formula ATR):
- SL/TP calcolati una sola volta all'apertura del trade, come multiplo
  dell'ATR(14) **al momento dell'ingresso** (non ricalcolato durante la vita
  del trade) — identico a `NXS_DefaultSLTP` in MQL5.
- Breakeven (dove beR > 0): quando il profitto flottante raggiunge `beR × R`
  (R = distanza SL iniziale), lo stop si sposta esattamente al prezzo
  d'ingresso — identico a `NXS_ManageBreakevenAndTrail`. TSI ha breakeven
  a 1.0×R; SAR/RSI_DIV/ORDER_BLOCK nella config attuale non lo usano.

**LIQ_VOID/DISP_REBAL** (SL/TP dalla geometria della zona, non ATR generico):
- SL/TP calcolati una sola volta al momento del segnale, come prezzi
  assoluti derivati dai bordi della zona FVG/void (± buffer ATR) — non un
  multiplo ATR generico applicato al prezzo d'ingresso. Nessun breakeven per
  nessuna delle due (beR=0 nel profilo).

**Tutte e 10**:
- **Time-exit a 40 barre**: se né SL né TP vengono toccati entro 40 barre dal
  timeframe della strategia, la posizione viene chiusa a mercato — replica il
  "time-based forced exit" reale di MQL5 (`~40 barre del TF della strategia`).
- Nessun trailing stop per le 9 con SL/TP fisso (`trailATR=0` nel profilo
  MQL5 attuale, confermato inefficace dal test MFE/MAE del 17/07 per il
  Batch 1) — l'eccezione è SILVER_BULLET, vedi sopra.

## Risultati dei test manuali — Batch 1 (SAR/MACD/ADX_RSI/RSI_DIV)

Test eseguiti con lo Strategy Tester nativo di TradingView su
**OANDA:XAUUSD**, `calc_on_every_tick=false`, capitale iniziale 10.000 USD.

> ⚠️ I risultati di **SAR/MACD/ADX_RSI** sotto sono stati raccolti **prima**
> della correzione del filtro HTF del 18/07 (vedi sezione "Filtro HTF —
> cos'è, e correzione del 18/07"). Da rieseguire con la versione corretta
> per un confronto pienamente valido.

> **Sintesi**: dei 4 motori indipendenti testati, **SAR/MACD/ADX_RSI
> confermano risultati profittevoli** e in linea con la direzione dei fix
> MFE/MAE del 17/07 — per MACD e ADX_RSI la config TP-largo+breakeven (che è
> anche quella live oggi in produzione) migliora PF e/o drawdown rispetto
> alla vecchia config pre-fix; per SAR il miglioramento della variante
> BE-only è marginale/ambiguo. **RSI_DIV mostra invece risultati
> deboli/in perdita** nel periodo campione disponibile su TradingView e
> merita ulteriore osservazione prima di trarre conclusioni (vedi nota sul
> campione dati sotto).

### SAR (H4) — range dati Jan 2, 2023 – Jul 17, 2026 (~3.5 anni)
| Config | Trade | PF | Win Rate | Max DD | Net PnL |
|---|---|---|---|---|---|
| Baseline (SL1.5×/TP4.0× ATR, no BE) | 406 | 1,276 | 37,44% (152/406) | 973,13 USD (7,52%) | +2.127,08 USD (+21,27%) |
| Variante TP-largo + BE 1.5×R (SL1.5×/TP4.0× ATR) | 404 | 1,30 | 34,65% (140/404) | 1.022,80 USD (7,79%) | +2.185,53 USD (+21,86%) |

Miglioramento marginale, variante non conclusivamente superiore alla
baseline (coerente con quanto già annotato nello script: il test MFE/MAE
del 17/07 aveva già segnalato questo caso come ambiguo).

### MACD (H4) — stesso range dati
| Config | Trade | PF | Win Rate | Max DD | Net PnL |
|---|---|---|---|---|---|
| Config pre-fix, storica (SL2.0×/TP3.0× ATR, no BE) | 292 | 1,321 | 48,29% (141/292) | 909,56 USD (7,61%) | +1.895,02 USD (+18,95%) |
| **Baseline = live oggi** (SL2.0×/TP8.0× ATR + BE 1.0×R) | 192 | 1,459 | 28,65% (55/192) | 778,88 USD (6,44%) | +1.955,65 USD (+19,56%) |

La config live oggi riduce nettamente il numero di trade (292→192) rispetto
alla vecchia config pre-fix, ma migliora PF e riduce il drawdown — coerente
col fix reale applicato in produzione il 17/07 lato sito.

### ADX_RSI (D1) — range filtrato da `startDate` dello script (2019-01-01)
| Config | Trade | PF | Win Rate | Max DD | Net PnL |
|---|---|---|---|---|---|
| Config pre-fix, storica (SL1.0×/TP4.0× ATR, no BE) | 217 | 1,326 | 29,49% (64/217) | 534,53 USD (5,25%) | +1.529,77 USD (+15,30%) |
| **Baseline = live oggi** (SL1.0×/TP10.0× ATR + BE 1.5×R) | 199 | 1,672 | 24,62% (49/199) | 483,12 USD (4,65%) | +1.950,87 USD (+19,51%) |

Miglioramento netto su tutti i fronti (PF, DD assoluto e %, PnL) rispetto
alla vecchia config pre-fix — coerente col fix reale applicato in produzione
il 17/07 lato sito.

> Nota tecnica: il date-picker del chart D1 mostrava un valore anomalo
> ("Jan 6 1833") durante il test, dovuto a un bug cosmetico di rendering di
> TradingView con zoom molto ampio su D1 (probabile overlay di un secondo
> simbolo storico) — non un problema del filtro date dello script. I trade
> restano correttamente filtrati dagli input `startDate`/`endDate`, quindi i
> numeri sopra sono validi.

### RSI_DIV (H1) — range dati Jan 2, 2025 – Jul 17, 2026 (~1.5 anni)
| Config | Trade | PF | Win Rate | Max DD | Net PnL |
|---|---|---|---|---|---|
| Baseline (SL1.0×/TP4.5× ATR) | 338 | 0,931 | 20,41% (69/338) | 1.290,93 USD (12,67%) | −339,20 USD (−3,39%) |
| Variante TP-largo (SL1.0×/TP10.0× ATR) | 341 | 0,989 | 20,82% (71/341) | 789,53 USD (7,83%) | −52,12 USD (−0,52%) |

Entrambe le configurazioni sono in perdita/breakeven sul campione
disponibile, a differenza del quadro più favorevole probabilmente osservato
su dataset MT5 più lunghi. **Non trarre conclusioni definitive**: campione
troppo corto e specifico per questo periodo di mercato.

> **Limite del dato, non della strategia**: TradingView (piano Basic) mette
> a disposizione solo ~1,5 anni di storico intraday H1 per OANDA:XAUUSD,
> molto più corto dei ~3,5 anni usati per SAR/MACD (H4) — verificato che non
> è un artefatto di zoom (tentato zoom/pan del chart per forzare più
> storico, senza risultato: è il limite reale dei dati disponibili sul
> piano). I risultati RSI_DIV qui sopra vanno letti in questo contesto.

### Osservazioni (Batch 1)
- SAR, MACD e ADX_RSI confermano un edge positivo su un terzo motore/dataset
  indipendente da MT5 e dal sito. Per MACD e ADX_RSI la config TP-largo+BE
  (live oggi in produzione) migliora PF e/o drawdown rispetto alla vecchia
  config pre-fix, in linea con l'analisi MFE/MAE del 17/07; per SAR la
  variante BE-only resta marginale/ambigua rispetto alla baseline.
- RSI_DIV è l'unica delle 4 in perdita/breakeven su questo campione, ma il
  campione (~1,5 anni, limite del piano TradingView) è troppo corto per
  giudicarla — da rivalidare quando sarà disponibile più storico o un feed
  con maggiore profondità intraday.
- Prossimo passo naturale: confrontare questi numeri con l'equivalente
  finestra temporale sul motore sito e su MT5 per vedere se le divergenze
  già note tra motori (vedi `NEXUS EA - Principi.md` #5) si ripresentano
  anche qui.
- ⚠️ Vedi anche l'avviso in cima a questa sezione: SAR/MACD/ADX_RSI vanno
  rieseguiti con la versione corretta del filtro HTF (18/07) prima di
  considerare queste osservazioni definitive.

## Risultati dei test manuali — Batch 2 (TSI/LIQ_VOID/DISP_REBAL/ORDER_BLOCK)

Da compilare dopo i test manuali, stesso formato del Batch 1 sopra.

### TSI (D1)
| Config | Periodo | Trade | PF | Win Rate | Max DD | Net PnL |
|---|---|---|---|---|---|---|
| Config attuale (SL1.5×/TP4.5×/BE1.0R) | | | | | | |

### LIQ_VOID (H4)
| Config | Periodo | Trade | PF | Win Rate | Max DD | Net PnL |
|---|---|---|---|---|---|---|
| `requireBiasHtf`=ON (default, testabile) | | | | | | |
| `requireBiasHtf`=OFF (replica comportamento reale dormiente) | | | | | | |

### DISP_REBAL (H4) — disabilitata in produzione, solo verifica
| Config | Periodo | Trade | PF | Win Rate | Max DD | Net PnL |
|---|---|---|---|---|---|---|
| Config attuale (geometria FVG/CE) | | | | | | |

### ORDER_BLOCK (D1)
| Config | Periodo | Trade | PF | Win Rate | Max DD | Net PnL |
|---|---|---|---|---|---|---|
| Config attuale (SL1.0×/TP3.0×, no BE) | | | | | | |

### Osservazioni (Batch 2)
_(da compilare)_

## Risultati dei test manuali — Batch 3 (MALAYSIAN_SNR/SILVER_BULLET)

Da compilare dopo i test manuali, stesso formato dei batch precedenti.

### MALAYSIAN_SNR (D1)
| Config | Periodo | Trade | PF | Win Rate | Max DD | Net PnL |
|---|---|---|---|---|---|---|
| Config attuale (livello H4 + conferma W1, F-05 max 2 utilizzi/livello) | | | | | | |

### SILVER_BULLET (M15)
| Config | Periodo | Trade | PF | Win Rate | Max DD | Net PnL |
|---|---|---|---|---|---|---|
| Config attuale (killzone ET DST-aware F-02, sweep cascata + FVG, BE+trailing) | | | | | | |

### Osservazioni (Batch 3)
_(da compilare — con queste due si raggiungono le 10 strategie del
portafoglio portate su Pine Script; una volta compilati questi risultati e
quelli del Batch 2, il quadro "10 strategie con edge reale testato" richiesto
sarà completo su un terzo motore/dataset indipendente da MT5 e dal sito.)_
