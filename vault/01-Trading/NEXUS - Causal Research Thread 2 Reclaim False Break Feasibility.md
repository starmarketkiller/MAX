# NEXUS Causal Research — Thread 2: Reclaim / False Break / Level Reaction (Feasibility)

Segue la chiusura del filone WICK Sweep v1 (commit `2abe922`, `LEVEL_AGE_REJECTED`). **Solo audit + design in questa nota — nessuna riga di codice modificata, nessun nuovo hook, nessun backtest completo, nessuna strategia.** Friday e Level Age non riaperti.

## 1. Source audit

| Sorgente | File | Stato attuale | Cosa produce |
|---|---|---|---|
| **Unified Level Registry** | `NXS_LevelRegistry.mqh` | Attivo, usato SOLO dalla famiglia WICK (selector 54 read-path, 55 shadow) | `SNXSUnifiedLevel` con lifecycle CREATED→FRESH→TOUCHED→SWEPT→RECLAIMED/INVALIDATED/CONSUMED, popolato da hook causali verificati (Fase A-D) |
| **Reaction Engine** | `NXS_ReactionEngine.mqh` | Attivo, stesso perimetro WICK | `SNXSReactionEvent` (CREATE/TOUCH/SWEEP/RECLAIM/INVALIDATE/CONSUME), log strutturato opzionale (`InpLevelRegistry_WickEventLog`) |
| **Legacy Structure** | `NXS_Structure.mqh` | Invariato da prima di dd22384, mai letto dall'Unified Engine | `g_struct`/`g_structH1`: trend, BOS, CHOCH (hysteresis, canonico); `g_levels[]`: pool swing+OB+FVG con 2-touch mitigation (`NXS_MitigateLevels`), **nessuna misura di profondità** |
| **Legacy Reaction** | `NXS_Reaction.mqh` | Invariato | `g_reaction`: quality score continuo 0-100 (mai discreto), consumato in 3 modi diversi (gate assoluto/gate doppio/modificatore) a seconda della strategia chiamante |
| **WICK_RECLAIM (selector 55)** | `NXS_Strategies_Experimental.mqh` | **Già pienamente strumentato nell'Unified Engine** (stesso perimetro WICK) | `SNxsWickReclaimState` (WR_IDLE→ARMED→RECLAIMED→OPENED) — sweep e reclaim del **trigger price**, non del livello grezzo. Eventi SWEEP/RECLAIM/INVALIDATE/CONSUME già loggati con `source_strategy="WICK_SWEEP_RECLAIM"` |
| **SH_BMS_RTO** | `NXS_Strategies_SMC.mqh:385-476` | Non strumentato | `ENUM_NXS_SHBMS_STATE{IDLE,SWEPT,WAITING_RETURN}` — sweep→MSS(displacement, soglia ATR)→retest a candela di rigetto. Nessun log persistente, stato locale per-call |
| **SH_BMS_RTO_V2** | `NXS_Strategies_SMC.mqh:497-556` | Non strumentato | Variante: zona `[sweepLevel..mssLevel]` invece di candela di rigetto per il retest — **geometria diversa dalla V1** |
| **SilverBullet** | `NXS_Strategies_SMC.mqh:645-726` | Non strumentato | `ENUM_NXS_SB_STATE{IDLE,SWEPT,WAITING_RETURN}` — sweep→FVG da displacement→retest del FVG, gate orario (killzone) |
| **SMS_BMS_RTO** | `NXS_Strategies_SMC.mqh` (righe ~583-636, da audit precedente) | Non strumentato | Labelling inline HH/LL/LH/HL (failure swing) + CHOCH (da `g_struct`) + candela di rigetto — **stateless**, nessuna persistenza |
| **IFVG** | `NXS_Strategies_SMC.mqh:166-192` | Non strumentato | Geometria FVG 3-candele, invalidazione esplicita "up/down" via CHOCH — concetto di **false break della propria zona**, non di un livello di struttura |
| **FVG_MIT_WINDOW** | `NXS_Strategies_SMC.mqh:251+` | Non strumentato | `SNXSFvgMitWZone{lo,hi,tBorn}` — pool con età (TTL 15 barre), retest+rigetto in altra funzione. Metadati minimi: **nessun touch_count, nessuna profondità, nessun reclaim_time** |
| **NXS_DetectSweepExt / SNXSSweepExt** | `NXS_MarketAnalysis.mqh:10-27,138` | Non strumentato, **ma il più riusato** (7 consumer: LIQ_SWEEP, SH_BMS_RTO, JUDAS_SWING, LDN_REVERSAL, PO3, AMD_REVERSAL, SILVER_BULLET) | Sweep di riferimenti di sessione/liquidità (PDH/PDL/PWH/PWL/PMH/PML/AsiaHigh/AsiaLow/EQH/EQL) con `levelTag` diagnostico — **stateless per chiamata**, nessuna identità di livello persistente (un PDH "nuovo" ogni giorno non ha un id proprio) |
| **NXS_DetectRegime** | `NXS_MarketAnalysis.mqh:29-41` | Non strumentato, calcolato ma non loggato | Classificazione regime (STRONG_TREND/WEAK_TREND/VOLATILE/RANGING/CHOPPY) da ADX+ATR — **candidato naturale per il campo "regime context"** richiesto, già causalmente disponibile ad ogni tick |
| **InstitutionalCore** | `NXS_InstitutionalCore.mqh` | Non strumentato | `g_ctx.structTrend/bosDir/sweepDir/zoneDir/reactionDir/chochDir` — **aggregatore** di stato esterno già calcolato altrove, non produce eventi propri |

## 2. Causal field matrix

Per famiglia di evento (colonne = classificazione: `AVAILABLE_NOW_CAUSAL` / `AVAILABLE_BUT_NOT_SNAPSHOTTED` / `REQUIRES_NEW_CAUSAL_HOOK` / `NOT_CAUSALLY_RECOVERABLE`):

| Campo | WICK (Unified Engine) | SH_BMS_RTO/V2, SilverBullet | LEVEL_REACTION (legacy) | SNXSSweepExt (PDH/PDL/…) |
|---|---|---|---|---|
| timestamp | AVAILABLE_NOW_CAUSAL | AVAILABLE_BUT_NOT_SNAPSHOTTED (calcolato ma non loggato) | AVAILABLE_BUT_NOT_SNAPSHOTTED | AVAILABLE_BUT_NOT_SNAPSHOTTED |
| level_id | AVAILABLE_NOW_CAUSAL | REQUIRES_NEW_CAUSAL_HOOK (nessuna identità persistente oggi — `sweepLevel` è un double, non un id) | REQUIRES_NEW_CAUSAL_HOOK (pool pivot ha slot ma senza id esposto esternamente, da verificare) | REQUIRES_NEW_CAUSAL_HOOK (PDH/PDL cambiano ogni giorno, serve un id tipo `data+tipo`) |
| source/source_tf | AVAILABLE_NOW_CAUSAL | AVAILABLE_BUT_NOT_SNAPSHOTTED (il TF è un parametro noto alla chiamata, solo non loggato) | AVAILABLE_BUT_NOT_SNAPSHOTTED | AVAILABLE_BUT_NOT_SNAPSHOTTED |
| side/direction | AVAILABLE_NOW_CAUSAL | AVAILABLE_BUT_NOT_SNAPSHOTTED | AVAILABLE_BUT_NOT_SNAPSHOTTED | AVAILABLE_BUT_NOT_SNAPSHOTTED (`SNXSSweepExt.dir`) |
| level price | AVAILABLE_NOW_CAUSAL | AVAILABLE_BUT_NOT_SNAPSHOTTED (`st.sweepLevel`) | AVAILABLE_BUT_NOT_SNAPSHOTTED | AVAILABLE_BUT_NOT_SNAPSHOTTED (`SNXSSweepExt.level`) |
| touch | AVAILABLE_NOW_CAUSAL (solo REV, mai chiamato dal path RECLAIM) | NOT_CAUSALLY_RECOVERABLE oggi (nessun concetto di "touch" prima dello sweep in questi state machine) | Parzialmente — dipende dal touchMode, da verificare nel dettaglio del codice | NOT_CAUSALLY_RECOVERABLE (stateless, nessun touch pre-sweep tracciato) |
| penetration | AVAILABLE_NOW_CAUSAL | REQUIRES_NEW_CAUSAL_HOOK (calcolabile da `close - sweepLevel` ma mai salvato) | AVAILABLE_BUT_NOT_SNAPSHOTTED (`breachPips` già calcolato internamente in alcuni rami, non loggato) | REQUIRES_NEW_CAUSAL_HOOK |
| sweep | AVAILABLE_NOW_CAUSAL | AVAILABLE_BUT_NOT_SNAPSHOTTED (`state==SWEPT`/`SHBMSV2_SWEPT`/`SB_SWEPT`) | AVAILABLE_BUT_NOT_SNAPSHOTTED | AVAILABLE_BUT_NOT_SNAPSHOTTED (`confirmed`) |
| reclaim | AVAILABLE_NOW_CAUSAL (**solo trigger, non livello grezzo** — vedi nota sotto) | NOT_CAUSALLY_RECOVERABLE come concetto esplicito (SH_BMS_RTO usa "MSS", non "reclaim" — semanticamente è più vicino a TRUE BREAK che a reclaim, vedi §3) | AVAILABLE_BUT_NOT_SNAPSHOTTED (sweepMode con chiusura di rientro) | N/A (il detector non ha nozione di reclaim) |
| break (vero) | NOT_CAUSALLY_RECOVERABLE per WICK (REV non aspetta mai una conferma di rottura, fa fade immediato) | AVAILABLE_BUT_NOT_SNAPSHOTTED — **MSS è letteralmente un evento di true break** (displacement oltre soglia ATR dopo lo sweep) | N/A | N/A |
| retest | NOT_CAUSALLY_RECOVERABLE per WICK (mai implementato) | AVAILABLE_BUT_NOT_SNAPSHOTTED — è il cuore della logica (`WAITING_RETURN`/zona `[sweepLevel..mssLevel]`) | N/A esplicito (il "pending" a N barre è concettualmente vicino ma non è un retest geometrico) | N/A |
| invalidation | AVAILABLE_NOW_CAUSAL | AVAILABLE_BUT_NOT_SNAPSHOTTED (`barsWaited > MaxBars` → torna IDLE; prezzo torna oltre `sweepLevel` → abort) | AVAILABLE_BUT_NOT_SNAPSHOTTED | N/A |
| age | AVAILABLE_NOW_CAUSAL (derivata) | REQUIRES_NEW_CAUSAL_HOOK (nessun `created_time` per il livello sweepato — è un prezzo, non un oggetto con storia) | Possibile via pool pivot (`createdAt`?) — da verificare, non confermato in questo audit | REQUIRES_NEW_CAUSAL_HOOK (PDH/PDL "nascono" a mezzanotte server, calcolabile ma non loggato) |
| regime/structure context | REQUIRES_NEW_CAUSAL_HOOK (mai letto da nessun hook Unified) | REQUIRES_NEW_CAUSAL_HOOK | REQUIRES_NEW_CAUSAL_HOOK | REQUIRES_NEW_CAUSAL_HOOK — ma la FONTE (`NXS_DetectRegime()`, `g_struct.trend`) è **già calcolata causalmente ad ogni tick**, solo mai salvata in un evento |

**Nota critica su "reclaim" per WICK_RECLAIM**: lo stato `RECLAIMED` tracciato oggi dall'Unified Engine per selector 55 è il reclaim del **trigger price** (il prezzo osservato al momento dello sweep), non del livello grezzo originale. Lo struct di shadow `SNxsWickShadowEvent` (mai wired nell'Unified Engine) distingue esplicitamente `reclaimed_trigger` da `reclaimed_level` — per il nuovo filone, se si vuole un concetto di "reclaim del livello" puro (più vicino alla definizione classica di false-break), serve o riusare quella distinzione shadow (già scritta, mai collegata al registry) o un hook nuovo dedicato.

## 3. Event lifecycle proposto (generalizzato oltre WICK)

```
CREATED
  → FRESH/UNTESTED
    → TOUCHED
      → SWEPT (penetrazione oltre soglia)
        → FALSE_BREAK  (= SWEPT poi RECLAIMED entro finestra — reclaim del livello, non solo del trigger)
        → TRUE_BREAK   (= SWEPT, MSS/displacement confermato, NESSUN reclaim entro finestra)
          → RETEST_OTHER_SIDE (prezzo torna a testare il livello rotto dal lato opposto)
            → RETEST_HOLD / RETEST_FAIL
      → INVALIDATED (mai swept, sostituito/scaduto)
```

Questo generalizza lo schema WICK (che si ferma a SWEPT→RECLAIMED/INVALIDATED/CONSUMED, senza mai un vero TRUE_BREAK né un RETEST) aggiungendo i due stadi che SH_BMS_RTO/SilverBullet già implementano operativamente (MSS≈TRUE_BREAK, WAITING_RETURN≈RETEST) ma non loggano in nessun registro persistente.

## 4. Population definitions (proposta)

**Population generale, indipendente dai filtri di strategia**:

> Tutti i livelli strutturali (di qualunque fonte: wick H4, pivot frattale, PDH/PDL/EQH/EQL, order block, FVG) che subiscono un **primo evento di sweep confermato** (penetrazione oltre una soglia dichiarata, misurabile in modo omogeneo — es. pip fissi o ATR-normalizzato) e per cui la finestra di osservazione successiva (barre M1 disponibili) permette di determinare causalmente se sia sopravvenuto un **reclaim** (ritorno del prezzo oltre il livello originale) entro un orizzonte temporale dichiarato PRIMA di guardare i dati.

Punti chiave (rispetto al filone WICK chiuso):
- **Non filtrata per strategia consumer** — un livello entra in population per il solo fatto di essere sweepato, indipendentemente da quale (o quante) strategie lo osservano poi.
- **Non filtrata per esito del trade legacy** — nessun trade deve necessariamente aprirsi perché un record entri nel dataset.
- **Sorgente-agnostica in linea di principio** — ma nella pratica, vedi §6, solo WICK ha oggi l'infrastruttura per produrre questa population senza nuovi hook.

## 5. Observation points (separazione obbligatoria)

### A) `AT_SWEEP_OR_BREAK`
Istante in cui il livello passa a `SWEPT`. Feature ammesse: tutto ciò che è vero A o PRIMA di questo istante (level_id, source, side, price, age, touch_count pre-sweep, penetration al momento dello sweep, regime/context al momento dello sweep). **Vietato**: qualunque campo che dipenda dal fatto che un reclaim avvenga o meno.

### B) `AT_RECLAIM`
Istante (se avviene) in cui il livello passa a `RECLAIMED`/`FALSE_BREAK`. Feature ammesse in aggiunta a quelle di (A): tempo trascorso da SWEPT a RECLAIM, massima penetrazione raggiunta PRIMA del reclaim (congelata, come già fa `SNxsWickShadowEvent.max_penetration_pips`), eventuale nuovo contesto di regime al momento del reclaim.

**Un modello che predice a `AT_SWEEP_OR_BREAK` non può mai usare feature disponibili solo a `AT_RECLAIM`** (violerebbe esattamente il tipo di leakage già verificato/escluso nei Thread 1). I due observation point producono due dataset separati, mai un solo dataset con colonne miste.

## 6. Outcome candidati (design, NON testati)

| Label | Entry reference | Horizon | Ambiguous/tie | Censored | Note bid/ask/spread |
|---|---|---|---|---|---|
| **+1R before −1R** | prezzo al momento dell'observation point (bid per SELL, ask per BUY, come nel Thread 1) | N barre M1 dichiarate a priori (es. equivalente a qualche giorno) o fino a fine dataset | stessa barra M1 tocca entrambe le soglie → escluso, non imputato (stessa regola Thread 1) | nessuna soglia toccata entro l'orizzonte → CENSORED, escluso | Nessuno spread modellato esplicitamente in Thread 1 (limite già noto, ereditato) — da dichiarare esplicitamente se il Thread 2 lo assume identico o lo migliora |
| **Continuation 1 ATR vs failure** | prezzo al momento dell'observation point | stesso principio, ma soglia = 1×ATR(H4) invece di 25 pip fissi — richiede ATR snapshottato causalmente (oggi REQUIRES_NEW_CAUSAL_HOOK) | stessa barra tocca sia +1ATR sia il livello di ritorno → escluso | idem | ATR va letto AL MOMENTO dell'evento, mai ricalcolato con dati successivi (stesso principio no-lookahead già applicato al Thread 1) |
| **Successful reclaim vs no reclaim** | N/A (è un evento binario, non un livello di prezzo) | finestra dichiarata a priori (es. N barre H4 dopo lo sweep) | N/A (evento binario, non c'è ambiguità di soglia — ma serve definire "reclaim" = tocco del livello o chiusura oltre il livello, DA DICHIARARE prima di misurare) | nessun reclaim entro la finestra E nessun TRUE_BREAK confermato → CENSORED (stato ancora indeterminato) | N/A |
| **Reclaim then +1R vs reclaim then failure** | prezzo al momento del reclaim (observation point B) | come "+1R before -1R" ma con orologio che riparte dal reclaim, non dallo sweep | stessa regola | stessa regola | Popolazione più piccola per costruzione (solo i livelli che arrivano a RECLAIMED) — vedi §7 per l'impatto sul campione |

## 7. Anti-leakage audit

Verificato esplicitamente (per costruzione, applicando la stessa disciplina già validata nel Thread 1):

- **Reclaim non è mai una feature nel dataset `AT_SWEEP_OR_BREAK`** — è per definizione un evento successivo, appartiene solo al dataset/label `AT_RECLAIM` o come outcome, mai come input al primo observation point.
- **Stato futuro del registry non va mai letto ex-post** — ogni feature deve provenire da uno hook che scrive il valore ESATTAMENTE all'istante dell'evento (stesso principio già applicato con successo a `touch_count_before_sweep` nel Thread 1, catturato al momento dello sweep e non a fine vita del livello).
- **Terminal state/MFE/MAE/exit reason/trade outcome**: esplicitamente esclusi da qualunque feature, per qualunque famiglia — stesso principio del Thread 1, qui riconfermato per le famiglie SH_BMS_RTO/SilverBullet dove esiste un vero "trade outcome" (a differenza di WICK dove l'esperimento usava un 1R sintetico indipendente dal trade legacy).
- **Campi mutabili**: `max_penetration`/`sweep_depth` vanno sempre congelati al PRIMO sweep osservato (già la convenzione dello schema Fase A) — se un futuro hook per SH_BMS_RTO/SilverBullet aggiunge penetrazione, deve seguire la stessa regola di congelamento, non una lettura "corrente" mutabile.

## 8. Sample feasibility (stima, non backtest completo)

| Famiglia | Fonte evidenza | Frequenza stimata | Affidabilità stima |
|---|---|---|---|
| **WICK sweep (REV)** | Dati reali Fase D/E (misurati) | ~75 sweep / 30gg → **~900/anno** | ALTA (misurato direttamente, più volte, su periodi diversi) |
| **WICK reclaim (RECLAIM, trigger)** | Dati reali Fase D (misurati: 30gg → armed=75, reclaim=56, opened=50) | ~56 reclaim / 30gg → **~670/anno** | ALTA (misurato direttamente) |
| **LEVEL_REACTION (pivot+SNR sweep/reclaim)** | Vault, nota "LEVEL_REACTION 3 Anni" (dati reali di trade, non di eventi grezzi) | **338 trade/3 mesi, 1833 trade/3 anni** ≈ 610/anno di TRADE (gli eventi sweep/reclaim grezzi sono più numerosi dei trade, poiché non ogni sweep supera la conferma a N barre) | MEDIA (trade reali noti, eventi grezzi sottostanti non contati direttamente — servirebbe instrumentazione per il numero esatto di sweep/reclaim, non solo dei trade risultanti) |
| **SH_BMS_RTO / V2 / SilverBullet** | Nessun dato di frequenza diretto trovato in questa sessione (nessun funnel esistente, nessuna nota vault con conteggio trovata) | Non quantificabile con certezza in questa fase — famiglia SMC/sessione tipicamente meno frequente delle famiglie a soglia fissa (killzone oraria per SilverBullet limita ulteriormente la finestra giornaliera) | **BASSA — richiede instrumentazione per una stima reale** |
| **SNXSSweepExt (PDH/PDL/EQH/EQL/Asia)** | Nessun dato diretto | Al massimo 1 evento/riferimento/giorno per tipo (10 tipi di riferimento) → limite teorico alto, ma `confirmed` richiede condizioni aggiuntive non quantificate qui | **BASSA — richiede instrumentazione** |

**Sintesi**: per un primo esperimento con campione già DIMOSTRATO adeguato senza bisogno di nuovi hook, la famiglia **WICK_RECLAIM (selector 55)** è pronta oggi (stessa infrastruttura del Thread 1, ~670 reclaim/anno). Per una popolazione più ricca strutturalmente (sweep→false-break/true-break→retest, non solo sweep→reclaim-del-trigger), **SH_BMS_RTO/SilverBullet** sono i candidati concettualmente più interessanti ma richiedono instrumentazione prima di poter anche solo stimare con certezza il campione.

## 9. Missing hooks (identificati, NON implementati)

1. **Identità di livello persistente per SH_BMS_RTO/V2/SilverBullet/SNXSSweepExt** — oggi questi detector sono stateless o quasi (un prezzo, non un oggetto con id/storia). Serve un `level_id` per poter costruire un dataset a un-record-per-livello come fatto per WICK.
2. **Snapshot di penetrazione/età al momento dello sweep** per tutte le famiglie non-WICK.
3. **Evento TRUE_BREAK esplicito** — oggi "MSS" (SH_BMS_RTO) è concettualmente un true break ma non è mai loggato con questa semantica in un registro condiviso.
4. **Evento RETEST esplicito** — `WAITING_RETURN`/zona `[sweepLevel..mssLevel]` esistono nel codice ma non producono un evento di lifecycle registrato.
5. **Distinzione reclaim-del-trigger vs reclaim-del-livello** per WICK_RECLAIM — la logica shadow (`SNxsWickShadowEvent.reclaimed_level`) esiste già scritta ma non è collegata all'Unified Engine.
6. **Snapshot di regime/contesto** (`NXS_DetectRegime()`, `g_struct.trend`) in qualunque evento — calcolo già disponibile, mai loggato da nessun hook esistente.

Nessuno di questi è stato implementato in questa fase, come richiesto.

## 10. Raccomandazione per il primo esperimento

**Non ancora un nuovo esperimento su una famiglia nuova.** Due percorsi ragionevoli, in ordine di prontezza:

- **Percorso A (zero nuovi hook, dati già disponibili)**: un esperimento discovery su **WICK_RECLAIM (selector 55)** usando la distinzione già presente nello schema Unified (SWEPT→RECLAIMED→CONSUMED) con outcome "successful reclaim vs no reclaim" e "reclaim then +1R vs reclaim then failure" (candidati 3 e 4 di §6) — campione stimato ~670/anno, sufficiente. Limite: il "reclaim" qui è del trigger price, non del livello grezzo (vedi nota critica §2) — da dichiarare esplicitamente se si procede.
- **Percorso B (richiede hook nuovi, popolazione più ricca)**: instrumentare **SH_BMS_RTO/SilverBullet** con gli hook di missing-hook §9 (level_id, penetrazione, TRUE_BREAK, RETEST espliciti) per ottenere il lifecycle completo sweep→false-break/true-break→retest richiesto dal task — più fedele all'obiettivo dichiarato del nuovo filone, ma richiede lavoro di implementazione non ancora autorizzato in questa fase.

## Verdict

### **HOLD_NEEDS_CAUSAL_HOOKS**

Motivazione: la population "generale, non legata ai filtri della vecchia strategia" richiesta dal task (sweep/false-break/true-break/retest attraverso più fonti strutturali) **non è oggi interamente disponibile senza nuovi hook** — solo la sotto-fetta WICK_RECLAIM lo è. Le famiglie concettualmente più ricche e allineate all'obiettivo del thread (SH_BMS_RTO, SilverBullet, SNXSSweepExt) mancano di identità di livello persistente, snapshot di penetrazione/età, ed eventi TRUE_BREAK/RETEST espliciti — tutti classificati `REQUIRES_NEW_CAUSAL_HOOK` in questo audit, non implementati come da istruzione. Un esperimento limitato al solo WICK_RECLAIM sarebbe eseguibile subito (Percorso A) ma non soddisferebbe l'ambizione dichiarata di "eventi di livello più ricchi strutturalmente" — la raccomandazione è di autorizzare l'instrumentazione minima del Percorso B prima di procedere con un esperimento su questo thread.
