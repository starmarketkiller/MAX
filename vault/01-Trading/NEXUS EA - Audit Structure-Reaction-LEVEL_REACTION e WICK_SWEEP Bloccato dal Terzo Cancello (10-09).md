# Audit Structure Engine / Reaction Engine / LEVEL_REACTION + WICK_SWEEP_REVERSAL bloccato dal "terzo cancello silenzioso"

Richiesto dall'utente il 10/09 dopo il baseline pulito ADX_RSI RAW ESL OFF (22 trade, PF1.67, 22/22 exit authority corrette). Scopo: capire l'architettura di Structure Engine / Reaction Engine / LEVEL_REACTION PRIMA di continuare a evolvere WICK_SWEEP_REVERSAL, e spiegare perché il Fast Smoke corretto (fix multi-TF one-shot) continua a produrre zero trade.

Vedi anche [[NEXUS EA - Terzo Cancello Silenzioso Trovato su 7 Strategie, Audit Proattivo (05-09)]] — lo stesso meccanismo colpisce ora anche WICK_SWEEP_REV.

## 1. Structure Engine (`NXS_Structure.mqh`, 298 righe)

Stato: `g_struct` (TF di ingresso, letto da ~30 call site) e `g_structH1` (contesto H1 indipendente, v2.0.34) sono istanze separate della stessa struct `SNXSStructure`. Un pool di livelli condiviso `g_levels[]`/`g_levelCount` (max 40, con compattazione FIFO-like quando pieno) alimentato SOLO dall'entry-TF (non da H1).

| Funzione | TF sorgente | Lookback | High strutturale | Low strutturale | Wick vs body | Swing/pivot rule | BOS | CHOCH | Nascita livello | Persistenza | Invalidation | Multi-touch | Storico o solo stato corrente |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `NXS_ComputeStructureCore` (righe 200-251) | TF passato (entry-TF per `g_struct`, sempre H1 per `g_structH1`) | scan=60 barre, wing=`InpSwingWing`=3 | `iHigh` frattale (`NXS_IsSwingHigh`, wick-based, NON body) | `iLow` frattale (`NXS_IsSwingLow`, wick-based) | **Wick puro** (usa `iHigh`/`iLow` grezzi, mai open/close) | Frattale simmetrico: wing barre a sx E dx devono essere piu' basse (per un high) — nessuna tolleranza, nessun ATR | Break di `lastSwingHigh`/`Low` che **conferma/estende** il trend precedente (v2.0.34: reso mutuamente esclusivo con CHOCH, prima i due potevano scattare insieme sullo stesso break — bug corretto) | Stesso break ma che **contraddice** il trend precedente | Al primo frattale confermato trovato scandendo indietro (solo per `g_struct`, `addLevels=true`; MAI per `g_structH1`) | Nessun campo di scadenza esplicito sul livello swing stesso — resta nel pool finché non mitigato 2 volte o il pool si riempie (drop FIFO) | Nessuna invalidation dedicata per gli swing (diversa da OB/FVG, vedi sotto) | `mitigations` conta i tocchi, ma solo per OB/FVG/swing generici via `NXS_MitigateLevels` | **Solo stato corrente per il trend/BOS/CHOCH** (`st.trend/bosUp/...` sovrascritti ogni call); **`g_levels[]` invece conserva fino a 40 livelli storici** (swing+OB+FVG misti, non solo l'ultimo) |
| `NXS_DetectOrderBlocks` (100-120) | TF passato | 30 barre (i=3..30, quindi esclude le 3 più recenti) | — | — | Body (`MathMax/Min(open,close)` della candela pre-displacement) | Bearish/bullish candle seguita da displacement ≥ `g_atr*InpOBDisplacement` (1.5×ATR) sulla barra successiva | n/a | n/a | Alla scansione, se il displacement supera la soglia | Come sopra (pool condiviso) | Mitigazione generica | Come sopra | Storico (fino a 40, condiviso con swing/FVG) |
| `NXS_DetectFVG` (122-143) | TF passato | 30 barre | — | — | Body per il filtro minimo (`body >= g_atr*InpFVGMinBody`=0.5×ATR sulla candela di mezzo), ma il gap stesso è wick-to-wick (`iHigh`/`iLow` delle candele esterne) | Gap classico 3-candele (low candela successiva > high candela precedente, o viceversa) | n/a | n/a | Alla scansione | Come sopra | Mitigazione generica | Come sopra | Storico (pool condiviso) |
| `NXS_MitigateLevels` (160-181) | — (usa BID corrente) | — | — | — | Zone (OB/FVG): tocco se prezzo dentro `[priceBot,priceTop]`; Swing: tocco se `|price-priceRef| <= 5 point` | — | — | — | — | **Un livello si disattiva (`active=false`) al SECONDO tocco/mitigazione**, non al primo — il primo tocco lo marca solo `mitigated=true` | Sì, `mitigations` incrementa a ogni tocco successivo, prima disattivazione al 2° | — |
| `NXS_UpdateTrendline` (145-158) | — | — | — | — | — | Estrapolazione lineare tra gli ultimi due swing (solo direzionale, usata come filtro extra altrove) | — | — | — | — | — | — | Solo stato corrente |

**Punti chiave per il confronto con WICK_SWEEP:**
- Gli swing highs/lows sono **wick-based**, esattamente come i livelli di WICK_SWEEP_REVERSAL — stessa natura del dato grezzo (`iHigh`/`iLow`), ma un rigore diverso: lo Structure Engine richiede una conferma frattale simmetrica (wing=3 barre a sinistra E a destra), mentre WICK_SWEEP registra il wick della barra H4 appena chiusa senza nessuna richiesta di isolamento laterale (qualunque wick ≥15 pip diventa livello, anche in mezzo a una sequenza di wick simili).
- Uno swing NON ha invalidation/scadenza esplicita nel tempo — resta valido finché non esce dal pool per compattazione. WICK_SWEEP invece **sostituisce** il livello attivo dello stesso lato a OGNI nuova barra H4 con un wick valido, anche se il precedente non è mai stato sweeppato (nessuna persistenza multi-barra, per design dichiarato nei commenti del file sperimentale).
- Il pool `g_levels[]` è storico (fino a 40 elementi, misto swing/OB/FVG); WICK_SWEEP mantiene invece **un solo livello per lato** (nessuno storico) — differenza architetturale enorme ai fini di un futuro "Level dataset".

## 2. Reaction Engine (`NXS_Reaction.mqh`, 177 righe)

`g_reaction` (struct `SNXSReaction`: `detected, direction, levelPrice, levelType, quality, summary`) è popolato **solo** da `NXS_DetectReaction(sym, tf)`, chiamata dal loop principale una volta per barra (e una volta per ogni passaggio multi-TF, vedi §7).

Meccanica esatta:
1. Scansiona `g_levels[]` per zone attive (OB/FVG) entro tolleranza `InpReactionTol`×ATR (0.3×ATR) dal prezzo BID corrente.
2. Per ogni zona in range, richiede `NXS_HasPriceReaction()` sulla candela appena chiusa: pin bar (wick opposto > 1.5× body E > 50% del range) OPPURE chiusura direzionale coerente — **questo è un vero gate booleano**, non un modificatore: senza reazione di prezzo la zona viene scartata (`continue`), non solo penalizzata.
3. Se passa, quality = 60 base +20 se la direzione è allineata al trend (`g_struct.trend`) +15 se la zona non è mai stata mitigata prima. Tiene il MIGLIOR candidato (`bestQuality`) tra tutte le zone/swing/EMA.
4. Stessa logica ripetuta per gli ultimi swing high/low (quality base 55 +20 trend) e poi per EMA200 come "livello dinamico" opzionale (quality base 58, o solo bonus di confluenza se già rilevato altrove).

**Verifica esplicita richiesta dall'utente — gate o modificatore?** Risposta: **dipende da CHI consuma `g_reaction`, non è univoco**:
- `NXS_ReactionScoreMod(dir)` (usato in `NXS_EntryScore.mqh:57`, score generale) è **puro modificatore**: +`quality*0.4` se allineato, −20 se opposto, 0 se non rilevato. Non blocca nulla da solo.
- `NXS_SMCReactionOK(tf, dir)` (usato da `NXS_Strat_OrderBlock`/OB_MIT su gate `InpUseSMCReactionGate`, righe 1500/2079 di `NXS_Strategies.mqh`) è invece **un vero gate booleano a due condizioni**: (a) `NXS_HasPriceReaction` sulla candela d'ingresso E (b) se `g_reaction.detected`, la sua direzione non deve contraddire il trade. Qui l'assenza/contraddizione della reazione **blocca** l'entrata (return false), non la penalizza soltanto.
- `NXS_Strat_StructureReaction` (STRUCT_REACT, #16, vedi §3) usa `g_reaction.detected` come **gate assoluto e unico** (`if(!g_reaction.detected) return s;` — riga 2090): senza reazione rilevata, zero segnale, indipendentemente da qualunque altro punteggio.

Quindi: per STRUCT_REACT è un gate puro; per le strategie SMC (OB/OB_MIT) è un gate a doppia condizione; per lo score generale delle altre strategie è solo un modificatore additivo. Non esiste un'unica risposta valida per "tutto il motore".

BOS/CHOCH e trend NON entrano nel calcolo di `g_reaction.detected` — entrano solo come bonus di qualità dentro STRUCT_REACT (righe 2099-2100, +5 punti ciascuno) e come bonus dentro `NXS_DetectReaction` stesso (+20 se direzione = trend). Non sono mai un gate per la reazione in sé.

## 3. LEVEL_REACTION (#52 M15) / LEVEL_REACTION_M5 (#53) — `_nxs_levelreact_core`, `NXS_Strategies.mqh:1179-1342`

Nato il 06/09 come merge dichiarato di PIVOT_WICK + STRUCT_REACT + MALAYSIAN_SNR. Due fonti di livello **indipendenti**, entrambe wick o body a seconda della fonte:

- **Fonte 1 — pivot frattali wick-based** su H1/H4/D1 (pool condiviso `g_pivotWickState`, `NXS_PIVOTWICK_MAXLVL` livelli per TF, lookback `InpPivotWickLookback`=5). Stesso frattale simmetrico dello Structure Engine ma calcolato e mantenuto a parte (pool proprio, non `g_levels[]`).
- **Fonte 2 — S/R a corpo H4** stile Malaysian SNR: massimo/minimo delle **chiusure** (non wick) delle ultime 12 barre H4 (`iHighest/iLowest(..., MODE_CLOSE, 12, 1)`). Attivabile/disattivabile con `InpLevelReactUseSNRLevels` (default true).
- Bonus di confluenza opzionale (non gate salvo `InpLevelReactRequireConfluence=false` di default) se il livello coincide (tolleranza doppia/tripla) con un'altra fonte pivot, con l'SNR, o con una zona SMC attiva (`g_reaction`).

**Da dove vengono le statistiche 99.5% / 78.9% / 69.1%**: dal commento in codice (righe 1109-1123), da un'analisi Python separata "rifatta da zero il 06/09 su 7402 pivot dell'intera storia GOLD M15 (2019-2026, zigzag K=3×ATR14, stesso script del 'Gold Reversal Map')" — **non da un test di questa strategia**, ma da uno studio statistico esterno sui pivot storici usato per giustificare le soglie `InpLevelReactMaxBreachPips`=100 (gate duro, sopra scarta) e `InpLevelReactDeepBreachPips`=50 (sotto: 2 barre conferma; sopra: +2 barre extra). **Come richiesto esplicitamente dall'utente: queste percentuali NON sono state riverificate in questa sessione con un test/dataset diretto di LEVEL_REACTION — sono un input storico documentato ma non un edge validato qui.** Andrebbero ricontrollate contro il dataset di livelli proposto al §5 prima di trattarle come vere.

**Meccanica di entrata — NON immediata**: quando un breach/touch valido appare a fine barra, si apre uno stato "pendente" (`pendingDir/pendingLevel/pendingBars/pendingReqBars`). Il trade scatta SOLO quando il prezzo resta valido (chiusura entro tolleranza del livello) per `pendingReqBars` barre consecutive (base 2, +2 se lo sfondamento è "profondo" ≥50 pip) — quindi è **entry a conferma ritardata**, l'opposto della logica "entra subito al sweep" di WICK_SWEEP_REVERSAL. Se il prezzo esce dalla validità prima di raggiungere le barre richieste, il candidato viene scartato (`pendingDir=0`) senza mai generare un segnale.

SL/TP: via `NXS_DefaultSLTP`, con profilo per-strategia `slMult=1.5, tpMult=3.0` × ATR(M15,14) (RR fisso 1:2), niente BE/trail dedicato (`beR=0, trailATR=0`).

Invalidation/re-entry: un solo candidato pendente per volta per istanza (M15 e M5 hanno stati separati, `g_levelReactState`/`g_levelReactState5`); niente cooldown esplicito dopo un trade — appena `pendingDir` torna 0 (fired o invalidato) la ricerca riparte dalla barra successiva. Nessun limite di re-trigger sullo stesso identico livello prezzo (a differenza del one-shot per-livello di WICK_SWEEP).

### Baseline STRUCT_REACT (#16) — `NXS_Strat_StructureReaction`, righe 2087-2108

Serve da riferimento "puro" per la tabella comparativa: **gate assoluto e unico** = `g_reaction.detected` (nessuna logica propria oltre a leggere `g_reaction`). Direzione = `g_reaction.direction`. Score = 55 + quality×0.35 (+6 se trend allineato, +5 se BOS/CHOCH coerente). SL/TP: profilo dedicato `slMult=2.0, tpMult=6.0` (RR 1:3), TF forzato a H4, **direction-lock a SOLO BUY** (`NXS_Profile_DirectionLock`="STRUCT_REACT"→1, righe 534-543 di `NXS_StrategyProfiles.mqh`) perché la ricetta simmetrica H1 era in perdita (PF0.61) mentre H4 BUY-only sale a PF2.32-2.43 — **asimmetria nota e voluta**, non un bug, ma un limite architetturale da tenere presente nel confronto (STRUCT_REACT non è testabile come strategia simmetrica nella sua ricetta live).

## 4. Tabella comparativa

| | STRUCT_REACT (#16) | LEVEL_REACTION (#52/#53) | WICK_SWEEP_REVERSAL (#54, prototipo) |
|---|---|---|---|
| **Livello sorgente** | Zone SMC (OB/FVG da `g_levels[]`) + swing + EMA200, tutte lette da `g_reaction` | Pivot frattali wick H1/H4/D1 (fonte 1) + S/R a corpo H4 ultime 12 chiusure (fonte 2) | Wick della singola candela H4 appena chiusa (solo se ≥15 pip) |
| **TF** | Forzato H4 (via profilo) | M15 (#52) o M5 (#53) per l'esecuzione; livelli letti da H1/H4/D1 | H4 hardcoded, indipendente da `InpProfileMultiTF` |
| **Creazione livello** | Ereditata da Structure/Reaction Engine (scansione 60 barre + OB/FVG 30 barre) | Scansione pivot frattale (lookback 5) + rolling 12-barre H4 per l'SNR, ricalcolata ogni barra | Ad ogni nuova barra H4, se il wick della barra appena chiusa ≥ soglia |
| **Persistenza** | Fino a 2 mitigazioni (pool condiviso, storico fino a 40) | Pool pivot proprio, non scade esplicitamente | **Nessuna**: sostituito dalla barra H4 successiva se produce un nuovo wick valido, anche se non ancora sweeppato |
| **Sweep richiesto** | No — basta un touch/pin/chiusura direzionale in zona | Sì, ma anche un semplice "touch" senza sfondamento è ammesso (touchMode OR sweepMode) | Sì, obbligatorio: serve superare il livello di `InpWickSweep_SweepPips`=35 pip |
| **Timing di entrata** | Immediato alla rilevazione (stessa barra) | **Ritardato**: richiede N barre di conferma (2, +2 se sfondamento profondo) dopo il touch/sweep | **Immediato "di pancia"**, al tick, appena il prezzo tocca la soglia di sweep |
| **Conferma** | Pin bar o chiusura direzionale (`NXS_HasPriceReaction`) | Persistenza di N barre entro tolleranza dal livello | Nessuna — solo la condizione di prezzo istantanea |
| **SL** | 2.0×ATR(H4) | 1.5×ATR(M15) | Fisso 25 pip ($2.50/lotto std) |
| **TP** | 6.0×ATR(H4) (RR 1:3) | 3.0×ATR(M15) (RR 1:2) | Fisso 100 pip (RR 1:4 nominale) |
| **Invalidation** | Nessuna oltre al gate iniziale | Il candidato pendente si annulla se il prezzo esce dalla tolleranza prima delle N barre | Nessuna — il livello vive finché non sweeppato o sostituito dalla barra successiva |
| **Re-entry** | Nessun blocco esplicito, ma dipende da `g_reaction` che si ricalcola ogni barra | Un solo pendente alla volta per istanza, nessun cooldown post-trade | **One-shot per livello** (flag `highSwept`/`lowSwept`), ma un nuovo livello sullo stesso lato può riformarsi alla barra successiva |
| **Frequenza attesa** | Bassa-media (dipende da zone SMC attive + reazione di prezzo) | Media (due fonti indipendenti + soglie permissive di touch) | **Alta** — 165 eventi di sweep in ~80 giorni H4 nel Fast Smoke corrente (~2/giorno), molto più frequente dell'ipotesi iniziale "pattern raro" |
| **Debolezza maggiore** | Direction-lock BUY-only nella ricetta live (asimmetria strutturale, non simmetrico come richiesto dal protocollo di test) | Percentuali di reversal (99.5/78.9/69.1%) provenienti da uno studio esterno sui pivot, **mai riverificate su questa strategia specifica** | Nessuna persistenza/storico del livello, nessuna conferma prima di entrare, nessun filtro di qualità sul wick oltre alla dimensione minima — il tasso di segnale molto alto (165 in 80gg) suggerisce che la soglia attuale cattura moltissimo "rumore" di volatilità gold, non necessariamente eventi di liquidity grab selettivi |

## 5. Proposta dataset Level Engine (design, non implementato)

Per ogni livello H4 registrabile (qualunque fonte: wick WICK_SWEEP, pivot frattale, OB/FVG), un record con:

`level_price, wick_high, wick_low, wick_size_pips, candle_body_pips, atr_h4_at_creation, creation_time, age_at_retest_bars, touch_count, penetration_depth_pips, max_penetration_pips, mfe_after_touch_pips, mae_after_touch_pips, reclaim (bool), structural_break (bool), time_to_reaction_bars`

Binning per profondità di penetrazione (1 pip = $0.10 su GOLD, come da convenzione confermata): **0-10, 10-20, 20-30, 30-40, 40-50, 50-75, 75-100, 100+**.

Esplicitamente: la soglia attuale di 35 pip per WICK_SWEEP **non va assunta come ottimale** — è il primo prototipo. Il dataset qui sopra permetterebbe di rispondere empiricamente a "quale bin di penetrazione riconquista di più il livello ed entro quante barre", esattamente come già fatto per i pivot M15 generici (le percentuali 99.5/78.9/69.1 del §3) ma **specificamente sui livelli a wick H4**, cosa che oggi non esiste per nessuna delle tre strategie in tabella.

## 6. Risultato Fast Smoke WICK_SWEEP_REV corretto (10/09, Terminal3) — solo dati descrittivi

Test: GOLD H4, 2026.06.01→2026.08.26, RAW puro (`InpResearchExitMode=0`, tutti gli opt-in ESL/DPT/TotalDD/Ruin OFF), lotto fisso 0.02, selettore 54, parametri bloccati (soglia 35 pip, SL 25, TP 100, wick-min 15).

Il fix del bug multi-TF (guardia `g_activeTF`) **ha funzionato**: la strategia ora genera segnali reali sul passaggio H4 corretto — **165 eventi di sweep** rilevati tra il 2026.06.01 e il 2026.08.19 (test quasi completo all'ultimo controllo).

**MA: zero trade aperti, di nuovo.** Causa, identificata riga per riga nel log del tester:

```
[NEXUS CONTRACT] OPEN BLOCCATO: strategy_id sconosciuto 'WICK_SWEEP_REV'
```

Tutti e 165 gli eventi vengono bloccati da `NXS_StrategyKnown()` (`NXS_StrategyRegistry.mqh:16`), chiamata come primissimo controllo dentro `NXS_OpenTrade()` (`NXS_Execution.mqh:284`), **prima** di qualunque altro gate (profile, risk, SL/TP). È lo stesso identico meccanismo già documentato il 05/09 per altre 7 strategie (vedi [[NEXUS EA - Terzo Cancello Silenzioso Trovato su 7 Strategie, Audit Proattivo (05-09)]] — "il terzo cancello silenzioso") e già visto in passato per PIVOT_WICK. `NXS_StrategyRegistry.mqh` è un file **generato** (`contracts/generate_registry.py`, "Do not edit") a partire da `knowledge/strategy_database.json` + `NXS_StrategyProfiles.mqh` + `server/backtest.py`: WICK_SWEEP_REV non è mai stato aggiunto a nessuna di quelle fonti, quindi non esiste nel registro generato, quindi ogni tentativo di apertura viene rifiutato in modo silenzioso (nessun errore visibile fuori dal log).

**Non ho toccato questo file né rigenerato il registro** — è un cambiamento più ampio della semplice strategia (tocca file "fonte di verità" condivisi con tutte le altre 49 strategie live) e va oltre il perimetro "non ottimizzare/non aggiungere filtri" che hai fissato per questa fase. Ti serve una decisione esplicita: se vuoi che WICK_SWEEP_REV superi il Fast Smoke con dati reali, va registrato in `knowledge/strategy_database.json` (o in un percorso equivalente per strategie sperimentali) e il registro va rigenerato — un'operazione meccanica e a basso rischio (stesso trattamento già dato a PIVOT_WICK in passato), ma è un cambiamento di codice condiviso che preferisco far approvare prima di eseguirlo.

Dati descrittivi disponibili (senza alcun giudizio di edge, come richiesto):
- **165 tentativi di sweep** in ~80 giorni di storico H4 (~2/giorno) — frequenza molto più alta dell'ipotesi "pattern raro" di partenza.
- **0 trade aperti**, 0 SL, 0 TP, 0 duplicati osservabili (nessun trade esiste).
- **165 livelli "consumati" senza trade** (ogni sweep marca `highSwept`/`lowSwept=true` e viene scartato dal gate, quindi il livello è bruciato comunque anche se il trade non parte — un effetto collaterale del bug: il one-shot si consuma anche su un'apertura fallita).
- Split BUY/SELL, durata, RR realizzato: non disponibili — il log del tester non registra la direzione del segnale bloccato (limite dell'attuale istrumentazione, coerente con quanto emerso nella proposta dataset del §5).
- Nessun `[RESEARCH][INVARIANT_FAIL]` — atteso, dato che nessun trade ha mai raggiunto l'apertura (l'invariante RAW si applica solo alle chiusure di posizioni reali).

## 7. Bug architetturali trovati in questo giro

1. **Multi-TF one-shot consumption bug** (già corretto in questa sessione, confermato funzionante dal log: i 165 eventi ora avvengono sul passaggio H4 corretto) — vedi nota precedente per il dettaglio del fix (`g_activeTF` guard in `NXS_Strategies_Experimental.mqh`).
2. **Terzo cancello silenzioso (`NXS_StrategyKnown`/`NXS_Contract`) — NON corretto, in attesa di decisione**: stessa classe di bug già documentata il 05/09 per 7 strategie, ora confermata anche su WICK_SWEEP_REV. È probabilmente il vero motivo per cui QUALUNQUE strategia sperimentale nuova (aggiunta solo in `NXS_Inputs.mqh`/`NXS_Strategies_Experimental.mqh` senza toccare il registro generato) risulterà sempre a zero trade nel Fast Smoke, indipendentemente da quanto sia corretta la sua logica di segnale — vale la pena controllarlo per PRIMA per ogni futura strategia sperimentale, prima ancora di lanciare il primo test.
3. **Effetto collaterale del bug #2 sul one-shot di WICK_SWEEP**: il flag `highSwept`/`lowSwept` si marca `true` anche quando l'apertura fallisce per cancello sconosciuto — quindi anche dopo il fix del registro, il PRIMO run continuerà a "bruciare" livelli su aperture che sarebbero fallite comunque per altri motivi (risk gate, cooldown, ecc.), non solo per trade effettivamente aperti. Da tenere presente quando si interpreta il prossimo run: il numero di "livelli consumati senza trade" non sarà mai zero per costruzione, va scomposto per causa di fallimento (serve loggare `g_nxsLastOpenFailure` per differenziare).
