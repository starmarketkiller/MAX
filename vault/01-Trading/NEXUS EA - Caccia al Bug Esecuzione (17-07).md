---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, bug, esecuzione, mt5, sar, macd, rsi-div, adx-rsi]
created: 2026-07-17
updated: 2026-07-17
---

# Caccia al bug di esecuzione + ricerca esterna (17/07)

Richiesta dell'utente: consiglia qualcosa per rendere profittevoli
SAR/MACD/RSI_DIV/ADX_RSI, cerca online come altri usano questi
indicatori, cerca bug/errori/logiche sbagliate nel codice. Durante questo
lavoro sono arrivati i primi 4 risultati REALI di MT5 (sweep isolato
1-37, `results/reports/sweep37/pre-fix-16-07/`) — dati pre-fix (compilati
prima dei fix di oggi) ma preziosissimi: la PRIMA volta che vediamo dati
di esecuzione MT5 reali per queste strategie isolate, non aggregate.

## 🚨 AGGIORNAMENTO 17/07 (notte, 11): refHigh/refLow completato + AMD_CONT + verifica TURTLE_SOUP/JUDAS_SWING

Continuando sul gruppo "plausibili ma incomplete", ho trovato un problema collegato al mio stesso fix di LIQ_SWEEP di stanotte, prima di procedere sugli altri.

**Fix reale — `sw.refHigh/refLow` (`NXS_MarketAnalysis.mqh`, `NXS_DetectSweepExt`)**: quando ho esteso LIQ_SWEEP a weekly/monthly stanotte, ho aggiunto i flag `sweptPWH/sweptPWL/sweptPMH/sweptPML` ma **non li avevo inclusi nella formula di `refHigh/refLow`** — che restava solo daily/Asia/equal. Effetto: consumer come LDN_REVERSAL, TURTLE_SOUP, PO3, AMD_REVERSAL che condizionano l'entry su un livello weekly/monthly swept, ma poi usano `sw.refHigh/refLow` per calcolare SL, prendevano il livello sbagliato (il fallback generico, non quello che aveva davvero scatenato il segnale) — esattamente il tipo di incoerenza segnalata dall'audit per LDN_REVERSAL ("sw.refHigh/refLow deve essere il livello coerente con quello usato nella condizione"). Corretto: stessa precedenza già usata per `s.dir/s.level` (monthly > weekly > daily > Asia > equal).

**Fix reale — AMD_CONT** (`NXS_Strat_AMD_Continuation`, `NXS_Strategies_Institutional.mqh`): mescolava `close` di barra 1 (breakout) con `bid` live (retest) — due punti temporali diversi nella stessa condizione, lo stesso pattern già corretto altrove stanotte (RANGE_FADE). Ora tutto sulla barra chiusa 1: `low[1]` tocca la fascia di retest, `close[1]` conferma oltre il bordo — niente prezzo live.

**Verificato, nessun cambio necessario — TURTLE_SOUP**: l'audit segnalava di dimostrare che sweep e rejection appartengano alla stessa barra. Controllato: `sw` (il segnale di sweep) e la rejection candle in questa funzione leggono ENTRAMBI shift=1 dello stesso `NXS_EffTF()` — sono già strutturalmente la stessa barra, non serve nuovo codice. Il "level_id per evitare segnali multipli" è già coperto dal gate globale "1 posizione per strategia" (`NXS_StrategyHasOpenPos`) che impedisce l'apertura ripetuta finché la posizione precedente è ancora aperta.

**Non ancora affrontato**: JUDAS_SWING (rischio reale ma minore — `g_struct.chochUp/Down` è uno stato corrente, non un evento con timestamp, quindi non garantisce che il CHOCH sia avvenuto DOPO lo sweep specifico di questa barra; fix richiederebbe tracciare un timestamp sul CHOCH, cambiamento più ampio a `NXS_Structure`, rimandato), AMD_REVERSAL e PO3 (richiedono vera memoria di fase giornaliera, redesign più corposo, non una patch).

Non ancora validato su MT5 reale.

---

## 🚨 AGGIORNAMENTO 17/07 (notte, 10): LONDON_BO + EMA_PULLBACK — prime 2 delle 8 "plausibili ma incomplete"

Iniziato il gruppo delle 8 strategie che l'audit giudica concettualmente plausibili ma senza una vera validazione/persistenza — qui il fix è irrobustire, non riscrivere da zero.

**LONDON_BO** (`NXS_Strategies.mqh`): prima qualsiasi chiusura anche marginale oltre l'Asian range contava come breakout. Aggiunta validazione vera: corpo minimo (`InpLondonBO_MinBodyATR`, 0.5×ATR), buffer oltre il livello (`InpLondonBO_BufferATR`, 0.15×ATR, non un tocco marginale), close location value minimo (`InpLondonBO_MinCLV`, 0.6 — la chiusura deve essere vicina all'estremo della barra, non nel mezzo). Timezone/DST della sessione restano un lavoro a parte, condiviso con NY_REVERSAL (non duplicato qui).

**EMA_PULLBACK** (`NXS_Strategies.mqh`): prima era un cross istantaneo di EMA20 nel tick corrente — non dimostrava trend persistente né un vero impulso precedente né una rejection reale, solo un incrocio. Ora richiede: trend persistente per `InpEMAPB_TrendPersistBars` (5) barre (non solo l'istante attuale), un impulso precedente che si sia allontanato dall'EMA20 di almeno `InpEMAPB_MinDistATR` (1.0×ATR) nelle ultime 12 barre, un vero pullback con rejection (tocco EMA20 + chiusura sopra con candela direzionale, non solo un cross), e blocco dell'entry se il prezzo rompe anche l'EMA50 (trend strutturalmente rotto).

Non ancora validato su MT5 reale. Restano dal gruppo "plausibili ma incomplete": TURTLE_SOUP, AMD_REVERSAL, AMD_CONT, JUDAS_SWING, LDN_REVERSAL, PO3.

---

## 🚨 AGGIORNAMENTO 17/07 (notte, 9): DISP_REBAL — CE corretto, chiude tutti e 5 i mismatch critici

Ultimo dei 5 mismatch critici del secondo audit. `NXS_Strat_DisplacementRebalance` usava il 50% dell'**intera candela** di displacement come "CE" (Consequent Encroachment) — non è il rebalance di un'inefficienza, è solo un retracement al 50% della candela impulso.

**Fix**: stessa geometria FVG a 3 candele già corretta per LIQ_VOID e riusata per SILVER_BULLET stanotte (bullish: `Low(candela3) > High(candela1)`). Il CE ora è il punto medio del vero FVG lasciato dal displacement, non della candela intera. Mantenuta la struttura "ricalcolo fresco ogni tick" (come LIQ_VOID dopo il fix di stanotte, non uno state machine completo — questa categoria di bug era "geometria sbagliata", non "sequenza causale collassata" come SH_BMS_RTO/SILVER_BULLET).

**Tutti e 5 i mismatch critici del secondo audit sono ora coperti**: TSI (vero calcolo Blau), ORDER_BLOCK (origine corretta + BOS), SILVER_BULLET (macchina a stati), CISD→THREE_BAR_DELIVERY_BREAK (rinominata), DISP_REBAL (CE corretto).

Non ancora validato su MT5 reale (macchina spenta stanotte). Restano dal secondo audit: 8 strategie "plausibili ma incomplete" (causalità sweep→displacement→MSS→retracement→entry da imporre) e 4 di allineamento indicatori/timeframe. Restano dal primo audit canonico: WEEKLY_EXP, NY_REVERSAL, RANGE_FADE, OTE_CONT (redesign più corposi) + rename ELLIOTT (a sweep concluso).

---

## 🚨 AGGIORNAMENTO 17/07 (notte, 8): CISD rinominata THREE_BAR_DELIVERY_BREAK

Quarto dei 4 mismatch critici — questa volta **rinominata, non riscritta**. `NXS_Strat_CISD` implementa "3 barre chiuse dello stesso segno, poi rottura del loro estremo" — un pattern di rottura reale e funzionante, ma non è il vero Change in State of Delivery (che l'audit descrive come rottura del **livello/open** che sosteneva la sequenza di candele opposte, non dell'high/low estremo).

**Perché rename e non riscrittura**, a differenza di TSI/ORDER_BLOCK/SILVER_BULLET: il commento già presente nel codice (v2.3.3) documenta che un tentativo precedente di versione "vera" (displacement+delivery+sweep+reclaim) **non scattava mai — 0 setup su 1067**. Riscriverla di nuovo verso una definizione più stretta rischiava concretamente di silenziarla un'altra volta, e senza MT5 disponibile stanotte (macchina spenta) non potevo verificare subito se una nuova versione avrebbe prodotto segnali. Scelta più sicura: tenere la logica che funziona, dichiarare onestamente cosa fa.

**Rinominata ovunque nel codice** (stratName, profili SL/TP, stats, router, family list) — solo il nome `InpUseStrat_CISD` (il toggle input) resta invariato apposta, per non rompere i `.set` di NEXUS Bot già esistenti che lo referenziano.

Non ancora validato su MT5 reale. **4 dei 5 mismatch critici di questo audit sono ora coperti** (TSI, ORDER_BLOCK, SILVER_BULLET, THREE_BAR_DELIVERY_BREAK/CISD) — resta **DISP_REBAL** come ultimo, prossimo in coda.

---

## 🚨 AGGIORNAMENTO 17/07 (notte, 7): SILVER_BULLET riscritta come macchina a stati

Terzo dei 4 mismatch critici. `NXS_Strat_SilverBullet` (`NXS_Strategies_SMC.mqh`) era solo "sweep dentro una finestra oraria" — mancavano displacement, creazione dell'FVG e ritorno successivo nella zona, gli elementi centrali del modello Silver Bullet secondo l'audit.

**Riscritta con la stessa architettura a stati di SH_BMS_RTO** (stato per lato BUY/SELL): `IDLE → SWEPT → WAITING_RETURN → entry`.
- `IDLE→SWEPT`: sweep confermato **dentro la killzone** (10-11 o 14-15 GMT, invariate).
- `SWEPT→WAITING_RETURN`: displacement con BOS (stesso schema swing-lookback di ORDER_BLOCK/SH_BMS_RTO) **e** FVG a 3 candele generato dal displacement, con la geometria corretta già usata per LIQ_VOID stanotte (bullish: `Low(candela3) > High(candela1)`).
- `WAITING_RETURN→entry`: primo tocco della zona FVG (prezzo live), entro `InpSB_MaxBars` (15) barre dal sweep.
- Invalidazione: chiusura oltre il livello sweepato nel verso sbagliato, o timeout.

**Limite noto, non risolto qui**: la scadenza della sequenza è a conteggio barre (`InpSB_MaxBars`), non un calcolo preciso del termine sessione in timezone reale — quel lavoro (DST-aware) resta in coda separatamente per NY_REVERSAL, dove verrà fatto una volta sola e centralizzato invece di duplicarlo qui.

Non ancora validato su MT5 reale. Restano: CISD, DISP_REBAL (ultimi 2 mismatch critici) + le 8 "plausibili ma incomplete" + le 4 di allineamento indicatori.

---

## 🚨 AGGIORNAMENTO 17/07 (notte, 6): ORDER_BLOCK — origine della zona corretta

Secondo dei 4 mismatch critici dall'audit delle 20 residue. `NXS_Strat_OrderBlock` (`NXS_Strategies.mqh`) usava la candela di **displacement stessa** come order block — in ICT/SMC un OB bullish è invece l'**ultima candela bearish prima del displacement** che rompe struttura. Era più una "displacement body zone" che un vero OB.

**Fix**: stato persistente per lato (BUY/SELL, come ORDER_BLOCK/SH_BMS_RTO stanotte):
- Displacement cercato fra 3-10 barre fa (come prima), ma ora deve anche **rompere uno swing precedente (BOS)** — prima non veniva verificato per niente.
- Zona OB = **ultima candela di colore opposto prima dell'impulso** (scan fino a 6 barre indietro), non più il corpo dell'impulso.
- Zona persistente e "fresh" fino al primo retest o invalidazione (prima si ricalcolava tutto da zero ogni tick, nessuna nozione di zona già consumata) — one-shot dopo il primo retest, scade dopo `InpOB_MaxWaitBars` (20) barre di attesa.
- Mantenuti invariati: conferma trend H1 esterno e reaction gate SMC che seguivano già la detection.

Nota collaterale: `NXS_Strat_OB_Mitigation_Structural` (la vecchia OB_MIT legacy) chiamava questa funzione — ma dal consolidamento NXR di stanotte non è più raggiunta da nessun percorso attivo (NXR è l'unica fonte per OB_MIT), quindi nessun rischio di doppio conteggio.

Non ancora validato su MT5 reale. Restano: SILVER_BULLET, CISD, DISP_REBAL (mismatch critici) + le 8 "plausibili ma incomplete" + le 4 di allineamento indicatori.

---

## 🚨 AGGIORNAMENTO 17/07 (notte, 5): audit delle 20 strategie residue + TSI reale implementato

Arrivato il secondo audit esterno dell'agente logico, questa volta sulle 20 strategie non coperte da nessun audit precedente (il conteggio reale residuo era 20, non 27 come stimato prima). Qualità alta come i precedenti.

**Verifica fatta prima di tutto**: l'audit segnala che molte strategie istituzionali (TURTLE_SOUP, SMS_BMS_RTO, SILVER_BULLET, AMD_REVERSAL, MALAYSIAN_SNR, CISD, AMD_CONT, JUDAS_SWING, LDN_REVERSAL, PO3, DISP_REBAL) condividono `s.strat = STRAT_STRUCT_REACT`, chiedendo di verificare che non condividano anche stats/profili/attribuzione. **Verificato: falso allarme sul meccanismo specifico temuto.** Tutto ciò che conta per Livello A/B/C (stats, profili SL/TP, router, gate posizione-per-strategia) usa `stratName` (stringa), confermato distinto per ognuna (es. `s.stratName = "CISD"`, `"TURTLE_SOUP"` ecc., righe diverse in file diversi). Il campo `.strat` (l'enum condiviso) viene usato in un solo punto, `NXS_VisualBridge.mqh`, solo per un valore cosmetico di dashboard (`active_strat`) — non incide su nessuna logica di trading, stats o attribuzione. Giusto controllarlo, ma non era un bug.

**Risultati principali dell'audit** (20 strategie):
- **5 mismatch critici** (il nome non corrisponde al codice): TSI (non calcolava il vero TSI), ORDER_BLOCK (usa la candela displacement stessa come OB, non l'ultima candela opposta prima dell'impulso), SILVER_BULLET (solo sweep in finestra oraria, manca displacement→FVG→retest), CISD (proxy "3 candele stesso colore + rottura", non il vero Change in State of Delivery), DISP_REBAL (50% dell'intera candela displacement, non il Consequent Encroachment di un vero FVG)
- **8 plausibili ma incomplete** (manca la relazione temporale causale sweep→displacement→MSS→retracement→entry): LONDON_BO, EMA_PULLBACK, TURTLE_SOUP, AMD_REVERSAL, AMD_CONT, JUDAS_SWING, LDN_REVERSAL, PO3
- **4 con problemi di allineamento indicatori/timeframe**: BOLLINGER (verificare Close[2] vs banda della barra 2, non barra 1), BB_SQUEEZE (soglia assoluta debole, dovrebbe essere percentile relativo alla storia), ICHIMOKU (rischio shift temporale Senkou Span), MALAYSIAN_SNR (W1 calcolato ma mai usato, mix ATR fra timeframe)

**Fix implementato**: **TSI reale** (`NXS_Strat_TSI`, `NXS_Strategies.mqh`). La versione precedente era RSI+EMA20 col nome sbagliato — zero relazione col vero True Strength Index di Blau. Ora calcola il vero TSI: doppio EMA (long=25, short=13) del price change, diviso per il doppio EMA dell'abs(price change) x100, confrontato con una signal line (EMA a 7 periodi del TSI) — entry sul cross TSI/signal. Calcolo iterativo, aggiornato una sola volta per barra chiusa (stesso bar-gating di SH_BMS_RTO stanotte), con warmup di `LongPeriod×3` barre prima di generare segnali (il doppio smoothing parte da zero, non dalla media storica reale, serve tempo per convergere).

Non ancora validato su MT5 reale. Restano da fare: ORDER_BLOCK, SILVER_BULLET, CISD, DISP_REBAL (i 4 mismatch critici rimanenti) + le 8 "plausibili ma incomplete" + le 4 di allineamento indicatori — più i 4 redesign già in coda dall'audit canonico precedente (WEEKLY_EXP, NY_REVERSAL, RANGE_FADE, OTE_CONT).

---

## 🚨 AGGIORNAMENTO 17/07 (notte, 4): SH_BMS_RTO riscritta come vera macchina a stati

Primo dei 5 redesign più corposi dall'audit canonico (priorità più alta secondo l'audit fra le macchine a stati). `NXS_Strat_SH_BMS_RTO` (`NXS_Strategies_SMC.mqh`) prima richiedeva sweep + CHOCH + FVG (barre 4/2) + prezzo già dentro la zona **tutto sullo stesso tick** — collassava una sequenza che nella realtà è causale (sweep → displacement/MSS entro qualche barra → un ritorno SUCCESSIVO alla zona d'origine), senza dimostrare che gli eventi fossero davvero collegati.

**Riscritta con una vera sequenza a stati**, per lato (BUY/SELL, stato separato):
```
IDLE → SWEPT → (entro InpSHBMS_MaxMSSBars barre, MSS confermato + origine registrata) → WAITING_RETURN → primo ritorno nella zona = entry
```
- `IDLE→SWEPT`: sweep confermato (`sw.confirmed && sw.dir`), registra livello sweepato e uno swing di riferimento (15 barre precedenti) che l'MSS dovrà rompere.
- `SWEPT→WAITING_RETURN`: entro `InpSHBMS_MaxMSSBars` (20) barre, una chiusura rompe lo swing di riferimento con un corpo displacement ≥ `InpSHBMS_DispBodyATR` (0.8×ATR) → MSS confermato. Origine = ultima candela di colore opposto prima del displacement (scan fino a 6 barre indietro).
- `WAITING_RETURN→entry`: primo tocco della zona d'origine (prezzo live, come già fa LIQ_VOID) entro `InpSHBMS_MaxWaitBars` (15) barre dall'MSS. One-shot: lo stato si resetta subito dopo l'entry.
- Invalidazione a ogni stadio: chiusura oltre il livello sweepato nel verso sbagliato, o timeout.
- Vincolo causale `sweepTime < mssTime < retestTime` garantito per costruzione (si avanza di stato solo su una barra chiusa successiva, mai sullo stesso tick).

Nessuna modifica alla firma della funzione (`NXS_Strat_SH_BMS_RTO(SNXSSweepExt &sw)`), nessun cambiamento al chiamante in `NEXUS_EA_v2.mq5`. Non ancora validato su MT5 reale.

**Prossimi redesign in coda**: WEEKLY_EXP, NY_REVERSAL, RANGE_FADE, OTE_CONT.

---

## 🚨 AGGIORNAMENTO 17/07 (notte, 3): primi 2 fix dall'audit esterno canonico (LIQ_VOID + consolidamento NXR)

Arrivato l'audit esterno/canonico dell'agente logico (`NEXUS_EA_Audit_Canonico_Concetti_e_Specifiche_Fix.md`, continuazione dell'audit Livello A) — confronto fra definizione ICT/SMC reale e codice per 10 strategie, con specifiche di fix precise. Qualità alta, fonti citate, nessuna invenzione riscontrata nei punti verificati.

**Scoperta collaterale importante durante la verifica**: per IFVG/FVG_MIT/OB_MIT (+ MALAYSIAN_SNR/STRUCT_REACT, non segnalate come problematiche) esiste già un secondo motore più sofisticato su zone persistenti (`NXS_ReusePerformancePack.mqh`, "NXR pack") — ma **non sostituiva quello vecchio, lo affiancava**: ogni tick calcolava ENTRAMBI i segnali (quello "stretto" già segnalato come non fedele da due audit indipendenti, e quello nuovo su zone persistenti) e teneva quello con score più alto. Trovato anche un bug in più nella parte NXR: OB_MIT mescolava "mitigation" e "breaker" nello stesso segnale — la stessa confusione concettuale che l'audit dice di evitare.

**Fix implementati (2 dei 10, i meno rischiosi):**

1. **LIQ_VOID** (`NXS_Strategies_Institutional.mqh`, `NXS_Strat_LiquidityVoid`): geometria FVG corretta — prima confrontava `high(displacement)` con `high(displacement+2)` (due high, non un vero gap). Ora usa la vera relazione a 3 candele (fonti ICT/SMC): bullish `Low(candela3) > High(candela1)`, zona fra `High[candela1]`-`Low[candela3]`; bearish speculare.
2. **Consolidamento su NXR come unica fonte** (`NXS_ReusePerformancePack.mqh`): `NXR_Strat_IFVG_Reversal`, `NXR_Strat_FVG_Mitigation`, `NXR_Strat_OB_Mitigation` non chiamano più la funzione legacy "base" come concorrente per score — se NXR non ha un trigger valido, il segnale è vuoto (niente fallback sulla logica stretta). Corretto anche il conflation OB_MIT/breaker: OB_MIT ora prende solo il primo retest di un OB ancora valido, i trigger BREAKER non producono più un segnale OB_MIT (nessuna strategia dedicata al breaker esiste ancora — lavoro futuro separato).

**Non ancora fatto (rimandato, non dimenticato)**: WEEKLY_EXP (macchina a stati, due modelli alternativi proposti dall'audit), NY_REVERSAL (aggregazione sessione Londra con timezone/DST reali), SH_BMS_RTO (macchina a stati sweep→MSS→origin→return), RANGE_FADE (qualificazione persistente del range su N barre), OTE_CONT (ancoraggio Fibonacci allo stesso leg/BOS) — tutti richiedono più lavoro di design, non semplici patch.

**ELLIOTT — decisione presa ma NON eseguita ora**: l'audit raccomanda scartarla o rinominarla `FIVE_SWING_IMPULSE` (dichiarata pattern geometrico proprietario, non vero conteggio Elliott onesto). Deciso di rinominare (meno distruttivo, preserva lo storico raccolto) — ma **rimandato all'esecuzione**: un rename tocca il nome della strategia in molti file (profili, stats, router, chain, learner CSV) e lo sweep 1-37 di NEXUS Bot sta girando proprio ora con un matching per-nome appena rinforzato contro corruzioni (vedi incidente S01/LIQ_SWEEP di stanotte) — rinominare ELLIOTT a metà sweep rischierebbe di rompere proprio quel meccanismo. Da fare a sweep concluso.

Non ancora validato su MT5 reale (nessuno dei due fix di stanotte).

---

## 🚨 AGGIORNAMENTO 17/07 (notte, 2): LIQ_SWEEP esteso a weekly/monthly, un solo motore invece di 3 cloni

Richiesta dell'utente: i sweep importanti avvengono anche su livelli weekly e monthly, non solo daily — voleva capire se il codice riconosce quando viene "preso" il massimo/minimo del giorno, della settimana, del mese. Verificato: **daily (PDH/PDL) era già implementato** (`NXS_DetectSweepExt`, usato da `LIQ_SWEEP` e riusato da NY_REVERSAL/LDN_REVERSAL/altri), **weekly/monthly non esistevano affatto** (zero riferimenti a `PERIOD_MN1` in tutto il progetto; `WEEKLY_EXP` esiste ma è un concetto diverso — premium/discount + displacement, non un vero sweep di PWH/PWL, ed è anche il candidato "quasi bloccato" dell'audit Livello A di stanotte).

**Decisione presa con l'utente**: niente 3 strategie clonate (avrebbe replicato l'antipattern OB_MIT appena segnalato dall'audit — wrapper mascherati da strategie indipendenti). Un solo motore di rilevamento, esteso a daily+weekly+monthly, con un **tag esplicito di quale livello ha scatenato lo sweep** per diagnostica — non profili SL/TP separati per livello (l'utente ha dato via libera a procedere senza differenziazione).

**Fix implementato** (commit da pushare):
- `SNXSSweepExt` (`NXS_MarketAnalysis.mqh`) esteso con `sweptPWH/sweptPWL/sweptPMH/sweptPML` + nuovo campo `string levelTag`.
- `NXS_DetectSweepExt()` esteso: stesso pattern "stoppino oltre il livello + chiusura dentro" già usato per PDH/PDL, applicato anche a `PERIOD_W1` e `PERIOD_MN1` (shift 1, periodo precedente). Ordine di precedenza intenzionale — Asia → daily → weekly → monthly → equal H/L (fallback) — così se più livelli scattano sulla stessa barra vince quello di scala più grande/più raro, il più significativo come evento di liquidità.
- `NXS_Strat_LiqSweep()` (`NXS_Strategies.mqh`): il `reason` del segnale ora include `sw.levelTag` (es. `Sweep_low_reversal:Weekly-Low`), visibile nel CSV — diagnostica per capire quale livello produce l'edge, senza duplicare la strategia.
- **Effetto collaterale consapevole**: `SNXSSweepExt` è condiviso da altre strategie (TurtleSoup, SH_BMS_RTO, SilverBullet, CISD, JudasSwing, LondonReversal, NY_REVERSAL, PO3, AMD_Reversal) che leggono `sw.dir`/`sw.level`/`sw.refHigh`/`sw.refLow` o i singoli flag booleani — ora possono reagire anche a sweep weekly/monthly, non solo daily/Asia. Estensione naturale (più livelli di liquidità riconosciuti a livello di sistema), non una regressione, ma da tenere presente leggendo i risultati del prossimo sweep.
- **Fix di sicurezza collaterale**: rimosso `ZeroMemory(s)` dalla costruzione di `SNXSSweepExt` — non è sicuro su uno struct con un campo `string` (comportamento non definito in MQL5, l'handle stringa non viene rilasciato correttamente). I campi sono già puliti di default alla dichiarazione.

Non ancora validato su MT5 reale.

---

## 🚨 AGGIORNAMENTO 17/07 (notte): sospetto CSV infinito dietro i timeout Tester + reset opt-in

Lo sweep 1-37 (arrivato a S30/37) ha iniziato a dare timeout ripetuti nello script di automazione di NEXUS Bot, con perdita di tempo significativa segnalata dall'utente. `NEXUS_trades.csv` non viene MAI svuotato (`NXS_LogTradeCSV`, `NXS_Logging.mqh` — apre sempre in `FILE_WRITE|FILE_READ` + `FileSeek(SEEK_END)`, mai un reset) — accumula da ogni sweep dall'inizio del progetto, gia' a 24.8MB+ nello snapshot analizzato ieri sera. Sospetto (non ancora confermato con timing esatti da NEXUS Bot): passate successive dello sweep rallentano perche' MT5 deve aprire/scrivere in coda a un file sempre piu' grande, fino a superare il timeout impostato nello script.

**Decisione presa con l'utente**: niente pulizia automatica ad ogni passata (romperebbe la possibilita' di confrontare passate consecutive durante un'analisi in corso). Invece, reset **esplicito e opt-in**, da attivare solo quando i dati fin li' raccolti sono stati letti e le decisioni prese — "puliamo quando abbiamo visto i dati e deciso come procedere".

**Fix implementato** (`3cba036`... nuovo commit da pushare):
- Nuovo input `InpResetTradesLogOnInit` (default `false`, `NXS_Inputs.mqh`) — se attivato per UNA run, `NXS_ResetTradesLogIfRequested()` (`NXS_Logging.mqh`, chiamata a inizio `OnInit()`) archivia il file corrente rinominandolo con timestamp (`NEXUS_trades_archive_<data>.csv`), MAI lo cancella. La scrittura successiva lo ricrea vuoto con header.
- Se il rename fallisce (es. file occupato), l'EA non si blocca: continua ad accumulare sul file esistente e stampa un warning.

**Da fare per chiudere il sospetto**: chiedere a NEXUS Bot (a) il testo esatto dell'errore di timeout e se viene dallo script PowerShell o da MT5, (b) il valore di timeout impostato, (c) la dimensione attuale del file sul disco locale — per confermare se il CSV e' davvero la causa o solo un sospetto plausibile non provato.

---

## 🚨 AGGIORNAMENTO 17/07 (sera): trovata la VERA causa dominante — mancava il gate "1 posizione per strategia" in DataCollectionMode

Il fix del cap a 12h (sotto) era reale e corretto — verificato che `resolved_tf`
nel CSV risolve giusto (es. `PERIOD_H4` per BJORGUM) — ma **il primo sweep
post-fix (S01-S06) ha mostrato holding time identici a prima**. Recuperato
`NEXUS_trades.csv` reale (24.8MB, `results/reports/sweep37/trades_snapshots/`)
per capire perché, invece di continuare a ipotizzare da codice statico.

**Trovato**: il path `NXS_CheckProtections`/best-per-bar standard ha un gate
`NXS_StrategyHasOpenPos()` — "1 posizione per strategia alla volta"
(`NEXUS_EA_v2.mq5:821`). **`InpDataCollectionMode` non ce l'aveva per
niente.** Le funzioni segnale sono quasi tutte a STATO persistente (es.
`macd>signal>0`), non a evento singolo — restano vere per molte barre di
fila. Senza il gate, DataCollectionMode riapriva una NUOVA posizione a
OGNI tick finché il segnale restava valido: **MALAYSIAN_SNR_NXR risultava
aperta 17.218 volte** nel file controllato, contro le poche centinaia
attese in anni di dati.

Con centinaia/migliaia di posizioni della stessa strategia accumulate,
correlate sullo stesso simbolo, la loro **equity flottante combinata**
faceva scattare ripetutamente `NXS_Prot_CheckESL()` (Equity Stop Loss,
`InpESL_Value=5%` del saldo) — che chiude TUTTE le posizioni aperte in un
colpo solo. Confermato sui dati: **97.8% di tutte le chiusure** (68.242 su
69.788) avvengono in "cluster" di più posizioni chiuse entro 15 secondi
l'una dall'altra — non chiusure indipendenti per singola posizione.
Guardando il campo `reason` sulle righe già nel formato nuovo (con
strategia/motivo compilati): **`expert` (chiusura forzata) 2163, `sl`
1812, `tp` = 1 su quasi 4000** — praticamente nessuna posizione arriva mai
al take-profit, non perché il trigger sia sbagliato, ma perché viene
travolta da un flatten di massa prima di poterlo raggiungere.

**Perché il fix del cap 12h non bastava**: risolveva un problema reale
(scaling del timeout per-strategia) ma completamente in ombra rispetto a
questo — un flatten di massa ogni poche ore/minuti rende irrilevante
qualsiasi cap di durata più generoso, la posizione non arriva mai a
vedere quel limite.

**Fix applicato** (`NEXUS_EA_v2.mq5`, blocco `InpDataCollectionMode`):
aggiunto `if(NXS_StrategyHasOpenPos(s.stratName)) continue;` prima di
aprire ogni segnale — stesso gate già presente nel path standard, mai
esteso qui. Non tocca `InpESL_Value` o altri parametri delle protezioni
(sarebbe un cerotto sul sintomo) — cura la causa: impedisce l'accumulo
di posizioni della stessa strategia che faceva scattare il flatten.

**Non ancora validato su MT5** — prossimo sweep dirà se questo,
combinato col fix del cap 12h, normalizza finalmente `avg_holding_sec` e
la quota di trade che arrivano al vero TP.

## Scoperta 1 (mattina): un'anomalia nei dati reali che nessun fix di oggi spiega

Le 4 passate isolate (ADX_RSI, BOLLINGER, MACD, SAR — GOLD M15,
2019-2025, `InpDataCollectionMode`) mostrano tutte lo stesso pattern
sospetto:

| Strategia | Trade decisi | WR% | PF | avg_R_win | avg_R_loss | avg_holding |
|---|---|---|---|---|---|---|
| ADX_RSI | 625 | 31.0 | 0.58 | **+0.230** | **-0.177** | **6.06h** |
| BOLLINGER | 185 | 42.2 | 0.60 | **+0.160** | **-0.195** | **5.47h** |
| MACD | 176 | 20.5 | 0.13 | **+0.216** | **-0.431** | **3.56h** |
| SAR | 242 | 19.4 | 0.18 | **+0.293** | **-0.383** | **4.67h** |

**Il problema**: con SL=1× e TP=4× ATR (config dell'epoca), un vero TP
dovrebbe chiudere a **+4.0R esatto**, un vero SL a **-1.0R esatto** (R è
calcolato sul rischio ORIGINALE, `NXS_StratStats.mqh::_nxs_stats_dealR`,
formula verificata corretta). Invece **ogni singola strategia** — con TF,
SL/TP e logiche completamente diverse — chiude vinte e perse a una
frazione minuscola di R (0.16-0.29 invece di 4.0, -0.18/-0.43 invece di
-1.0), e **il tempo medio in posizione è sempre 3.5-6 ore**,
indipendentemente dal fatto che ADX_RSI/BOLLINGER siano strategie D1
(dovrebbero durare giorni) e MACD/SAR H4.

**Non è compatibile con "il prezzo tocca SL o TP"** — se lo facesse, R
sarebbe vicino a -1.0/+4.0 quasi sempre. Qualcos'altro chiude le
posizioni molto prima, a un P&L parziale, quasi sempre entro poche ore.

## ✅ CONFERMATO (17/07, non più solo sospetto): tabella TF duplicata e disallineata

Trovata la causa esatta leggendo il codice riga per riga fino in fondo.
Esiste un SECONDO meccanismo di chiusura forzata, indipendente da quello
inizialmente sospettato (`NXS_Management.mqh`, time-exit a 4h — quel
meccanismo in realtà scala correttamente): `NXS_Protections.mqh::
NXS_Prot_CheckMaxHold()`, attivo di default (`InpUseMaxHold=true`,
confermato nel `.set` reale usato per questo sweep) con un cap base
`InpProt_MaxHoldHours=12` (12 ore), scalato per timeframe tramite
`NXS_TF_LifeFactor(NXS_PosSourceTF(commento_posizione))`.

**Il bug**: `NXS_PosSourceTF()` chiama `NXS_StrategySourceTF()` — una
**tabella di mappatura strategia→timeframe completamente diversa e mai
sincronizzata** da quella vera (`NXS_Profile_TF()` in
`NXS_StrategyProfiles.mqh`, usata per il trigger e per il SL/TP). Questa
tabella vecchia copriva **solo 10 strategie su ~30**
(WEEKLY_EXP/PO3/JUDAS_SWING/LDN_REVERSAL/NY_REVERSAL/AMD_CONT/CISD/
LIQ_VOID/SILVER_BULLET/OTE_CONT/ICHIMOKU) — e per 4 di quelle 10
(CISD/LIQ_VOID/OTE_CONT/ICHIMOKU) il valore era anche **sbagliato**
(diceva H1, il profilo vero è H4/H4/H4/D1). **Tutte le altre —
ADX_RSI, SAR, MACD, RSI_DIV, BOLLINGER, TSI, BJORGUM, LIQ_SWEEP,
FVG_CONT, ORDER_BLOCK, TURTLE_SOUP, IFVG, FVG_MIT, OB_MIT, SH_BMS_RTO,
SMS_BMS_RTO, AMD_REVERSAL, MALAYSIAN_SNR, DISP_REBAL, RANGE_FADE,
BREAKOUT_ACC, LONDON_BO, EMA_PULLBACK, BB_SQUEEZE, STRUCT_REACT —
cadevano nel default `InpTFEntry` (M15)**.

Con TF risolto a M15, `NXS_TF_LifeFactor(M15)` ritorna **1.0** (nessuno
scaling, perché M15 ≤ TF base) invece di 20× (H4) o 60× (D1). Risultato:
`NXS_Prot_CheckMaxHold()` applicava un cap **piatto di 12 ore** — non i
30+ giorni previsti per una D1, non i 10 giorni per una H4 — su
praticamente tutte le strategie principali dell'EA, chiudendole forzate
molto prima che SL o TP potessero essere toccati. Coerente al millimetro
con i dati: holding medio 3.5-6h (SL veri che scattano più veloci si
mescolano con chiusure forzate a 12h, abbassando la media), R medio
compresso su entrambi i lati indipendentemente dal multiplo SL/TP reale
di ciascuna strategia — esattamente il pattern trovato.

**`NXS_Prot_CheckMaxLossPerPos()` ha lo stesso identico bug** (stessa
`NXS_PosSourceTF()`, scala `InpProt_MinLifeMin` invece di `MaxHoldHours`)
— probabilmente chiude posizioni in perdita prima del tempo minimo di
vita previsto per le stesse ~25 strategie.

**Fix applicato**: `NXS_StrategySourceTF()` ora chiama `NXS_Profile_TF()`
come prima e unica fonte di verità (stessa mappa già usata per
trigger/SL/TP, garantita in ordine di `#include` prima di
`NXS_Strategies.mqh`), con fallback alla vecchia lista solo per le
session/Elliott senza profilo (`JUDAS_SWING`/`LDN_REVERSAL`/
`NY_REVERSAL`/`AMD_CONT`/`SILVER_BULLET`/`WEEKLY_EXP`/`PO3`). Nessuna
tabella duplicata che può disallinearsi di nuovo. **Non ancora validato
su MT5** — richiede ricompilazione e un nuovo sweep per conferma finale,
ma a differenza delle altre ipotesi di oggi questa è un bug di codice
verificato riga per riga, non solo una correlazione nei dati.

## Bug reale trovato e corretto: log CSV di chiusura sempre vuoto

Durante la caccia, trovato un bug concreto e indipendente: in
`OnTradeTransaction()` (`NEXUS_EA_v2.mq5`), la riga che scrive il log
CSV di ogni chiusura (`NXS_LogTradeCSV("CLOSE", ...)`) veniva chiamata
**PRIMA** che le variabili `strat` (nome strategia) e `reason` (sl/tp/
stop_out/**expert**) fossero calcolate — passava sempre stringhe vuote.
`reason="expert"` è esattamente il segnale di una chiusura FORZATA
dall'EA (`DEAL_REASON_EXPERT`, es. il time-exit sopra) invece che un
vero SL/TP toccato dal prezzo — la distinzione che serve per confermare
o smentire il sospetto sopra. **Spostata la chiamata dopo il calcolo**,
ora il CSV mostra la strategia e il motivo reale di ogni chiusura.

**Utile anche per confermare il fix sopra**: nel prossimo sweep (dopo
ricompilazione di ENTRAMBI i fix), controllare `NEXUS_trades.csv` — la
quota di chiusure con `reason=expert` (chiusura forzata dall'EA, es.
`NXS_Prot_CheckMaxHold`) dovrebbe crollare rispetto a prima, e
l'`avg_holding_sec` per ADX_RSI/SAR/MACD/RSI_DIV dovrebbe salire di
molto (giorni per le D1, non più ore) — la verifica finale che il fix
alla tabella TF ha davvero risolto, non solo che sembra corretto da
codice.

## Audit "il CSV ha tutto quello che serve?" (17/07, su richiesta dell'utente)

Controllati tutti i CSV/log che l'EA produce (`NEXUS_trades.csv` via
`NXS_LogTradeCSV`, `nexus_stats_<sym>_<tf>.csv` via `NXS_Stats_ExportCSV`,
`nexus_shadow_*.csv` per lo Shadow Trading). Il file **stats** (40
colonne per strategia: wins/losses/PF/avg_R/avg_holding/tutti i blocker)
è già ricco — è quello che ha permesso di trovare il bug sopra
guardando solo gli aggregati. Ma il file **per-trade**
(`NEXUS_trades.csv`) aveva 3 buchi concreti, tutti corretti oggi:

1. **Nessuna intestazione** — colonne posizionali, bisognava indovinare
   l'ordine leggendo il codice.
2. **Riga OPEN sempre con `ticket=0` e `lots=0`** — impossibile
   collegare in modo affidabile una riga OPEN alla sua CLOSE (nessuna
   chiave di join). Corretto: cercato il ticket vero appena assegnato
   (stesso commento, appena aperto) invece di scartarlo.
3. **Nessun campo diceva QUALE timeframe risolto veniva usato** per
   scalare durata massima/vita minima di quella posizione. Se questo
   campo (`resolved_tf`, aggiunto oggi) fosse già esistito, il bug della
   tabella disallineata si sarebbe visto in **30 secondi** guardando una
   riga del CSV — invece di un'ora passata a rileggere il codice a
   ritroso da un pattern sospetto negli aggregati.

Aggiunte 3 colonne nuove a ogni riga CLOSE: `hold_sec` (durata reale),
`r_multiple` (P&L in multipli del rischio originale, stessa formula
usata per le statistiche), `resolved_tf` (il TF che l'EA ha risolto per
questa strategia — visibile subito se è quello giusto o no). **Da
ricompilare insieme agli altri 2 fix di oggi** prima che serva a
qualcosa sul prossimo sweep.

**Cosa resta fuori, consapevolmente**: lo Shadow Trading
(`nexus_shadow_*.csv`) traccia anche i segnali BLOCCATI con contesto
ricco (blocker, regime, sessione, spread) ma è un sistema parallelo
indipendente, non ancora integrato con l'analisi di oggi — prossimo
candidato se emergono altri misteri legati ai gate piuttosto che
all'esecuzione.

## Ricerca esterna: come i professionisti usano questi indicatori

- **Parabolic SAR + ADX come filtro**: tecnica da manuale (raccomandata
  dallo stesso Wilder, creatore di entrambi gli indicatori). Uno studio
  DailyFX (EUR/USD daily) citato dalla ricerca: aggiungere ADX>25 come
  filtro ha portato il WR dal 47% al 58%, riducendo i segnali del 40% —
  SAR da solo soffre di whipsaw nei mercati laterali perché "è sempre
  acceso" e si inverte anche su rumore minimo. [Combining Parabolic SAR with ADX](https://unofficed.com/courses/entropy/lessons/combining-parabolic-sar-with-adx/) · [Parabolic SAR: The Trailing Stop Indicator for Trend Traders](https://www.tradealgo.com/trading-guides/technical-analysis/parabolic-sar-the-trailing-stop-indicator-for-trend-traders)
- **ADX come filtro universale di forza del trend**: soglia standard
  20-25 (sotto 20 = laterale, sopra 25 = trend forte); i professionisti
  lo usano per decidere SE tradare trend-following, non come segnale a
  sé. Backtest citati mostrano che aggiungere ADX riduce il drawdown
  evitando entrate nei mercati laterali. [ADX Indicator Trading Strategy — Mind Math Money](https://www.mindmathmoney.com/articles/adx-indicator-trading-strategy-the-complete-guide-to-finding-trends-like-a-pro) · [ADX 25+: The One Filter That Kills Bad Trades](https://fxnx.com/en/blog/adx-strategy-efficiency-filter-measure-trend-strength-like)
- **MACD**: la tecnica più citata è il filtro multi-conferma (trend
  HTF + ADX + volume) e il filtro zero-line (solo long sopra zero, solo
  short sotto) — quest'ultimo NEXUS lo applica già. Timeframe più bassi
  producono fino a 3× più falsi segnali di un daily. [MACD Indicator Guide 2025](https://piptrend.com/macd-indicator/) · [Avoiding Whipsaw](https://abovethegreenline.com/whipsaw-trading/)
- **RSI divergence**: il punto più importante — "la divergenza è un
  ALERT, non un segnale d'ingresso". Serve una conferma price-action
  (candela di reversal, rottura di una trendline minore, chiusura sopra/
  sotto una EMA breve) DOPO la divergenza, prima di entrare. Senza
  conferma il WR scende sotto il 40%; con conferma sale al 55-65%. [RSI Divergence Trading Strategy — AlgoAlpha](https://algoalpha.io/blog/rsi-divergence-trading-strategy-how-to-spot-trade-and-avoid-false-signals) · [RSI Divergence Confirmation](https://tradefundrr.com/rsi-divergence-confirmation/)

## Test A/B degli spunti esterni sul motore sito — risultato onesto: non aiutano qui

Implementate e testate le 3 idee più forti (SAR+ADX>25, MACD+ADX>20,
RSI_DIV+conferma price-action via EMA9), sulla config reale di ciascuna
strategia (H4/H1, SL/TP/HTF del profilo):

| Variante | Trade (prima→dopo) | PF (prima→dopo) | DD% (prima→dopo) | Net (prima→dopo) |
|---|---|---|---|---|
| SAR + ADX>25 | 66→37 | 2.01→1.71 | 8.19→**3.94** | 4.233→1.654 |
| MACD + ADX>20 | 77→72 | 1.77→1.50 | 5.85→7.73 | 2.859→1.773 |
| RSI_DIV + conferma EMA9 | 84→11 | 1.34→1.16 | 11.91→**4.90** | 2.275→122 |

**Nessuna delle tre migliora nel complesso** — il DD scende parecchio in
2 casi su 3 (coerente con la letteratura: meno segnali, più selettivi),
ma PF e net peggiorano sempre, e il campione crolla (RSI_DIV+conferma:
84→11 trade, troppo pochi per fidarsi). Per SAR era già stato testato il
15/07 con lo stesso esito ("non aggiungere filtro ADX: testato,
peggiora") — questo lo conferma anche sul TF di produzione vero (H4,
non D1 come il test originale). **Nessuna applicata.**

**Lettura di questo risultato**: tecniche da manuale, validate
esternamente su altri dataset/strumenti, non si trasferiscono
automaticamente a XAUUSD con la logica NEXUS specifica — coerente con
tutto quello che si è visto oggi (un fix valido altrove non è garanzia
qui). Ma soprattutto: se filtri di INGRESSO ben validati non spostano
l'ago, il problema molto probabilmente non è "il trigger si sbaglia
troppo spesso" — è più coerente con l'ipotesi di esecuzione (sezione
sopra) che con un problema di qualità del segnale.

## Conclusione e raccomandazione

1. **Il bug più importante trovato in tutta la sessione**: la tabella
   `NXS_StrategySourceTF()` duplicata/disallineata che faceva collassare
   il cap di durata massima di `NXS_Protections.mqh` a 12 ore piatte
   (invece di 30+ giorni/10 giorni) per circa 25 strategie su ~30 —
   corretta oggi (`NXS_Strategies.mqh`, delega a `NXS_Profile_TF()`).
   Verificato riga per riga, non solo una correlazione. Spiega da solo
   la sotto-performance MT5 di molte più delle 4 strategie analizzate
   oggi — chiunque abbia un profilo D1/H4 non nella vecchia lista di 10
   era colpito.
2. Non applicare i filtri ADX/conferma esterni: testati, non aiutano su
   questi dati.
3. Il lavoro di oggi (TP largo+BE, confirm_bars/loss_cooldown) resta
   valido come miglioramento del SEGNALE — ma finché il bug al punto 1
   non era corretto, quei fix non potevano funzionare su MT5: il trade
   veniva chiuso forzatamente a 12h prima di poter vedere un TP largo o
   un breakeven attivarsi su una strategia D1/H4. Ora che è corretto,
   hanno una possibilità reale di funzionare quando testati.
4. **Prossimo passo**: ricompilare (2 fix in questa sessione: log CSV +
   tabella TF) e ripetere lo sweep isolato — confrontare
   `avg_holding_sec`/`reason=expert`/PF prima-dopo su tutte le 4
   strategie di questo primo lotto, poi le altre 33.

## Conferma round 2 (dati arrivati mentre si scriveva questa nota)

Arrivato un secondo lotto di dati pre-fix (`pre-fix-16-07-round2/`, S01-S05
ADX_RSI/BOLLINGER/MACD/SAR/TSI) — compilati DOPO il fix TP largo+breakeven
di MACD/ADX_RSI ma PRIMA del fix del cap 12h sopra. Conferma diretta e
indipendente della diagnosi: MACD e SAR sono **identici al centesimo** ai
numeri pre-TP/BE-fix (PF0.13/0.18, stesso holding al secondo), ADX_RSI
leggermente peggio. Il fix TP/BE, da solo, non ha spostato nulla su MT5
reale — esattamente perché il cap a 12h tagliava i trade prima che
potessero vedere il TP largo o il breakeven attivarsi. Rafforza molto la
fiducia che il fix del cap fosse la priorità giusta.

## Trovato anche (17/07, durante l'audit "come migliorare l'ecosistema"): le protezioni account-level sono spente in ogni test

`NXS_CheckProtections()` (`NXS_Risk.mqh:69` — DD giornaliero
`InpMaxDailyDDPct`, margine, trade/giorno, posizioni concorrenti,
anti-revenge/anti-bleed) inizia con `if(MQLInfoInteger(MQL_TESTER)) return
true;` — si disattiva da sola in OGNI test nello Strategy Tester, scelta
deliberata v2.0.31 (altrimenti questi gate bloccavano quasi tutte le 37
strategie). Spiega da solo l'87-88% di drawdown già documentato in
[[NEXUS EA - Backtest 10Y Segmentato - Analisi]] — il gate giornaliero
esiste già, semplicemente non gira mai nei test raccolti finora.

**Non trasformato in fix**: proposto di riattivarlo o aggiungere un gate
cumulato, l'utente ha corretto — un gate che taglia le perdite prima
maschera il sintomo (DD alto) senza curare la causa (la strategia perde
comunque). Tenuto solo come contesto per interpretare i DD estremi già
visti, non come priorità. Dettaglio: [[TODO - Backtest 10Y]].

## Audit "altri bug dello stesso tipo?" (17/07)

Cercate altre tabelle strategia→qualcosa duplicate/disallineate come
`NXS_StrategySourceTF()`. Trovate e controllate:
- `NXS_StratFamily()` (`NXS_SignalRouter.mqh`) — copre tutte le 36
  strategie connesse (+ fallback sicuro FAM_OTHER per ELLIOTT), usata per
  i gate MTF/velocity. **Completa, nessun bug trovato.**
- `_nxs_regime_veto()` (`NXS_SignalQuality.mqh`) — lista incompleta
  (~14/36) ma con fallback sicuro (nessun veto se non in lista, non un
  veto sbagliato) e gated dietro `InpInstRegimeVeto` (Institutional Core,
  OFF di default) — non attiva nel percorso standard.
- `NXS_ApplyScoreCap`/`NXS_StrategyMinScoreFloor`/`NXS_StrategyOnCooldown`
  — casi singoli o dinamici, non tabelle duplicate.

Nessun secondo bug critico dello stesso tipo trovato nel percorso
standard attivo di default.

## Fix reale: unificati i due sistemi di durata massima indipendenti

Bug architetturale distinto (non lo stesso della tabella disallineata,
ma imparentato — entrambi nell'area "quanto vive una posizione"):
`NXS_ManageBreakevenAndTrail()` (gestione completa, BE+trailing+time-exit
integrati) e `NXS_Prot_CheckMaxHold()` (gate separato, solo time-exit)
potevano chiudere la STESSA posizione con limiti diversi — es. una D1
calcolava 40 giorni nel primo, 30 giorni nel secondo, vinceva chi
scattava prima, in modo imprevedibile e mai realmente prevedibile da chi
tuning i due `input` separatamente. Segnalato dall'utente il 24/06,
verificato ancora presente il 15/07.

**Corretto** (non un nuovo limite, una correzione di un'incoerenza
reale): `NXS_Prot_CheckMaxHold()` ora salta ogni posizione che ha un
profilo reale (`NXS_Profile_TF(strat) != PERIOD_CURRENT`) — quelle
restano gestite esclusivamente da `NXS_Management.mqh`, che è già
integrato con breakeven/trailing nello stesso loop e quindi l'autorità
più coerente. Il gate delle Protezioni resta attivo solo per le
session/Elliott senza profilo — la sua funzione di rete di sicurezza
originale, non duplicata altrove. Non ancora validato su MT5.

## ⚠️ Scoperta più grande di tutte quelle di oggi: quasi tutto `NXS_Inputs.mqh` non è realmente configurabile

Controllando ogni "input group" del file (la sintassi MQL5 che raggruppa
gli input nel pannello Proprietà) contro le variabili dichiarate davvero
`input` al loro interno: **su ~40 gruppi, la stragrande maggioranza ha
zero o quasi zero variabili realmente `input`** — sono tutte plain
(assegnabili solo nel codice sorgente, MAI da un file `.set`). Contate
circa **370 variabili** su un totale di ~400 che sono "input group" solo
di nome.

Esempi concreti tra i più rilevanti per il lavoro di oggi: l'intero
gruppo **RISK PROTECTIONS** (`InpUseMaxHold`, `InpProt_MaxHoldHours`,
`InpUseESL`, `InpMaxLossPosPct`, `InpAutoCloseMin`...) e l'intero gruppo
**BREAK EVEN & TRAIL** (`InpMaxHoldHours`, `InpBE_TriggerATR`,
`InpTrailActivateATR`, `InpSL_HighVol_Mult`...) — cioè esattamente le due
aree al centro dell'indagine di oggi sul cap di durata massima. Anche
volendo, **non era possibile testare un valore diverso di
`InpProt_MaxHoldHours` o `InpMaxHoldHours` via `.set` file** prima di
questo fix — ogni riga `.set` per queste variabili era già silenziosamente
inerte, MT5 la ignora senza avvisare.

**Corretto oggi (27 variabili, i due gruppi più rilevanti)**: RISK
PROTECTIONS (14) e BREAK EVEN & TRAIL (13) resi `input` veri. Verificato
prima che nessuna delle 27 venga mai riassegnata a runtime nel codice
(sicuro renderle `input` — altrimenti la compilazione si romperebbe,
un `input` è di sola lettura dopo `OnInit`).

**Non corretto (deliberatamente, per ora)**: restano circa 340 altre
variabili non-`input` in altri ~35 gruppi (SIZING AGGRESSIVO, SCUDO
RISK-OF-RUIN, HTF BIAS, VELOCITY GATE, NEWS FILTER, GATE MODE,
INDICATORS, STRUCTURE ENGINE, MARKET CONTEXT LAYER, MTF/SPREAD/VOL
REGIME, e molti altri). Non toccate in blocco perché: (1) alcune
potrebbero essere pensate per restare interne per design (es. tuning
fine che non ha senso esporre), (2) 400 input tutti insieme renderebbero
il pannello Proprietà ingestibile, (3) senza poter compilare io stesso,
convertirne 340 in un colpo solo senza verifica è un rischio inutile
quando i due gruppi più urgenti sono già risolti. **Prossimo passo
naturale**: se emerge il bisogno di testare un'altra area specifica via
`.set` (come è successo oggi con Risk Protections), convertire quel
gruppo mirato, verificando ogni volta l'assenza di riassegnazioni prima.

## Collegamenti
[[MOC - Trading]] · [[Sar]] · [[Macd]] · [[Rsi Div]] · [[Adx Rsi]] · [[NEXUS EA - Gestione Uscita MFE-MAE (17-07)]] · [[NEXUS EA - Backtest 10Y Segmentato - Analisi]] · [[NEXUS EA - Ricerca Esterna e Test A-B per Strategia]] · [[TODO - Backtest 10Y]]
