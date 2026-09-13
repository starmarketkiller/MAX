# Unified Structure / Level / Reaction Engine — Audit operativo + Migration Plan v1

Richiesto dall'utente dopo la chiusura di Quantitative Integrity v1/v2, Web Bridge v1 e Backend Test Debt. Torna alla roadmap principale NEXUS: Market Structure Core / Level Engine / Reaction Engine.

**Perimetro di questa nota**: SOLO audit tecnico + piano implementativo. Nessuna riga di codice MQL5 modificata. Nessuna strategia toccata. Nessun SL/TP, execution, TF cambiato. I 10 file richiesti sono stati letti per intero o analizzati per pattern mirati (i 3 file `NXS_Strategies*` sono grandi: analizzati via grep + lettura di contesto sui match, non riga per riga).

File analizzati: `NXS_Structure.mqh`, `NXS_StructureMultiLayer.mqh`, `NXS_Reaction.mqh`, `NXS_BjorgumZones.mqh`, `NXS_FibonacciContext.mqh`, `NXS_InstitutionalCore.mqh`, `NXS_Strategies.mqh`, `NXS_Strategies_SMC.mqh`, `NXS_Strategies_Institutional.mqh`, `NXS_Strategies_Experimental.mqh`.

Vedi anche gli audit precedenti già nel vault, riusati come evidenza in questa nota: [[NEXUS EA - Audit Structure-Reaction-LEVEL_REACTION e WICK_SWEEP Bloccato dal Terzo Cancello (10-09)]], [[NEXUS EA - STRUCT_LEVEL_SWEEP, Audit Structure Engine e Design Nuovo Filone (10-09)]], [[NEXUS EA - LEVEL_REACTION, Merge Vero di PIVOT_WICK STRUCT_REACT MALAYSIAN_SNR (06-09)]].

---

## 1. Duplication Map

Per famiglia concettuale, tutte le implementazioni trovate nei 10 file. "Consumer" = strategia/modulo che la usa.

### 1.1 Swing high/low & Pivot — **9 implementazioni indipendenti**

| # | Source | Algoritmo | Consumer | State/Persistenza | TF | Geometria | Invalidazione |
|---|---|---|---|---|---|---|---|
| 1 | `NXS_Structure.mqh:80-98` `NXS_IsSwingHigh/Low` | Frattale simmetrico, wing=3 barre L/R, wick-based | `NXS_ComputeStructureCore` → `g_struct`/`g_structH1` | Stateless, scrive in struct globale sovrascritta ogni call | Entry-TF + H1 fisso (2 istanze parallele) | Prezzo singolo | Nessuna (FIFO a 2 slot: solo ultimo+penultimo) |
| 2 | `NXS_StructureMultiLayer.mqh:23-24` | `iHighest/iLowest` su finestra `wing*2`, **algoritmo diverso da #1** | `NXS_ML_BuildLayer` (3 TF: entry/medium/high) | Stateless, per-layer | 3 TF paralleli, sistema indipendente da #1 | Prezzo singolo | Nessuna |
| 3 | `NXS_BjorgumZones.mqh:29-47` `_bj_isFractalHigh/Low` | Frattale 3-bar (2 barre L/R) | `NXS_BJ_Compute`, `NXS_Quasimodo_Detect` — dichiarato "pure visual, NO trading logic" | Stateless | Fisso al TF param | Prezzo singolo | N/A |
| 4 | `NXS_FibonacciContext.mqh:27-28` | `iHighest/iLowest` su `lookback` intero (finestra ampia, non frattale) | `NXS_Fib_Build` (range Fib/OTE) | Stateless | Fisso al TF param | Prezzo singolo | N/A |
| 5 | `NXS_Strategies.mqh:777-799` `_nxs_pivotwick_scan_tf` | Frattale multi-TF, pool persistente `g_pivotWickState` (8 livelli/TF) | **PIVOT_WICK, LEVEL_CONFLUENCE(_M5), LEVEL_REACTION(_M5)** — già riusato tra 4 consumer | **Stateful**, pool con flag `used` (fresh/consumed) | M15/M30/H1/H4/D1 paralleli | Prezzo singolo | Consumo one-shot per livello |
| 6 | `NXS_Strategies.mqh:2016-2020` `NXS_OB_UpdateSide` (swing ref) | `iHighest/iLowest(15)` solo come riferimento BOS locale | ORDER_BLOCK (interno) | Stateless | Fisso | Prezzo singolo | N/A |
| 7 | `NXS_Strategies_SMC.mqh:83-118` `_sfb_isPivotHigh/Low` | Pivot L/R configurabile | SWING_FALSEBREAK | Stateless | Fisso | Prezzo singolo | N/A |
| 8 | `NXS_Strategies_Institutional.mqh:427-430` | `iHighest/iLowest` inline H4 | WEEKLY_EXP | Stateless | H4 fisso | Prezzo singolo | N/A |
| 9 | `NXS_Strategies_SMC.mqh:796-808` | Inline, per BOS locale | OTE_CONT | Stateless | Parametrico | Prezzo singolo | N/A |

Fuori famiglia (dominio diverso, da NON includere nell'engine unificato ma notare la collisione di pattern): `_nxs_rsidivpine_pivot_low/high` (`NXS_Strategies.mqh:1888-1894`) — pivot calcolato sulla **serie RSI**, non sul prezzo, usato solo da RSI_DIV_PINE.

### 1.2 Break di struttura / BOS / CHOCH — **4 implementazioni**

| # | Source | Consumer | Note |
|---|---|---|---|
| 1 | `NXS_Structure.mqh:200-251` `g_struct.bosUp/bosDown/chochUp/chochDown` | Consumato pervasivamente da SMC + Institutional (letto, non ricalcolato) | **Canonico de-facto**: hysteresis-based, reso mutuamente esclusivo BOS/CHOCH in v2.0.34 |
| 2 | `NXS_StructureMultiLayer.mqh:27-30` | `NXS_ML_BuildLayer` (3 TF) | Versione ridotta: rottura raw dell'ultimo swing, **nessuna hysteresis** — criterio diverso da #1 per lo stesso concetto |
| 3 | `NXS_Strategies.mqh:2020-2021` (Order Block, `c > swingRef`) | ORDER_BLOCK | Test BOS ad-hoc locale, ignora `g_struct.bosUp` esistente |
| 4 | `NXS_Strategies_SMC.mqh:583-636` (SMS_BMS_RTO, labelling HH/LL/LH/HL) | SMS_BMS_RTO | Non è un duplicato puro: aggiunge una tassonomia (failure swing) che `g_struct` non ha — da trattare come estensione, non solo doppione |

### 1.3 Wick levels (come livello persistente, non feature) — **1 implementazione compiuta**

| Source | Consumer | Note |
|---|---|---|
| `NXS_Strategies_Experimental.mqh:55-706` `SNxsWickSide`/`SNxsWickReclaimState`/`SNxsWickShadowEvent` | WICK_SWEEP_REVERSAL, WICK_SWEEP_RECLAIM | **Il modello di lifecycle più maturo di tutto il codebase** — vedi §3, è il precedente architetturale più vicino allo schema richiesto dall'utente. Isolato: nessun `#include`/riuso di `g_struct`/`g_levels`/Fibonacci. |

`NXS_Reaction.mqh:23-26` usa `upWick`/`dnWick` solo come feature per-barra dentro `NXS_HasPriceReaction` (stateless, non un livello).

### 1.4 Support/Resistance — **2 implementazioni concettualmente distinte**

| # | Source | Geometria dato | Consumer |
|---|---|---|---|
| 1 | Implicito negli swing (§1.1) | Wick | Tutte le strategie che leggono `g_struct`/pool pivot |
| 2 | `NXS_Strategies.mqh:1201-1207` (SNR, ex-MALAYSIAN_SNR) | **Body-close**, `iHighest/iLowest(MODE_CLOSE, 12)` H4 | `_nxs_levelreact_core` (LEVEL_REACTION/CONFLUENCE) | Unica fonte body-based, non wick — un secondo "tipo" legittimo, non un doppione da eliminare |

### 1.5 Order Blocks — **2 engine completamente separati** (la duplicazione più consequenziale insieme a FVG)

| # | Source | Lifecycle | Consumer | Pool |
|---|---|---|---|---|
| 1 | `NXS_Structure.mqh:100-120` `NXS_DetectOrderBlocks` + `g_levels[]`/`NXS_MitigateLevels` | Crudo: attivo → 2 tocchi → `active=false`. Nessuna misura di penetrazione | STRUCT_REACT (via `g_reaction`) | Pool condiviso con swing+FVG, max 40, entry-TF only |
| 2 | `NXS_Strategies.mqh:1992-2062` `SNXSOBState`/`NXS_OB_UpdateSide` | **Maturo**: created→active/fresh→waiting retest (max N barre)→touched+rejection→one-shot consumed, OPPURE invalidato se il prezzo attraversa la zona | ORDER_BLOCK diretto; **OB_MIT** via wrapper (`NXS_Strategies_SMC.mqh:353-364`, non ri-duplicato) | Per-lato (`g_obBuy`/`g_obSell`), non un pool storico |

Due "Order Block" con criteri di creazione, mitigazione e persistenza incompatibili, che alimentano consumer diversi.

### 1.6 FVG (Fair Value Gap) — **6 implementazioni geometriche, la famiglia più frammentata**

| # | Source | Geometria/stato | Consumer | Note |
|---|---|---|---|---|
| 1 | `NXS_Strategies.mqh:1481-1504` | Stateless puro, nessuna zona persistente | **FVG_CONT — REGRESSION FIXTURE**, non toccare | Modello più povero: nessun lifecycle, nessuna mitigation |
| 2 | `NXS_Structure.mqh:122-143` `NXS_DetectFVG` + pool condiviso | Zona in `g_levels[]`, 2-touch mitigation | STRUCT_REACT (via `g_reaction`) | Stesso pool di OB #1 |
| 3 | `NXS_Strategies_SMC.mqh:166-192` | Inline 3-candele, invalidata da CHOCH | IFVG | Stateless |
| 4 | `NXS_Strategies_SMC.mqh:198-232` | Inline 3-candele | FVG_MIT | Stateless, nessuna età tracciata |
| 5 | `NXS_Strategies_SMC.mqh:251-352` `g_fvgMitWBull/Bear` | **Stateful**, array con età (`tBorn`), TTL 15 barre, max 24 zone | FVG_MIT_WINDOW | Modello più maturo della famiglia FVG |
| 6 | `NXS_Strategies_Institutional.mqh:509-560` | Stessa geometria 3-candele di #3/#4, **duplicata a mano in 2 punti** (LIQ_VOID, DISP_REBAL) con commento esplicito "corretta il 17/07" propagato manualmente | LIQ_VOID, DISP_REBAL | Rischio di manutenzione dimostrato: bugfix propagati a mano tra copie |

### 1.7 Sweep — **4 famiglie, non tutte duplicati puri**

| # | Source | Modello | Consumer | Classificazione natura |
|---|---|---|---|---|
| 1 | `NXS_Strategies.mqh:1436-1461` `NXS_DetectSweepExt`/`SNXSSweepExt` | PDH/PDL/Asia H-L/equal H-L | LIQ_SWEEP, SH_BMS_RTO, JUDAS_SWING, LDN_REVERSAL, PO3, AMD_REVERSAL, SILVER_BULLET — **7 consumer, già ben riusato** | Canonico per sweep di riferimenti di sessione/liquidità ICT |
| 2 | `_nxs_levelreact_core` (`NXS_Strategies.mqh:990-1030`) | Breach oltre tolleranza + chiusura di rientro, su pool pivot/SNR | LEVEL_REACTION/CONFLUENCE | Unica famiglia che misura **profondità in pip** — feature unica da preservare |
| 3 | `NXS_Strategies_Experimental.mqh` (wick sweep) | Sweep su wick-level dedicato, soglia pip fissa | WICK_SWEEP_REVERSAL/RECLAIM | Vedi §1.3 |
| 4 | `NXS_Strategies_SMC.mqh` (SH_BMS_RTO / SH_BMS_RTO_V2 / SilverBullet) | 3 state machine "sweep→MSS→retest" **quasi identiche ma incompatibili** (enum, soglie, geometria zona diversi tra V1 e V2) | SH_BMS_RTO, SH_BMS_RTO_V2, SilverBullet | Duplicazione reale entro la stessa famiglia concettuale |

### 1.8 Reclaim — **2 significati diversi collidono sullo stesso nome**

| # | Source | Significato | Consumer | Nota |
|---|---|---|---|---|
| 1 | `_nxs_levelreact_core` + `SNxsWickReclaimState` | Reclaim di **livello strutturale** (prezzo rientra oltre il livello dopo lo sweep) | LEVEL_REACTION, WICK_SWEEP_RECLAIM | Stessa famiglia concettuale, 2 implementazioni |
| 2 | `NXS_Strategies.mqh:1759-1764` | Reclaim = **incrocio di prezzo su EMA** (non un livello) | **EMA_PULLBACK — REGRESSION FIXTURE**, non toccare | Collisione di naming, dominio diverso, va escluso dallo schema unificato |

### 1.9 Mitigation / Retest — **3 modelli**

| # | Source | Modello | Consumer |
|---|---|---|---|
| 1 | `NXS_MitigateLevels` (Structure.mqh:160-181) | 2-touch → inattivo, nessuna profondità | Pool condiviso (OB/FVG/swing) → STRUCT_REACT |
| 2 | `SNXSOBState` (Strategies.mqh) | Waiting-bars + touch + candela di rigetto → one-shot consumed | ORDER_BLOCK, OB_MIT |
| 3 | `FVG_MIT_WINDOW` (SMC.mqh) | TTL in barre (age-based invalidation) | FVG_MIT_WINDOW |

Retest è oggi incorporato ad-hoc in ciascuno di questi 3 modelli (waiting-bars counter per-strategia), mai un concetto esplicito e condiviso.

### 1.10 Reaction generica — **canonico + 2 varianti locali**

| # | Source | Modello | Consumo |
|---|---|---|---|
| 1 | `NXS_Reaction.mqh` `g_reaction`/`NXS_DetectReaction` | Quality score continuo 0-100 (pin/chiusura direzionale + bonus trend/mitigazione/EMA200) | **Consumato in 3 modi diversi e incompatibili**: gate assoluto (STRUCT_REACT), gate a doppia condizione (`NXS_SMCReactionOK`, OB/OB_MIT), puro modificatore additivo (`NXS_ReactionScoreMod`, score generale) |
| 2 | `_nxs_levelreact_core` | Breach-pips based, con conferma a N barre (entry ritardata, non immediata) | LEVEL_REACTION/CONFLUENCE |
| 3 | `SNxsWickShadowEvent` (Experimental) | Reclaim-trigger/reclaim-level con timestamp + stato enum discreto | WICK_SWEEP shadow |

**Osservazione strutturale**: `g_reaction` produce uno **score continuo**, mai uno stato discreto sweep/accept/reject — è il gap più importante rispetto allo schema `SNXSReactionEvent` richiesto (che vuole `reaction_type` discreto).

### 1.11 Trendlines — **1 implementazione, qualità insufficiente per il target**

`NXS_UpdateTrendline` (Structure.mqh:145-158): non ha veri anchor-point + slope nel tempo, è un'estrapolazione lineare grezza (`ultimoSwing + delta*0.5`), azzerata ogni call. Non c'è nulla con cui confrontarla: va ridisegnata da zero nel nuovo schema (che richiede `anchors`/`slope`), non migrata.

### 1.12 Bjorgum zones — probabile componente non-trading

`g_bjZones[12]` (BjorgumZones.mqh): array persistente ma azzerato/ricostruito da zero a ogni `NXS_BJ_Compute()`; **nessun consumer di strategia trovato** in nessuno dei 10 file analizzati. Dichiarato "pure visual indicator, NO trading logic" nell'header. Da verificare se è davvero morto prima di decidere se includerlo nell'unificazione.

---

## 2. Canonical Candidate Map

Classificazione per ciascuna implementazione (5 categorie: KEEP AS CANONICAL / MIGRATE TO COMMON ENGINE / SHADOW FIRST / DEPRECATE LATER / UNKNOWN).

| Famiglia | Implementazione | Classificazione | Motivazione |
|---|---|---|---|
| Swing/pivot | `_nxs_pivotwick_scan_tf` + `g_pivotWickState` (#5) | **KEEP AS CANONICAL** (tra le pivot) → **MIGRATE TO COMMON ENGINE** (fase successiva) | Già multi-TF, già pool stateful, già riusato da 4 consumer |
| Swing/pivot | `NXS_IsSwingHigh/Low` (#1, Structure.mqh) | **KEEP AS CANONICAL** (per BOS/CHOCH) | Alimenta `g_struct`, il canonico de-facto per trend/BOS |
| Swing/pivot | `NXS_StructureMultiLayer` (#2) | **SHADOW FIRST** poi **DEPRECATE LATER** | Sistema parallelo non comunicante col #1: va verificato chi lo consuma davvero prima di rimuoverlo |
| Swing/pivot | Bjorgum fractal (#3), Fibonacci window (#4) | **UNKNOWN** | Nessun consumer di trading trovato/nessuna urgenza; verificare uso reale prima di classificare |
| Swing/pivot | OB swing ref (#6), SWING_FALSEBREAK (#7), WEEKLY_EXP (#8), OTE_CONT (#9) | **MIGRATE TO COMMON ENGINE** | Duplicati minori, bassa complessità di porting, nessuna feature unica |
| Swing/pivot | RSI_DIV_PINE pivot-su-RSI | **UNKNOWN / fuori scope** | Dominio diverso (indicatore, non prezzo) — non è un level, non entra nell'engine |
| BOS/CHOCH | `g_struct.bosUp/chochUp` | **KEEP AS CANONICAL** | Consumato pervasivamente, hysteresis già corretta (v2.0.34) |
| BOS/CHOCH | StructureMultiLayer raw BOS | **SHADOW FIRST** | Criterio diverso (no hysteresis) da verificare prima di unificare |
| BOS/CHOCH | OB ad-hoc `c>swingRef` | **MIGRATE TO COMMON ENGINE** | Deve leggere il canonico, non ricalcolare |
| BOS/CHOCH | SMS_BMS_RTO HH/LL/LH/HL | **SHADOW FIRST** | Tassonomia potenzialmente complementare, non solo doppione — verificare prima di fondere |
| Wick level | `SNxsWickSide`/`SNxsWickReclaimState` | **MIGRATE TO COMMON ENGINE — PRIMA FAMIGLIA** (vedi §4) | Già quasi isomorfo allo schema target, isolato, a rischio live nullo |
| S/R | Swing wick-based | vedi Swing/pivot | — |
| S/R | SNR body-close H4 | **SHADOW FIRST** | Tipo di livello legittimo e distinto (body vs wick), non un doppione da eliminare — va preservato come secondo LEVEL SOURCE type |
| Order Block | `SNXSOBState` (Strategies.mqh) | **KEEP AS CANONICAL** (tra i 2 OB) → **MIGRATE TO COMMON ENGINE** | Lifecycle più maturo, più vicino al target |
| Order Block | `NXS_DetectOrderBlocks`/pool (Structure.mqh) | **SHADOW FIRST** | Alimenta STRUCT_REACT via `g_reaction`: consolidare richiede prima un parity check su quel percorso |
| FVG | FVG_CONT | **KEEP AS CANONICAL — fixture congelata** | Esplicitamente protetta come regression fixture; non va mai migrata silenziosamente, solo shadowata a tempo indeterminato se/quando un motore FVG unificato esisterà |
| FVG | `NXS_DetectFVG`/pool (Structure.mqh) | **SHADOW FIRST** | Stesso motivo di OB pool sopra (alimenta STRUCT_REACT) |
| FVG | IFVG, FVG_MIT (inline) | **MIGRATE TO COMMON ENGINE** | Nessuna feature unica, stateless, porting a basso rischio |
| FVG | FVG_MIT_WINDOW | **KEEP AS CANONICAL** (tra le FVG) → **MIGRATE TO COMMON ENGINE** | Unico modello FVG con età/TTL, il più vicino al target lifecycle |
| FVG | LIQ_VOID/DISP_REBAL (duplicate a mano) | **MIGRATE TO COMMON ENGINE — priorità alta** | Rischio di manutenzione già dimostrato (bugfix propagati a mano) |
| Sweep | `NXS_DetectSweepExt`/`SNXSSweepExt` | **KEEP AS CANONICAL** | Già ben riusato (7 consumer), nessuna urgenza di migrazione |
| Sweep | LEVEL_REACTION breach-based | **SHADOW FIRST** | Unica fonte con profondità in pip: preservare la feature, non solo il codice |
| Sweep | Wick sweep (Experimental) | **MIGRATE TO COMMON ENGINE — PRIMA FAMIGLIA** | Vedi §4 |
| Sweep | SH_BMS_RTO / V2 / SilverBullet (3 state machine) | **SHADOW FIRST** | Vanno confrontate le 3 prima di decidere se sono davvero equivalenti o comportamentalmente distinte |
| Reclaim | LEVEL_REACTION reclaim | **SHADOW FIRST** | Stessa famiglia di sweep breach-based |
| Reclaim | Wick reclaim (Experimental) | **MIGRATE TO COMMON ENGINE — PRIMA FAMIGLIA** | Vedi §4 |
| Reclaim | EMA_PULLBACK "reclaim" | **UNKNOWN / fuori scope** | Naming collision, non è un level reclaim — fixture, non toccare |
| Mitigation | `NXS_MitigateLevels` | **SHADOW FIRST** | Alimenta `g_reaction` canonico, serve parity check |
| Mitigation | `SNXSOBState` touch/rejection | **MIGRATE TO COMMON ENGINE** | — |
| Mitigation | FVG_MIT_WINDOW TTL | **MIGRATE TO COMMON ENGINE** | Pattern age-based da generalizzare |
| Reaction | `g_reaction`/`NXS_DetectReaction` | **KEEP AS CANONICAL** | Più consumato, ma serve un adapter verso `reaction_type` discreto |
| Reaction | `NXS_ReactionScoreMod`/`NXS_SMCReactionOK` (consumer) | **SHADOW FIRST** | Semantiche gate/modifier divergenti da preservare esattamente durante la transizione |
| Reaction | LEVEL_REACTION breach-based reaction | **SHADOW FIRST** | Confirmation-by-persistence è un `reaction_type` alternativo da preservare, non scartare |
| Trendlines | `NXS_UpdateTrendline` | **DEPRECATE LATER** | Non soddisfa il modello geometrico target (anchors/slope); va ridisegnata, non migrata |
| Bjorgum zones | `g_bjZones` | **UNKNOWN** | Nessun consumer di trading trovato — verificare se è morto prima di decidere |
| Fibonacci/OTE | `NXS_Fib_Build` | **KEEP AS CANONICAL** | Unica implementazione, nessuna duplicazione; bassa priorità di migrazione |

---

## 3. Unified schema proposal

Il precedente architetturale più vicino a questo schema esiste già nel codice: `SNxsWickSide` + `SNxsWickReclaimState` + `SNxsWickShadowEvent` in `NXS_Strategies_Experimental.mqh`. Lo schema sotto è la **generalizzazione** di quel pattern (già validato in produzione come metodologia shadow/parity) alle altre famiglie di livelli, non un'invenzione da zero.

```mql5
enum ENUM_NXS_LEVEL_LIFECYCLE {
   NXS_LVL_CREATED,
   NXS_LVL_FRESH_UNTESTED,
   NXS_LVL_APPROACHED,
   NXS_LVL_TOUCHED,
   NXS_LVL_SWEPT,             // ramo: sfondato oltre soglia
   NXS_LVL_ACCEPTED,          // ramo: prezzo si ferma/rigetta senza sfondare
   NXS_LVL_REJECTED,          // ramo: rigetto esplicito (candela di reazione)
   NXS_LVL_RECLAIMED,         // ramo: rientro oltre il livello dopo sweep
   NXS_LVL_BROKEN,            // ramo: rottura strutturale confermata
   NXS_LVL_RETEST_OTHER_SIDE,
   NXS_LVL_INVALIDATED
};

enum ENUM_NXS_LEVEL_SOURCE {
   NXS_SRC_SWING_FRACTAL,     // NXS_IsSwingHigh/Low e derivati
   NXS_SRC_PIVOT_MULTITF,     // _nxs_pivotwick_scan_tf / g_pivotWickState
   NXS_SRC_SNR_BODY,          // SNR body-close H4
   NXS_SRC_ORDER_BLOCK,
   NXS_SRC_FVG,
   NXS_SRC_WICK_EXTREME,      // WICK_SWEEP family
   NXS_SRC_SESSION_LIQUIDITY, // PDH/PDL/Asia (SNXSSweepExt)
   NXS_SRC_TRENDLINE,
   NXS_SRC_FIBONACCI
};

enum ENUM_NXS_LEVEL_GEOMETRY { NXS_GEO_PRICE, NXS_GEO_ZONE, NXS_GEO_DIAGONAL };

struct SNXSUnifiedLevel {
   long     level_id;              // identita' stabile, incrementale (come g_wickLevelIdCounter)
   ENUM_NXS_LEVEL_SOURCE source;
   string   source_strategy;       // "" se prodotto dal Level Engine condiviso, altrimenti id strategia
   ENUM_TIMEFRAMES source_tf;
   ENUM_NXS_LEVEL_TYPE  type;      // riuso dell'enum esistente NXS_LVL_SWING_HIGH/OB_BULL/FVG_BULL/... esteso
   ENUM_NXS_LEVEL_GEOMETRY geometry;
   double   price;                 // valida se geometry==NXS_GEO_PRICE
   double   zone_top, zone_bot;    // validi se geometry==NXS_GEO_ZONE
   double   anchor1_price, anchor1_time_ord;   // validi se geometry==NXS_GEO_DIAGONAL
   double   anchor2_price, anchor2_time_ord;
   double   slope;                 // ricavato dai due anchor, cache
   datetime created_time;
   datetime first_touch_time;
   int      touch_count;
   double   max_penetration;       // in price o pip (convenzione dichiarata a livello di build, come i pip GOLD $0.10)
   double   sweep_depth;           // profondita' oltre il livello al momento dello sweep (feature LEVEL_REACTION)
   datetime break_time;
   datetime reclaim_time;
   ENUM_NXS_LEVEL_LIFECYCLE state;
   bool     active;
   bool     consumed;              // trade realmente aperto su questo livello (stato terminale, come SNxsWickSide.consumed)
   bool     invalidated;
   long     confluence_ids[];      // altri level_id in confluenza (sostituisce i bonus impliciti in NXS_DetectReaction)
   long     linked_trade_ids[];    // ticket/id trade collegati a questo livello
};

enum ENUM_NXS_REACTION_TYPE {
   NXS_REACT_TOUCH, NXS_REACT_SWEEP, NXS_REACT_ACCEPT, NXS_REACT_REJECT,
   NXS_REACT_RECLAIM, NXS_REACT_BREAK, NXS_REACT_RETEST
};

struct SNXSReactionEvent {
   long     event_id;
   long     level_id;               // FK verso SNXSUnifiedLevel
   datetime timestamp;
   ENUM_NXS_REACTION_TYPE reaction_type;
   int      direction;              // DIR_BUY/DIR_SELL, riuso costanti esistenti
   double   strength;                // 0-100, sostituisce/generalizza g_reaction.quality
   double   penetration;             // in pip o price, coerente con max_penetration del livello
   bool     reclaim;
   double   close_location;          // 0-1, posizione della chiusura nel range della barra (rigore pin-bar)
   ENUM_TIMEFRAMES source_tf;
};
```

Note di raccordo con lo stato attuale:
- `SNXSUnifiedLevel.level_id`/`created_time`/`touch_count`/`consumed` mappano 1:1 su `SNxsWickSide.id`/`createdAt`/(derivabile)/`consumed`.
- `max_penetration`/`sweep_depth` generalizzano `SNxsWickShadowEvent.max_penetration_pips` — oggi calcolato SOLO per il wick shadow, in nessun'altra famiglia (nemmeno LEVEL_REACTION, che misura breach ma non lo storicizza per livello).
- `reclaim_time` generalizza `SNxsWickReclaimState.reclaim_level_time`.
- Il campo `strength` in `SNXSReactionEvent` è la generalizzazione esplicita di `g_reaction.quality` (continuo 0-100) MA con `reaction_type` reso discreto — oggi `g_reaction` non ha un campo discreto equivalente, è il gap più grande da colmare nell'adapter Phase A.

---

## 4. First migration candidate

**Famiglia: Wick level lifecycle (sweep/reclaim su estremi di wick H4) — `NXS_Strategies_Experimental.mqh`, strategie WICK_SWEEP_REVERSAL/WICK_SWEEP_RECLAIM.**

Motivazione (dettagliata anche in risposta finale):
1. **Isomorfismo quasi diretto**: `SNxsWickSide`/`SNxsWickReclaimState`/`SNxsWickShadowEvent` coprono già ~80% dei campi di `SNXSUnifiedLevel`/`SNXSReactionEvent` proposti sopra. Il porting è in gran parte un rename/riorganizzazione di uno schema già esistente e già testato, non un design da zero.
2. **Isolamento**: questo file non fa `#include`/non legge `g_struct`, `g_levels[]`, `g_reaction`, Fibonacci o `SNXSSweepExt`. Migrarlo non può toccare, nemmeno indirettamente, le altre 51 strategie live o gli stati condivisi (`g_struct`/`g_reaction`) usati da SMC/Institutional.
3. **Rischio live nullo oggi**: per il bug indipendente "terzo cancello silenzioso" (`NXS_StrategyKnown`, già documentato in [[NEXUS EA - Audit Structure-Reaction-LEVEL_REACTION e WICK_SWEEP Bloccato dal Terzo Cancello (10-09)]], NON in scope qui e da NON toccare in questo task), WICK_SWEEP_REVERSAL produce oggi **zero trade reali** (165 sweep rilevati, 0 aperture). Si può iterare sul nuovo engine senza nessun rischio di alterare un comportamento di trading realmente in produzione.
4. **Metodologia già pronta**: esiste già in codice un meccanismo di shadow-vs-canonico con parity check (`NXS_WickShadow_PrintSummary`, confronto `shadow_sweeps` vs `canonical_sweepsDetected`) — la Fase B (shadow old-vs-new) di questo piano può letteralmente estendere quel meccanismo invece di costruirne uno nuovo.
5. **Fixture esplicita**: l'utente ha indicato "WICK baseline/failure history" tra le regression fixture da preservare — segnale che la baseline attuale (165 sweep/0 trade, causa nota) è già il riferimento su cui il nuovo engine dovrà essere confrontato.

File coinvolti per questa migrazione (quando si passerà all'implementazione, NON ora): `NXS_Strategies_Experimental.mqh` (sorgente esistente), nuovo modulo `NXS_LevelEngine.mqh`/`NXS_ReactionEngine.mqh` (Phase A, telemetry-only, accanto al vecchio) — nomi indicativi, da confermare in fase di design del file-by-file plan.

---

## 5. Risks

| Rischio | Impatto | Mitigazione proposta |
|---|---|---|
| Alterare per errore il comportamento di FVG_CONT/ADX_RSI/EMA_PULLBACK RAW toccando file condivisi (es. `NXS_Structure.mqh`) durante il porting di altre famiglie | Rompe le regression fixture ufficiali, invalida confronti storici | Ogni Phase C successiva alla prima tocca SOLO file isolati per famiglia; nessuna modifica a `NXS_Structure.mqh`/`NXS_Reaction.mqh` finché non esiste un parity test verde per TUTTI i loro consumer (STRUCT_REACT, SMC, Institutional) |
| `g_reaction`/`g_struct` sono stato globale condiviso, non per-TF: un refactor incompleto può introdurre letture cross-TF errate (bug già noto, vedi §multi-TF nell'audit) | Falsi segnali silenziosi, difficili da individuare | Il nuovo registry deve essere esplicitamente per-TF fin dalla Fase A, mai un singleton globale come oggi |
| I 2 motori Order Block e le 6 varianti FVG hanno consumer diversi con criteri di gate diversi (assoluto/doppia condizione/modificatore) | Consolidare prematuramente può cambiare la frequenza/qualità dei segnali di STRUCT_REACT, OB, OB_MIT, IFVG, FVG_MIT(_WINDOW) simultaneamente | Migrare UNA famiglia alla volta (regola già imposta dall'utente); ogni famiglia successiva alla prima richiede il proprio parity test dedicato prima di Phase C |
| Bug indipendente "terzo cancello silenzioso" (registry strategie) potrebbe mascherare falsi negativi durante lo shadow testing di future strategie sperimentali collegate al nuovo engine | Un parity test potrebbe risultare "verde" per il motivo sbagliato (zero trade su entrambi i lati) | Il parity test di Fase D deve confrontare EVENTI (livelli creati, sweep, reclaim), non solo trade aperti — esattamente come già fa `NXS_WickShadow_PrintSummary` oggi |
| Pressione a includere anche Bjorgum zones / trendline nel primo giro perché "sembrano semplici" | Bjorgum ha 0 consumer accertati (rischio di formalizzare codice morto), trendline non ha nemmeno un modello valido da migrare (va ridisegnata) | Escluderli esplicitamente dalle prime fasi (§8) |
| Naming collision (reclaim EMA vs reclaim livello, pivot RSI vs pivot prezzo) può confondere futuri contributor nel leggere il registry unificato | Bug di integrazione per ambiguità semantica, non di logica | Documentare esplicitamente le collisioni nello schema/commenti del nuovo modulo (già fatto in questa nota, §1.8) |

---

## 6. Parity acceptance criteria

Per qualunque famiglia migrata (a partire dalla prima), la Fase D (parity test) è superata solo se, sullo stesso storico e stesso simbolo/TF:

1. **Conteggio eventi identico**: n. livelli creati, n. sweep, n. reclaim, n. invalidazioni prodotti dal nuovo engine == quelli del motore legacy corrispondente (tolleranza zero sugli eventi discreti, non solo sui trade).
2. **Timestamp identici** (±0 barre) per ogni evento corrispondente — non solo lo stesso conteggio ma lo stesso momento.
3. **Prezzo/zona identici** (tolleranza = 1 point, per arrotondamenti) per ogni livello corrispondente.
4. **Nessuna variazione nei trade reali** delle strategie NON migrate (ADX_RSI RAW, EMA_PULLBACK RAW, FVG_CONT RAW invariati bit-per-bit nei risultati RAW; WICK baseline/failure history invariata finché il vecchio motore resta quello attivo).
5. **Zero nuovi trade** generati dal nuovo engine durante Phase A/B (telemetry-only per definizione — se anche un solo ordine reale nasce dal nuovo path prima di Phase C, è una violazione di scope, non solo un bug).
6. Per la famiglia migrata in Phase C: il conteggio di trade REALI (dopo lo switch) deve combaciare 1:1 col vecchio motore sullo stesso storico, prima di poter dichiarare la migrazione conclusa e passare a Phase E.
7. Report di parity scritto (tabella vecchia-vs-nuovo, come già lo stile usato in `NXS_WickShadow_PrintSummary`), non solo "0 differenze" affermato a parole.

---

## 7. File-by-file implementation plan (roadmap, non eseguita ora)

Solo indicazione di dove ogni fase toccherebbe codice — nessuna di queste modifiche viene fatta in questo task.

| File | Ruolo nel piano | Fase in cui viene toccato |
|---|---|---|
| `NXS_LevelRegistry.mqh` (nuovo) | Definisce `SNXSUnifiedLevel`, pool/array registry, API create/update/query | A |
| `NXS_ReactionEngine.mqh` (nuovo) | Definisce `SNXSReactionEvent`, classificazione discreta reaction_type | A |
| `NXS_Strategies_Experimental.mqh` | Prima famiglia: wrapper telemetry-only che alimenta il nuovo registry accanto a `SNxsWickSide` esistente, senza toccare la logica canonica | A, poi B (shadow) |
| (nessuno — solo strumentazione OnDeinit/log) | Parity report Phase B/D per la prima famiglia | B, D |
| `NXS_Strategies_Experimental.mqh` | Switch dell'esecuzione reale (`NXS_TryExecuteRC`) dal vecchio `SNxsWickSide` al nuovo registry, SOLO dopo Phase D verde | C |
| `NXS_Strategies.mqh` (SNXSOBState, ORDER_BLOCK/OB_MIT) | Seconda famiglia candidata (Order Block, engine già maturo) | E (non prima) |
| `NXS_Strategies_SMC.mqh` (FVG_MIT_WINDOW) | Terza famiglia candidata (FVG, engine con TTL già maturo) | E (non prima) |
| `NXS_Strategies_Institutional.mqh` (LIQ_VOID/DISP_REBAL) | Consolidamento FVG duplicate a mano, dopo che FVG_MIT_WINDOW è il canonico migrato | E (non prima) |
| `NXS_Structure.mqh`, `NXS_Reaction.mqh` | Consolidamento finale (pool OB/FVG condiviso + `g_reaction`) — richiede parity su STRUCT_REACT + tutti i consumer SMC | E, ultimo, con massima cautela |
| `NXS_StructureMultiLayer.mqh` | Deprecazione dopo shadow contro `g_struct`, se confermato ridondante | Dopo E |
| `NXS_BjorgumZones.mqh` | Da verificare se ha consumer reali prima di decidere qualunque azione | Fuori roadmap finché non chiarito |

---

## 8. Cosa NON toccare (in questo task e nelle prime fasi)

- **Nessuna logica live**: nessuna strategia, SL/TP, execution, TF viene modificato in questo task (audit-only, come richiesto).
- **Regression fixture congelate**: ADX_RSI RAW, EMA_PULLBACK RAW, FVG_CONT RAW, WICK baseline/failure history (165 sweep/0 trade) — i loro risultati non devono cambiare per NESSUN motivo finché non c'è un parity test esplicito che le riguarda direttamente.
- **`NXS_Structure.mqh`/`NXS_Reaction.mqh`**: sono condivisi da troppi consumer (STRUCT_REACT + tutta la famiglia SMC/Institutional che legge `g_struct`) per essere toccati prima che la Fase E sia raggiunta con successo sulle famiglie più isolate.
- **Il bug "terzo cancello silenzioso"** (`NXS_StrategyKnown`/registry strategie) — fuori scope per questo piano, documentato altrove, da NON correggere qui anche se rilevante per il rischio nullo della prima migrazione.
- **`knowledge/strategy_database.json` / `contracts/generate_registry.py`** — nessuna nuova strategia da registrare in questa fase (Phase A/B sono telemetry-only, non richiedono un id di strategia registrato).
- **Bjorgum zones e Trendline** — esclusi dalle prime fasi per mancanza di consumer accertati (Bjorgum) o di un modello valido da cui partire (Trendline).
- **Le 3 varianti sweep→MSS→retest (SH_BMS_RTO/V2/SilverBullet)** — non vanno fuse per assunzione; richiedono uno shadow comparativo dedicato prima di qualunque decisione di merge.
