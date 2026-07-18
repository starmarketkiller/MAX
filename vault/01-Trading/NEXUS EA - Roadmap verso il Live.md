#nexus #trading #roadmap #live #moc

# NEXUS EA — Roadmap verso il Live

Documento vivo, da aggiornare ad ogni sessione. Scopo: sapere sempre "dove siamo" e "qual è il prossimo passo concreto", senza perdersi nell'implementazione infinita. 7 fasi in sequenza — non si salta una fase per andare alla successiva, ognuna è un gate reale, non burocrazia.

**Non c'è una data.** Dipende da quanto si stabilizza lo sweep MT5 e da quanto lavoro di design richiedono le strategie ancora da ridisegnare. Questo documento serve a rendere visibile la sequenza, non a promettere un calendario.

---

## ⚠️ Scoperta 17/07 notte (tardi): tutti i test finora girati con leva sbagliata

L'utente userà **1:500** in reale, ma il Tester girava con **1:100 su €1000** — un conto sottodimensionato per XAUUSD a leva bassa. Verificato nel codice: esiste un gate reale (`InpUseMarginGate`/`InpMinMarginLevelPct`, `NXS_Execution.mqh`) che calcola il margine richiesto (`OrderCalcMargin`, dipende dalla leva) e blocca l'apertura se il margin level proiettato scende sotto soglia — a differenza delle altre protezioni, **questo NON viene bypassato nel Tester**. Con XAUUSD a leva 1:100 su €1000 il margine per lotto è enorme rispetto all'equity → il gate blocca quasi tutto. Spiega "i test non partivano". Non è un bug di codice (la leva è già letta dinamicamente dal conto, non hardcoded) — era una configurazione del Tester diversa dal conto reale target. Corretto lato NEXUS Bot.

**Implicazione**: tutti i dati raccolti finora (incluso lo sweep di stanotte) vanno considerati sospetti fino a conferma col nuovo sweep a 1:500 — secondo motivo indipendente (oltre al gate posizione mancante, Fase 0) per cui la Fase 3 va rifatta da zero. Aggiunto come voce esplicita qui sotto.

---

## Fase 0 — Integrità di esecuzione (Level B) — 🟡 quasi completa

L'EA deve eseguire fedelmente quello che decide, prima di chiedersi se le decisioni sono buone.

- [x] Gate "1 posizione per strategia" in DataCollectionMode (17/07 sera) — bug dominante, causava mass-flatten continui via ESL
- [x] Unificati i due sistemi indipendenti di durata massima posizione (bug del 24/06, chiuso il 17/07)
- [x] Tabella cap 12h corretta e resa coerente per TF di origine
- [x] `NEXUS_trades.csv` non più infinito — reset opt-in aggiunto (17/07 notte)
- [x] Identity check anti-corruzione fra passate Tester consecutive (NEXUS Bot, 17/07)
- [ ] **Uno sweep 1-37 completo, pulito, senza timeout, CON LEVA 1:500 (non 1:100)** — in corso ora (NEXUS Bot, timeout portato a 6h + leva corretta dopo la scoperta del margin-choke)
- [x] Audit "altri bug dello stesso tipo?" — famiglia `NXS_StratFamily` completa, `_nxs_regime_veto` incompleto ma disattivato di default (safe)

**Prossimo passo concreto**: aspettare l'esito dello sweep in corso. Se completa senza timeout, Fase 0 è chiusa.

---

## Fase 1 — Coerenza logica (Level A) — 🟡 in corso, buona parte fatta

Ogni strategia deve fare davvero quello che il suo nome promette, prima di misurarne la redditività.

- [x] 7 strategie auditate (sessione precedente): SAR, BJORGUM, MACD, RSI_DIV, BREAKOUT_ACC, LIQ_SWEEP, ADX_RSI
- [x] 4 strategie zero-trade auditate: WEEKLY_EXP, LIQ_VOID, IFVG, RANGE_FADE
- [x] Audit esterno canonico completo (fonti ICT/SMC) per altre 10 strategie, con specifiche di fix precise
- [x] Fix implementato: **LIQ_VOID** — geometria FVG corretta (era high-vs-high, ora vera relazione a 3 candele)
- [x] Fix implementato: **IFVG/FVG_MIT/OB_MIT** — consolidati sul motore NXR come unica fonte (eliminata l'ambiguità fra due implementazioni concorrenti), corretto anche il conflation OB_MIT/breaker
- [x] **WEEKLY_EXP** — completata come "Modello B" (già la più vicina): ATR H4 dedicato (era D1, il bug dominante) + BOS aggiunto (17/07 notte)
- [ ] **NY_REVERSAL** — sessione di Londra da ricostruire con timezone/DST reali (non offset GMT fisso)
- [x] **SH_BMS_RTO** — trasformata in macchina a stati sweep→MSS→origine→ritorno→entry (17/07 notte)
- [ ] **RANGE_FADE** — qualificazione del range da rendere persistente su N barre (non solo l'ultima lettura ADX)
- [ ] **OTE_CONT** — ancorare Fibonacci e struttura di conferma allo stesso leg/BOS
- [ ] **ELLIOTT** — decisione presa (rinominare `FIVE_SWING_IMPULSE`, dichiarata pattern proprietario), esecuzione rimandata a sweep concluso (tocca il nome in molti file, rischio di interferire col matching identità di NEXUS Bot)
- [x] Audit di coerenza completato anche per le 20 strategie residue (il conteggio reale, non 27) — agente logico, 17/07 notte
- [x] Verificato che l'attribuzione condivisa `s.strat = STRAT_STRUCT_REACT` (11 strategie) NON è un bug reale — stats/profili/router usano tutti `stratName` (stringa, distinto), il campo condiviso serve solo a un valore cosmetico di dashboard
- [x] **TSI** — implementato il vero True Strength Index di Blau (era RSI+EMA20 col nome sbagliato) — 17/07 notte
- [x] **ORDER_BLOCK** — corretto: origine = ultima candela opposta prima dell'impulso + BOS richiesto + zona persistente (17/07 notte)
- [x] **SILVER_BULLET** — macchina a stati sweep→displacement/BOS→FVG→retest (17/07 notte; scadenza a barre, non timezone reale — vedi NY_REVERSAL)
- [x] **CISD** — rinominata `THREE_BAR_DELIVERY_BREAK` (17/07 notte; non riscritta, un tentativo precedente di versione "vera" non scattava mai — 0/1067)
- [x] **DISP_REBAL** — CE corretto sul vero FVG a 3 candele, non più il 50% dell'intera candela displacement (17/07 notte) — **chiude tutti e 5 i mismatch critici del secondo audit**
- [x] **LONDON_BO** — validazione breakout aggiunta (corpo minimo, buffer, close location value) (17/07 notte)
- [x] **EMA_PULLBACK** — trend persistente + impulso precedente + vera rejection, non più un cross istantaneo (17/07 notte)
- [x] **refHigh/refLow** — completato con weekly/monthly (bug collegato al fix LIQ_SWEEP di stanotte, beneficia LDN_REVERSAL/TURTLE_SOUP/PO3/AMD_REVERSAL) (17/07 notte)
- [x] **AMD_CONT** — non mescola più close barra1 e bid live (17/07 notte)
- [x] **TURTLE_SOUP** — verificato: nessun bug reale, causalità sweep/rejection già garantita strutturalmente, dedup già coperto dal gate posizione-per-strategia (17/07 notte)
- [x] **LDN_REVERSAL** — beneficia automaticamente dal fix refHigh/refLow sopra (17/07 notte)
- [ ] **JUDAS_SWING** — rischio minore rimanente: CHOCH è stato corrente senza timestamp, non garantisce causalità con lo sweep di questa barra specifica (richiede timestamp su NXS_Structure, rimandato)
- [ ] **AMD_REVERSAL**, **PO3** — richiedono vera memoria di fase giornaliera (redesign, non patch)
- [x] **BOLLINGER** — allineamento shift1/shift2 corretto (17/07 notte)
- [x] **BB_SQUEEZE** — squeeze percentile-relativo alla propria storia, non più soglia assoluta (17/07 notte)
- [x] **ICHIMOKU** — stesso allineamento shift1/shift2 corretto (17/07 notte)
- [x] **MALAYSIAN_SNR** — ATR H4 corretto, tocco su barra chiusa (non bid live), W1 da codice morto a vero bonus di confluence (17/07 notte)

**Secondo audit (20 strategie residue) interamente coperto.** Prossimo passo concreto: WEEKLY_EXP/NY_REVERSAL/RANGE_FADE/OTE_CONT (redesign più corposi, dal primo audit canonico), JUDAS_SWING/AMD_REVERSAL/PO3 (rimandate, serve memoria di fase/timestamp), infine il rename ELLIOTT a sweep concluso.

---

## Fase 2 — Verifica indipendente multi-motore — 🟡 iniziata

Tre motori diversi (MT5, sito Python, TradingView) devono raccontare storie coerenti prima di fidarsi di uno solo.

- [x] Pine Script per 4 strategie (SAR/MACD/ADX_RSI/RSI_DIV), confronto incrociato con motore sito — MACD confermato su 2 motori, SAR ambiguo/discorde, RSI_DIV in disaccordo forte (probabile regime-dipendenza)
- [ ] Estendere ad altre strategie a gruppi di 4, partendo da quelle già coerenti a Livello A (non le 5 ancora da ridisegnare — inutile ottimizzare l'ingresso di un trigger rotto)
- [ ] Cross-check con dati MT5 reali quando lo sweep sarà completo

**Prossimo passo concreto**: dopo Fase 0, riprendere Dispatch/TradingView sul prossimo gruppo di 4 strategie già coerenti.

---

## Fase 3 — Stabilità statistica (Level C) — 🔴 da rifare da zero

**Perché "da zero" e non "da dove eravamo"**: tutte le conclusioni statistiche raccolte finora (10Y segmentato, screening, hedge nel tempo) sono state raccolte MENTRE l'esecuzione era rotta (gate mancante, Fase 0). Vanno considerate inaffidabili finché non rifatte su dati puliti.

- [ ] Ribacktest 10 anni segmentato con tutti i fix di Fase 0+1 applicati
- [ ] PF/DD/numero trade stabili su ogni segmento annuale, non solo in media
- [ ] Walk-forward: parametri scelti su una finestra, validati su una finestra successiva mai vista in fase di scelta
- [ ] Hedge/correlazione fra strategie ri-misurato sui dati puliti (la nota "Hedge nel Tempo" esistente va rifatta)

**Prossimo passo concreto**: non iniziare finché Fase 0 e almeno le strategie critiche di Fase 1 non sono chiuse — altrimenti si rifà il lavoro due volte.

---

## Fase 4 — Il nodo del rischio in Tester — 🔴 identificato, non risolto (deliberatamente)

Il gate di protezione conto (DD giornaliero, margine, trade/giorno, anti-revenge) è **disattivato di default nel Tester** (`MQL_TESTER` bypass) — tutti i PF/DD misurati finora NON includono l'effetto di queste protezioni, che invece saranno attive in demo/live.

Deciso esplicitamente di NON "aggiustare" questo come se fosse un fix delle strategie — sarebbe un camuffamento, non cura le cause di perdita (principio già stabilito: "non è una vera soluzione alle strategie").

- [ ] Prima del live, capire concretamente cosa cambia CON le protezioni attive — almeno un test dedicato, non necessariamente riattivarle in pianta stabile nel Tester

**Prossimo passo concreto**: pianificare questo test dopo Fase 3, quando i numeri di baseline sono affidabili e si può misurare la differenza.

---

## Fase 5 — Realismo di esecuzione — 🔴 da fare

- [ ] Spread/slippage/commissioni reali del broker che userai in demo/live, non i default a zero di backtest/Pine/sito
- [ ] Verifica che il modello di esecuzione (istantaneo vs market vs apertura barra) sia comparabile fra i 3 motori usati finora

---

## Fase 6 — Demo / forward test — 🔴 non iniziata (gate finale prima del capitale reale)

- [ ] Account demo, stesso broker/spread previsto per il live
- [ ] EA in esecuzione per un periodo minimo continuativo (indicativamente 4-8 settimane) senza interventi manuali sulla logica
- [ ] Nessuna sorpresa strutturale rispetto al backtest (disconnessioni, requotes, gap di weekend, comportamento reale dei fix di Fase 0)

**Solo dopo un demo pulito si passa a capitale reale — e comunque con size ridotta all'inizio, non a piena scala.**

---

## Fase 7 — Operatività live — 🔴 non iniziata

- [ ] Monitoraggio/alert che avvisa se l'EA si blocca o si comporta in modo anomalo (non scoprirlo dopo giorni)
- [ ] Piano di kill-switch manuale, testato almeno una volta
- [ ] Position sizing finale calibrato sul capitale reale disponibile
- [ ] Capitale iniziale ridotto, scaling graduale solo dopo risultati coerenti col demo

---

## Legenda stato

🟢 completa · 🟡 in corso · 🔴 non iniziata

## Log aggiornamenti di questo documento

- **17/07 notte** — creazione. Stato fotografato: Fase 0 quasi chiusa (sweep in corso), Fase 1 al ~40% (2 fix su 7 rimanenti + audit completo), Fase 2 iniziata su 4/37 strategie, Fasi 3-7 non ancora iniziate.
