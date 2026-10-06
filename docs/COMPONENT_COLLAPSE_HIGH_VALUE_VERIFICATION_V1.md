# Component Collapse — High Value Verification V1

**Stato:** verifica di codice, non ancora committata. Nessuna modifica a codice/registry, nessun backtest nuovo. Ogni claim è marcato CODE_VERIFIED (letto il codice reale) / HISTORICAL_NOTE (solo da nota vault) / UNKNOWN. Scope: solo i cluster prioritari richiesti, non le 83 strategie.

**Scoperta trasversale, più importante di qualunque singolo cluster** (CODE_VERIFIED): esiste un **enum di attribuzione `s.strat`** (`STRAT_*`, in `NXS_Defines.mqh`) distinto dal nome leggibile `s.stratName`. Più strategie strutturalmente diverse condividono lo stesso `s.strat`, il che significa che qualunque statistica/analisi chiavata su `strat` (invece di `stratName`) le tratterebbe come la stessa identità. Questo è un meccanismo di possibile double-counting **più forte e più esteso** di quanto ipotizzato nell'audit precedente, perché è strutturale nel motore, non solo un sospetto di nome.

---

## Cluster 1 — ORDER_BLOCK / OB_MIT / ORDER_BLOCK_V2

- **ORDER_BLOCK** (`NXS_Strat_OrderBlock`, `NXS_Strategies.mqh:2142`): `s.strat = STRAT_ORDER_BLOCK`. Logica propria: zona OB persistente (`g_obBuy`/`g_obSell`) + conferma H1 + reazione SMC.
- **OB_MIT**: la funzione chiamata dalla EA viva, `NXS_Strat_OB_Mitigation_Structural()`, è **macro-ridefinita** (`NXS_ReusePerformancePack.mqh:2366`) a `NXR_Strat_OB_Mitigation()` (riga 2294). Questa a sua volta consuma uno **stato condiviso globale** (`g_nxrTrigger`, motore `NXR_TriggerSignalFor`) filtrato su `NXR_ZONE_OB_BULL/BEAR`, e **assegna esplicitamente `s.strat = STRAT_ORDER_BLOCK`** (riga 2311) — **stesso identico enum di ORDER_BLOCK**. Commento nel codice (righe 2298-2304) conferma che questo era un bug di nomenclatura già corretto una volta ("un breaker NON è una normale mitigation... venivano attribuiti entrambi a OB_MIT").
- **ORDER_BLOCK_V2**: nel registry, `live_implementation=False`, `research_parity=NOT_IMPLEMENTED` — **nessun codice MQL5 o research esiste per questo strategy_id**. Non è una variante con codice proprio, è un placeholder di registry.

**Classificazione:** ORDER_BLOCK ↔ OB_MIT = **SAME_COMPONENT** (stesso enum di attribuzione, stato di zona condiviso) — **CODE_VERIFIED**, più forte della sola HISTORICAL_NOTE di partenza. ORDER_BLOCK_V2 = **UNKNOWN** (nessun codice da verificare — non "variante nascosta", semplicemente non implementata).

## Cluster 2 — FVG_CONT / FVG_CONT_V2 / FVG_MIT / FVG_MIT_WINDOW / IFVG / IFVG_CHOCH_WINDOW / LIQ_VOID

Quattro funzioni live realmente distinte, **tutte con `s.strat = STRAT_FVG_CONT`**:

| strategy_id (EA) | Funzione reale | Logica | `s.strat` |
|---|---|---|---|
| FVG_CONT | `NXS_Strat_FVG()` (riga 1488) | Gap a 3 candele + trend H1 esterno | `STRAT_FVG_CONT` |
| IFVG | `NXS_Strat_IFVG_Reversal()` (SMC.mqh:163) | Inverse-FVG: invalidazione di un gap + CHoCH | `STRAT_FVG_CONT` |
| FVG_MIT | `NXS_Strat_FVG_Mitigation()` → **macro-ridefinita** a `NXR_Strat_FVG_Mitigation()` (ReusePerformancePack:2290) | Stato condiviso `g_nxrTrigger`, zona `NXR_ZONE_FVG_BULL/BEAR` | `STRAT_FVG_CONT` |
| FVG_MIT_WINDOW | `NXS_Strat_FVG_Mitigation_Window()` (SMC.mqh:312) | Tracker a finestra propria (`g_fvgMitWBullCount`), NON passa per NXR | `STRAT_FVG_CONT` |

**4 funzioni geometricamente diverse, 1 solo enum di attribuzione.** Qualunque statistica su `strat` confonderebbe tutte e 4.

**Scoperta aggiuntiva non ipotizzata:** il commento a `NXS_ReusePerformancePack.mqh:2272-2281` dichiara l'intento esplicito "IFVG/FVG_MIT/OB_MIT... converge on NXR as sole source of truth" — ma **solo FVG_Mitigation e OB_Mitigation_Structural sono effettivamente macro-ridefinite**; **IFVG non lo è** (continua a chiamare la propria logica originale, `NXS_Strat_IFVG_Reversal`, non `NXR_Strat_IFVG_Reversal` che esiste ma non è mai raggiunto dal selettore EA). L'intento dichiarato nel commento e il comportamento reale del codice **divergono** — IFVG non è unificata come il commento afferma.

**Discrepanza registry-vs-codice trovata (non richiesta, ma rilevante):** il registry classifica `FVG_MIT_WINDOW` come `live_implementation=False`, `selector_index=None`. Il codice reale ha `InpStrat_FVG_MIT_WINDOW` + `NXS_SelectorAllows(39)` attivamente chiamato dalla EA (`NEXUS_EA_v2.mq5:542`) — **la strategia è viva nel codice, il registry dice il contrario**.

**FVG_CONT_V2, IFVG_CHOCH_WINDOW**: come ORDER_BLOCK_V2, nessun codice (`live_implementation=False`, `NOT_IMPLEMENTED`) — placeholder, non varianti verificabili.

**LIQ_VOID**: il registry dichiara esplicitamente `proxy_for: FVG_CONT` — non un'inferenza di questo audit, un campo già popolato nel registry stesso.

**Classificazione:** FVG_CONT / IFVG / FVG_MIT / FVG_MIT_WINDOW = **VARIANT_OF_SAME_SETUP** (stesso fenomeno — fair value gap — 4 geometrie/meccanismi di detection reali e distinti, ma 1 solo enum di attribuzione) — **CODE_VERIFIED**. LIQ_VOID = **SAME_PHENOMENON_DIFFERENT_PROXY** per dichiarazione esplicita del registry — **CODE_VERIFIED** (campo registry, non inferenza). FVG_CONT_V2/IFVG_CHOCH_WINDOW = **UNKNOWN** (non implementate).

## Cluster 3 — MALAYSIAN_SNR + varianti

- **MALAYSIAN_SNR** (base, live): la EA chiama `NXS_Strat_MalaysianSNR_Rejection()`, macro-ridefinita (ReusePerformancePack:2367) a `NXR_Strat_MalaysianSNR()` (riga 2316). Questa funzione **combina per score** due calcoli: il trigger NXR condiviso (zona `NXR_ZONE_SNR_SUPPORT/RESISTANCE`) **e** la vera logica legacy (`NXS_Strat_MalaysianSNR_Rejection`, SMC.mqh:875, supporti/resistenze H4 "a corpo" su 12 barre) — vince chi ha score più alto. **Entrambi i rami, quando restituiti direttamente dalla funzione legacy, usano `s.strat = STRAT_STRUCT_REACT`** (SMC.mqh:877) — **non un enum MALAYSIAN_SNR dedicato**. Quando vince il ramo NXR, l'enum diventa invece `STRAT_STRUCT_REACT` anche lì (riga 2321, `NXR_TriggerSignalFor(..., STRAT_STRUCT_REACT)`).
- **MALAYSIAN_SNR_BREAKOUT, MALAYSIAN_SNR_V2_RETEST, MALAYSIAN_SNR_V2_RETEST_OUTRANGE, MALAYSIAN_SNR_V2_STAGE1, MALAYSIAN_SNR_V2_STAGE3**: tutte `live_implementation=False`, `research_parity=NOT_IMPLEMENTED` nel registry — **nessun codice esiste per nessuna delle 5**. Non sono stage reali di una pipeline verificabile, sono placeholder.

**Classificazione:** MALAYSIAN_SNR = **SAME_COMPONENT** rispetto a `STRAT_STRUCT_REACT`/`NXS_Strat_StructureReaction` a livello di attribuzione (stesso enum, pur essendo concettualmente un fenomeno diverso — support/resistance a corpo, non reazione generica) — **CODE_VERIFIED**, e questa è la scoperta più sorprendente del cluster: **MALAYSIAN_SNR non ha mai avuto un proprio enum di attribuzione**, condivide quello di STRUCT_REACT fin dall'origine. Le 5 varianti = **UNKNOWN** (non implementate).

## Cluster 4 — TURTLE_SOUP + varianti

- **TURTLE_SOUP** (base, `NXS_Strategies_SMC.mqh:24`): consuma lo **stesso oggetto sweep condiviso** `SNXSSweepExt &sw` di LIQ_SWEEP (stesso motore upstream `NXS_DetectSweepExt`, confermando e risolvendo l'UNKNOWN lasciato aperto nell'audit precedente). Condizione aggiuntiva propria: candela di rejection ≥0.4×ATR che chiude oltre il livello swept. **Anche qui `s.strat = STRAT_STRUCT_REACT`** (riga 26) — non un enum TURTLE_SOUP o LIQUIDITY dedicato.
- **TURTLE_SOUP_CHOCH, TURTLE_SOUP_CHOCH_DBLBODY, TURTLE_SOUP_CHOCH_NEAR**: tutte `live_implementation=False`, `NOT_IMPLEMENTED` — nessun codice.

**Classificazione:** TURTLE_SOUP ↔ LIQ_SWEEP = **EXACT_SHARED_PRIMITIVE** per il componente upstream (`liquidity_sweep_detection`, stesso `sw`) + **VARIANT_OF_SAME_SETUP** per il trigger a valle (soglie/candela diverse) — **CODE_VERIFIED**. TURTLE_SOUP ↔ STRUCT_REACT (via `strat` enum) = **SAME_COMPONENT per attribuzione**, stesso pattern del Cluster 3 — **CODE_VERIFIED**. Le 3 varianti CHOCH = **UNKNOWN** (non implementate).

## Cluster 5 — MACD / MACD_SMA200

- **MACD** (`NXS_Strat_MACD`, riga 358): `g_macd`/`g_macdSig` (handle indicatore MACD EMA-based reale) + filtro `price > g_ema200`. `s.strat = STRAT_MACD` (enum proprio, corretto).
- **MACD_SMA200** (`NXS_Strat_MacdSma200`, riga 567): **ricostruisce un pseudo-MACD a mano con medie SMA** (fastMA-slowMA via `NXS_SMAv(12/26)`, non l'handle MACD reale), più un cross di histogram e un filtro SMA200 (non EMA200). Formula genuinamente diversa dalla vera MACD, stesso principio concettuale (cross momentum + filtro trend di lungo periodo). **`s.strat = STRAT_STRUCT_REACT`** (riga 568) — **non un enum legato a MACD, nonostante il nome**. Terza occorrenza dello stesso pattern di misattribuzione dei Cluster 3-4.

**Classificazione:** MACD ↔ MACD_SMA200 = **SAME_PHENOMENON_DIFFERENT_PROXY** (stesso principio — cross momentum + filtro trend lungo — formula e indicatore sottostante genuinamente diversi: EMA vs SMA a ogni stadio) — **CODE_VERIFIED**. Non è una duplicazione quasi esatta come ipotizzato nell'audit precedente: è un secondo proxy indipendente dello stesso fenomeno, non lo stesso componente rinominato — ma la sua attribuzione a `STRAT_STRUCT_REACT` lo rende comunque un rischio di misattribuzione, non di ridondanza di segnale.

## Cluster 6 — RSI_DIV / RSI_DIV_PINE

- **RSI_DIV** (riga 2026): divergenza su finestra fissa (barra 1 vs barra 8), soglia RSI<40/>60. Semplice, non basata su pivot confermati.
- **RSI_DIV_PINE** (riga 1979): divergenza basata su **pivot RSI confermati** (lookback/lookforward 1/3 barre, distanza 5-60 barre tra pivot), porting di un indicatore Pine Script pubblico — metodologia materialmente più rigorosa, non solo un parametro diverso.
- **Entrambe usano correttamente `s.strat = STRAT_RSI_DIV`** — **nessuna misattribuzione qui**, a differenza di tutti i cluster precedenti.

**Classificazione:** **SAME_PHENOMENON_DIFFERENT_PROXY** (stessa idea — divergenza RSI/prezzo — algoritmo di rilevamento genuinamente diverso, non un duplicato) — **CODE_VERIFIED**. Esempio pulito di come il sistema DOVREBBE taggare varianti dello stesso fenomeno — enum condiviso correttamente, nomi distinti, nessun bug di attribuzione.

## Cluster 7 — pattern generale _V2/_SCALP/_ACC

**Risultato netto, il più forte di questo intero audit:** per **tutti** gli strategy_id con suffisso _V2 o appartenenti alla famiglia SCALP controllati in questo task (ORDER_BLOCK_V2, FVG_CONT_V2, FVG_MIT_WINDOW — quest'ultimo in realtà implementato, vedi discrepanza sopra —, IFVG_CHOCH_WINDOW, MALAYSIAN_SNR_BREAKOUT, MALAYSIAN_SNR_V2_RETEST, MALAYSIAN_SNR_V2_RETEST_OUTRANGE, MALAYSIAN_SNR_V2_STAGE1, MALAYSIAN_SNR_V2_STAGE3, TURTLE_SOUP_CHOCH, TURTLE_SOUP_CHOCH_DBLBODY, TURTLE_SOUP_CHOCH_NEAR — 11 su 12 controllati): **`live_implementation=False` e `research_parity=NOT_IMPLEMENTED`**. Non sono varianti esecutive di un fenomeno già codificato — **sono voci di registry senza alcuna implementazione dietro**, in nessun linguaggio. L'unica eccezione verificata (FVG_MIT_WINDOW) è implementata ma il registry lo nega.

Questo non confuta l'ipotesi della famiglia SCALP come "gonfiamento del conteggio" — la **conferma con un meccanismo diverso e più semplice** da quello ipotizzato: non sono wrapper ridondanti di codice reale, sono **placeholder di pianificazione futura mai costruiti**, contati comunque negli 83 totali del registry.

---

## Tabella di sintesi

| Cluster | Relazione | Confidence | n strategy_id | n componenti canonici stimati dopo verifica |
|---|---|---|---|---|
| ORDER_BLOCK/OB_MIT/_V2 | SAME_COMPONENT (OB) + UNKNOWN (_V2) | CODE_VERIFIED / UNKNOWN | 3 | 1 reale + 1 non implementata |
| FVG_CONT/IFVG/FVG_MIT/FVG_MIT_WINDOW/_V2/_CHOCH_WINDOW/LIQ_VOID | VARIANT_OF_SAME_SETUP (4 reali) + SAME_PHENOMENON_DIFFERENT_PROXY (LIQ_VOID) + UNKNOWN (2 non implementate) | CODE_VERIFIED | 7 | 4 reali distinte (stesso enum) + 1 proxy dichiarato + 2 non implementate |
| MALAYSIAN_SNR + 5 varianti | SAME_COMPONENT (per attribuzione) + UNKNOWN (5 non implementate) | CODE_VERIFIED / UNKNOWN | 6 | 1 reale + 5 non implementate |
| TURTLE_SOUP + 3 varianti | EXACT_SHARED_PRIMITIVE (upstream con LIQ_SWEEP) + UNKNOWN (3 non implementate) | CODE_VERIFIED / UNKNOWN | 4 | 1 reale (upstream condiviso) + 3 non implementate |
| MACD/MACD_SMA200 | SAME_PHENOMENON_DIFFERENT_PROXY | CODE_VERIFIED | 2 | 2 reali, genuinamente distinte |
| RSI_DIV/RSI_DIV_PINE | SAME_PHENOMENON_DIFFERENT_PROXY | CODE_VERIFIED | 2 | 2 reali, genuinamente distinte |

**Totale controllato in questo task: 24 strategy_id.** Di questi, **13 non hanno alcuna implementazione** (né MQL5 né research) — sono voci di registry vuote. Degli **11 realmente implementati**, almeno **6** (OB_MIT, FVG_MIT, MALAYSIAN_SNR, TURTLE_SOUP, MACD_SMA200, e per attribuzione anche STRUCT_REACT stesso) condividono l'enum `STRAT_STRUCT_REACT` o `STRAT_ORDER_BLOCK`/`STRAT_FVG_CONT` con un'altra strategia nominalmente diversa.

## Stima aggiornata (solo sui cluster verificati qui — non estrapolata)

```
24 strategy_id controllati
  → 13 placeholder senza codice (nessun fenomeno, nessun componente)
  → 11 realmente implementati
      → almeno 4 enum di attribuzione condivisi tra fenomeni diversi
        (STRAT_ORDER_BLOCK: 2 consumer: ORDER_BLOCK, OB_MIT
         STRAT_FVG_CONT: 4 consumer: FVG_CONT, IFVG, FVG_MIT, FVG_MIT_WINDOW
         STRAT_STRUCT_REACT: almeno 4 consumer: STRUCT_REACT, MALAYSIAN_SNR, TURTLE_SOUP, MACD_SMA200
         STRAT_RSI_DIV: 2 consumer, correttamente — non un rischio)
      → 1 componente upstream condiviso non enum-correlato (liquidity sweep: LIQ_SWEEP + TURTLE_SOUP)
```

Non estendo questa proporzione (13/24 placeholder, condivisione pesante di enum tra i restanti) alle 76 strategie non controllate — ma è un segnale concreto, non più solo un'ipotesi di naming, che il conteggio "83 idee" è sovrastimato per almeno due meccanismi distinti e verificati: placeholder mai implementati, ed enum di attribuzione condivisi tra fenomeni nominalmente diversi.

## Addendum — verifica diretta del coordinatore (grep sistematico, chiude il primo gap residuo sopra)

Il fork che ha prodotto questo documento aveva esplicitamente lasciato aperto il gap "non verificato se altre strategie oltre a quelle elencate consumano `STRAT_STRUCT_REACT`". L'ho chiuso con un grep sistematico di `s.strat = STRAT_` su tutto `MQL5/Include/NEXUS_v1/` (non solo i 7 cluster prioritari): **il numero reale è ~32 `stratName` distinti che assegnano `STRAT_STRUCT_REACT`**, non "almeno 4" — inclusi molti strategy_id completamente fuori dai 7 cluster di questo task: BAR_UPDN, PMAX, PIVOT_WICK, 3COMMAS_BOT, ICHIMOKU_HULL_MACD, CRT, ELLIOTT, SWING_FALSEBREAK, SH_BMS_RTO, SH_BMS_RTO_V2 (×2 funzioni), SMS_BMS_RTO, SILVER_BULLET, AMD_REVERSAL, OTE_CONT, THREE_BAR_DELIVERY_BREAK, AMD_CONT, JUDAS_SWING, LDN_REVERSAL, NY_REVERSAL, WEEKLY_EXP, PO3, LIQ_VOID, DISP_REBAL, RANGE_FADE, LEVEL_CONFLUENCE, LEVEL_CONFLUENCE_M5, LEVEL_REACTION, LEVEL_REACTION_M5, WICK_SWEEP_REV — oltre a STRUCT_REACT/MALAYSIAN_SNR/TURTLE_SOUP/MACD_SMA200 già trovati dal fork. **CODE_VERIFIED, grep diretto, non estrapolazione.**

**Precisazione interpretativa necessaria, per non ripetere l'errore di overclaim già corretto altre volte in questa sessione:** condividere `s.strat` **non significa** che questi ~32 strategy_id calcolino la stessa evidenza di mercato. A differenza di ORDER_BLOCK/OB_MIT (stato di zona condiviso) e del cluster FVG (4 geometrie reali ma stesso fenomeno "fair value gap"), la maggioranza di questi 32 ha logica di detection genuinamente diversa e non correlata (es. BAR_UPDN è pattern OHLC puro, CRT è struttura dominata dai costi, JUDAS_SWING è logica di sessione — nessuna relazione di mercato tra loro). L'interpretazione più probabile, supportata da un commento reale nel codice ("v2.0.27 attribution fix", `NXS_ReusePerformancePack.mqh:2310`, che conferma un problema di attribuzione già affrontato almeno una volta per le varianti NXR): **l'enum `STRAT_*` non è stato esteso per ogni strategia aggiunta nelle fasi successive, e molte sono ricadute di default su `STRAT_STRUCT_REACT` come bucket generico** — un bug/gap di attribuzione per analytics/statistiche, confermato reale, ma **distinto** dal double-counting di evidenza di mercato che è il vero bersaglio architetturale di questo filone di lavoro. Entrambi i problemi sono reali; non vanno confusi tra loro.

**Impatto pratico non verificato in questo task (gap residuo, non risolto):** se qualche componente del sistema (dashboard, performance tracking, futuro aggregatore) calcola statistiche aggregate chiavate su `s.strat` invece di `s.stratName`, le statistiche di ~32 strategie nominalmente distinte verrebbero mescolate in un unico bucket — un rischio operativo concreto da verificare separatamente, non solo un dettaglio di naming.

**Nota di coerenza (aggiunta durante la chiusura della foundation, nessuna modifica alla conclusione):** il censimento sistematico completo in `STRATEGY_IDENTITY_ATTRIBUTION_PREAUDIT_V1.md` ha poi confermato il numero esatto: **34** (non "~32") `strategy_id` condividono `STRAT_STRUCT_REACT`, inclusi 2 nomi assenti dalla lista sopra (`WICK_SWEEP_RECLAIM`, oltre a quelli già elencati). Il "~32" qui resta corretto come stima approssimata dichiarata al momento — il numero preciso e la lista completa vivono nel documento successivo, non duplicati qui.

## Gap residui non risolti in questo task

- (Risolto dall'addendum sopra: l'estensione di `STRAT_STRUCT_REACT` oltre i 7 cluster è stata verificata con un grep completo.)
- Non letto il codice "base" morto di `NXS_Strat_OB_Mitigation_Structural`/`NXS_Strat_FVG_Mitigation` prima della macro-redirezione (restano nel file per compatibilità, mai eseguiti — non rilevante per il comportamento live, ma non ispezionato).
- Non verificato se `NXS_SelectorAllows` o altre logiche di selezione usano `s.strat` in modo che la condivisione di enum abbia un impatto diretto su quali segnali vengono effettivamente eseguiti (vs. solo su come vengono etichettati nei log/statistiche) — distinzione importante non risolta qui.

COMPONENT_COLLAPSE_HIGH_VALUE_VERIFICATION_V1_READY_FOR_REVIEW
