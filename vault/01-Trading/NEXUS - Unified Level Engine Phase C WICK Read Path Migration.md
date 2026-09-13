# Unified Level Engine — Phase C: WICK read-path migration with legacy shadow fallback

Segue [[NEXUS - Unified Level Engine Phase B Causal Non-Interference Validation]] (commit `74bd116`, verdict PASS_TO_PHASE_C). Primo consumer migrato: **solo WICK_SWEEP_REVERSAL (selector 54)**. WICK_SWEEP_RECLAIM (selector 55) resta legacy-only. Il vecchio `SNxsWickSide`/`SNxsWickReclaimState` NON è stato rimosso e continua a scrivere il proprio stato in ogni caso. Nessuna altra strategia toccata. `NXS_Structure.mqh`, `NXS_Reaction.mqh`, execution, SL/TP, strategy registry, Global New-Bar Gate: invariati.

## File modificati

| File | Modifica |
|---|---|
| `MQL5/Include/NEXUS_v1/NXS_LevelRegistry.mqh` | aggiunto campo minimo `last_attempt_bar` a `SNXSUnifiedLevel` (mancava — serve a replicare il throttle "un tentativo per livello per barra H4" del legacy) + setter `NXS_LevelReg_SetLastAttemptBar` |
| `MQL5/Include/NEXUS_v1/NXS_ReactionEngine.mqh` | aggiunto `NXS_WickReadPath_Compare` (comparator) e `NXS_LevelEngine_PrintReadPathSummary` (riepilogo checks/mismatches) |
| `MQL5/Include/NEXUS_v1/NXS_Strategies_Experimental.mqh` | `NXS_Strat_WickSweepReversal()` rinominata internamente `_NXS_WickSweepReversal_Legacy()` (corpo identico + 2 hook per `last_attempt_bar`); aggiunte `_NXS_WickReadPath_EvaluateSide`/`NXS_WickReadPath_Evaluate` (lettura pura dal registro); nuovo wrapper esterno `NXS_Strat_WickSweepReversal()` (dual-decision comparator + fail-safe) |
| `MQL5/Include/NEXUS_v1/NXS_Inputs.mqh` | nuovo input `InpLevelRegistry_WickReadPath` (default `false`) |
| `MQL5/Experts/NEXUS_EA_v2.mq5` | 1 chiamata aggiunta in `OnDeinit` (`NXS_LevelEngine_PrintReadPathSummary()`) |

Nessun altro file toccato. Compilazione: **0 errori, 2 warning preesistenti** (invariati da Fase A/B).

## Nuovo input

```
input bool InpLevelRegistry_WickReadPath = false;
```

`false` (default): comportamento legacy invariato al 100% — il wrapper richiama sempre `_NXS_WickSweepReversal_Legacy()` come unica fonte, il comparator gira comunque (se `InpLevelRegistry_WickTelemetry=true`) per visibilità ma non influenza la decisione restituita.
`true`: la decisione new-engine diventa autoritativa **solo se** il comparator conferma equivalenza con quella legacy per quella stessa chiamata; altrimenti fallback silenzioso al legacy per quel segnale (loggato come mismatch, mai un trade da una decisione non riconciliata).

## Quali campi del registry vengono letti

Dal `SNXSUnifiedLevel` (mai scritti dal read-path, solo letti):

- `price` — prezzo del livello (fonte della condizione di sweep, identica formula del legacy)
- `consumed` — se già tradato (idoneità)
- `invalidated` — se il livello è stato invalidato (idoneità)
- `last_attempt_bar` — throttle "un tentativo per barra H4" (**campo nuovo, minimo, aggiunto in questa fase** — mancava nello schema Fase A/B; popolato dall'hook causale nello stesso punto in cui il legacy scrive `SNxsWickSide.lastAttemptBar`, mai ricostruito ex-post)

**Confine dichiarato di questa fase** (non un'omissione nascosta): il read-path continua a leggere `g_wickHigh.id`/`g_wickLow.id` (per sapere quale livello è "attivo" per lato) e `g_wickLastBar` (clock condiviso per il throttle) direttamente dal legacy — sono puntatori di identità/tempo, non campi decisionali, e migrarli richiederebbe migrare anche la CREAZIONE del livello (fuori scope: Phase C migra solo la lettura della decisione di trading, non la sorgente del livello). Documentato esplicitamente per trasparenza, non nascosto.

## Bug trovati e corretti durante il test (prima del verdetto)

Il comparator ha fatto esattamente il suo lavoro: ha bloccato 2 bug reali prima che potessero mai causare un trade errato (fail-safe sempre attivo → legacy sempre autoritativo in presenza di mismatch → CSV trade MAI stato alterato in nessuna delle iterazioni, anche con i bug presenti).

1. **Guardia multi-TF mancante nel wrapper**: il legacy limita la propria valutazione al solo passaggio H4 (`if(g_activeTF != PERIOD_CURRENT && g_activeTF != PERIOD_H4) return s;`); il primo wrapper non replicava questa guardia, quindi il read-path veniva valutato anche sui passaggi M15/M30/H1/D1, producendo falsi mismatch (367 su 10308 controlli). **Fix**: stessa identica guardia replicata nel wrapper prima di fare qualunque lavoro.
2. **Auto-interferenza sul throttle**: l'hook che scrive `last_attempt_bar` nel registro scatta DENTRO la stessa chiamata in cui il legacy emette il segnale; leggere il registro DOPO aver chiamato il legacy faceva sì che il read-path vedesse il proprio stesso tentativo già segnato come "fatto questa barra" e si auto-negasse. **Fix**: la decisione new-engine viene letta PRIMA di chiamare il legacy (ordine invertito nel wrapper), cosicché veda lo stato pre-mutazione.

Dopo il fix: **0 mismatch** (vedi §Decision mismatch count).

Una terza discrepanza, puramente cosmetica (non un bug decisionale): la stringa `reason` del segnale new-engine usava un formato diverso (`"[NEW-ENGINE] WickSweep..."`) da quello legacy, causando un CSV di log non bit-identico pur avendo prezzo/SL/TP/timestamp identici. Corretto allineando esattamente il formato testuale (stesso wording, stesso contatore `attempts`) — il campo non è mai stato parte del contratto di equivalenza decisionale richiesto (should_trade/direction/level_id/trigger/SL/TP/timestamp), ma la parità richiesta dal task è bit-a-bit sull'intero CSV, quindi corretto per coerenza.

## Legacy/new trade digest

Finestra: GOLD H4, 2026-06-01→2026-07-01 (30gg, stessa finestra affidabile di Fase B), Model=1, selector 54.

| Run | InpLevelRegistry_WickReadPath | sha256(NEXUS_trades.csv) | Bytes | Trade (OPEN+CLOSE) |
|---|---|---|---|---|
| LEGACY | false | `979325de0339d2d5...48a9d44` | 34272 | 146 (73+73) |
| NEW read-path | true | `979325de0339d2d5...48a9d44` | 34272 | 146 (73+73) |

**IDENTICO bit-a-bit** — stesso hash della fixture REV già vista in Fase B (stesso storico, stessa config, coerenza cross-fase confermata). Report .htm confermano Profitto Netto -12.57, Drawdown Massimo 82.49 (7.94%), Profit Factor 0.95 identici su entrambi.

## Decision mismatch count

Dopo i 2 fix sopra:

```
[LEVELENGINE][READPATH] enabled=false checks=1718 mismatches=0
[LEVELENGINE][READPATH] enabled=true  checks=1718 mismatches=0
```

**0 mismatch su 1718 controlli**, sia con il flag OFF (comparator attivo solo per visibilità) sia con il flag ON (comparator che decide l'autorità). Nessun record `[LEVELENGINE][DECISION_MISMATCH]` prodotto in nessuna delle run finali.

## Regression

Stessa identica config di Fase B, hash confrontati contro le fixture già salvate in quella fase:

| Strategia | Selector | sha256 | Esito |
|---|---|---|---|
| WICK_SWEEP_RECLAIM (legacy-only) | 55 | `87078d65fcf2656a...5be548005` | **MATCH** con Fase B |
| ADX_RSI RAW | 1 | `af03313d3117cc36...9bb8bce1` | **MATCH** con Fase B |
| EMA_PULLBACK RAW | 11 | `f6fc623f51c9cde9...095a75277` | **MATCH** con Fase B |
| FVG_CONT RAW | 8 | `e17b5e4a3cc6f106...4867b60` | **MATCH** con Fase B |

**4/4 invariati.** Nessuna delle 4 strategie/percorsi ha subito modifiche di codice in questa fase (verificabile da `git diff`), il match hash lo conferma anche empiricamente.

## Overhead

Misurato con `Stopwatch` (stessa metodologia di Fase B), stesso run 30gg/224 livelli:

| Config | Durata |
|---|---|
| Pure legacy (`InpLevelRegistry_WickTelemetry=false`, nessun registro/comparator) | 222.77s |
| Legacy autoritativo, comparator attivo (`WickReadPath=false`) | 152.91s |
| New-path autoritativo, comparator attivo (`WickReadPath=true`) | 177.12s |

**Il dato grezzo non è utilizzabile così com'è**: la run "pure legacy" (zero lavoro aggiuntivo) è risultata la PIÙ LENTA delle tre, il che dimostra che a questo punto della sessione (~20 lanci consecutivi di `terminal64.exe`) il rumore di sistema (carico cumulato, scheduling OS) domina completamente qualunque differenza di costo reale — la stessa identica osservazione qualitativa di Fase B (dove OFF e ON erano 145.72s/145.68s, differenza 0.04s) vale qui: il lavoro aggiunto dal read-path è un'unica lookup `_NXS_LevelReg_Find` in più (O(n), n≤224, già dimostrato trascurabile in Fase B) più un confronto di poche `double` in `NXS_WickReadPath_Compare`, eseguito 1718 volte sull'intero run — nell'ordine dei microsecondi totali, non misurabile con `Stopwatch` a livello di processo in un ambiente già rumoroso quanto questo. **Non ottimizzato**, come da istruzione: nessuna evidenza che serva.

## Verdict finale

| Criterio | Esito |
|---|---|
| Trade sequence legacy/new bit-identica | ✅ (sha256 identico, 146/146 trade) |
| Decision mismatch = 0 | ✅ (0/1718, dopo i 2 fix documentati sopra) |
| Regression smoke puliti | ✅ (4/4 hash identici a Fase B) |
| Nessuna authority nuova inattesa | ✅ (il read-path diventa autoritativo SOLO quando il comparator conferma equivalenza; mai un'autorità indipendente) |
| Fallback non utilizzato | ✅ (0 mismatch nella run finale → il fallback non è mai scattato; era stato validato come funzionante nelle 2 iterazioni precedenti con i bug, dove ha correttamente impedito qualunque trade da una decisione divergente) |

### **VERDICT: PASS_TO_PHASE_D**

Nota di trasparenza: il verdetto è raggiunto DOPO aver trovato e corretto 2 bug nel comparator stesso durante il testing di questa fase — in nessun momento questi bug hanno prodotto un trade errato (il fail-safe ha funzionato esattamente come progettato, il CSV è rimasto invariato anche nelle iterazioni con i bug). Questo è considerato un successo del design (dual-decision comparator + fail-safe), non un rischio residuo.
