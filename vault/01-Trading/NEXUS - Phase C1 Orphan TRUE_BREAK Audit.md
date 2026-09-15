# NEXUS Phase C.1 — Orphan TRUE_BREAK Root-Cause Audit

Segue [[NEXUS - Structural Lifecycle Sample Recovery]] (commit `3c1c296`, episodeSeq additivo, sample recovery 60→159, 288 orphan TRUE_BREAK riportati e correttamente esclusi ma non spiegati in dettaglio). Questa fase chiude definitivamente la causa degli orphan **prima** di aprire nuovi thread di ricerca. Nessuna feature discovery, nessuna analisi dei 6 WEAK_HINT, nessuna modifica alla trading logic.

## 1. Conteggio esatto — 283 vs 288

**288 è il numero corretto.** Verificato contando direttamente la lista di righe orphan TRUE_BREAK (una riga = un evento, mai deduplicato): `len(tb_orphans) == 288`.

Il **283** stampato a console da `causal_thread3_true_break_quality.py` era un artefatto cosmetico di UNA sola riga diagnostica: `orphan_true_break_ids = set(e["event_id"] for e in true_orphans if ...)` costruiva un `set` sul solo `event_id`, senza `window_id`. `event_id` riparte da 1 a ogni run/finestra separata del Tester (causa già nota e già corretta ovunque nel resto del codice — vedi Structural Causal Experiment 1 — ma **non** in questa singola riga di stampa). 5 coppie di orphan TRUE_BREAK di finestre diverse condividono per coincidenza lo stesso `event_id` (`1164`, `1622`, `786`, `979`, `1804`), collassando 288→283 nel solo conteggio stampato. **La popolazione/esclusione effettiva non era mai stata affetta** — solo questa riga di diagnostica testuale. Corretto nel codice (chiave `(window_id, event_id)`, stesso pattern usato ovunque altrove).

## 2-3. Test delle due ipotesi + attribution

### Round 1 — stima euristica (post-hoc, senza strumentazione causale)

Prima di aggiungere qualunque strumentazione nuova, ho testato le due ipotesi ricostruendo a posteriori, per ogni orphan, la riga SWEEP più vicina (per `event_id`) sullo stesso `structural_level_id`:

| | n | % |
|---|---|---|
| Ipotesi B (riga più vicina ha già un `sh_bms_episode_seq` diverso e non-zero) | 247 | 85.8% |
| Ipotesi A (nessuna riga con seq già occupato nelle vicinanze) | 41 | 14.2% |

Ho escluso l'ipotesi "cold-start di finestra" per i 41 casi A: distribuiti su tutta la durata delle finestre (giorno 2→116 dall'inizio), non concentrati all'apertura.

**Questa stima si è rivelata imprecisa** (vedi §Round 2) — è il motivo esatto per cui l'istruzione di "causal integrity" (non ricostruire con euristiche a posteriori) è corretta: la ricostruzione post-hoc non può sapere con certezza quale fosse il vero bar canonico di un episodio mai loggato.

### Round 2 — verità causale (`episode_sweep_link`, scritta nell'istante della transizione)

Implementata la mappa additiva `episode_sweep_link` (§4) e ricollezionate le 6 finestre. Risultato definitivo, verificato sul dato reale (12.219 righe di link, 6 finestre):

| attach_result | n righe (tutte le osservazioni SH_BMS_RTO) |
|---|---|
| ATTACHED_EXISTING | 12.219 (100%) |
| NEW_CANONICAL | 0 |
| MALFORMED_SKIPPED | 0 |

**Zero casi di MALFORMED_SKIPPED osservati in pratica.** Spiegazione architetturale: il hook canonico "DETECTOR" (fonte condivisa, Fase A.1) viene chiamato **prima** di `NXS_Strategies_SMC.mqh` all'interno dello stesso pass (`NXS_CollectAllSignals` → hook centrale poi `NXS_CollectRaw`), quindi quando SH_BMS_RTO ingaggia lo stesso `sw` pochi istanti dopo, nello stesso pass, la riga canonica esiste **già sempre** (creata da DETECTOR) — SH_BMS_RTO non è mai il primo osservatore. Questo spiega sia zero NEW_CANONICAL sia zero MALFORMED_SKIPPED per SH_BMS_RTO: se `sw` fosse stato malformato, DETECTOR lo avrebbe già scartato pochi istanti prima con lo stesso identico `sw`.

**Attribution finale dei 288 orphan originali (verità causale, non ricostruita):**

| Categoria | n | % |
|---|---|---|
| CANONICAL_DEDUP_EPISODE_COLLISION_RESOLVED | 288 | 100% |
| MALFORMED_SWEEP_NOT_LOGGED | 0 | 0% |
| MISSING_OBSERVER_CALL | 0 | 0% |
| WINDOW_BOUNDARY | 0 | 0% |
| OTHER_EXPLAINED | 0 | 0% |
| **UNEXPLAINED** | **0** | **0%** |

**Acceptance soddisfatta: UNEXPLAINED = 0.**

La stima euristica del Round 1 (85.8% B / 14.2% A) è quindi **superata e corretta** da questo risultato: la causa è **100% Ipotesi B** (collisione canonical-dedup vs episodeSeq), zero Ipotesi A osservata in questo dataset. I 41 casi "candidati A" del Round 1 erano falsi positivi della ricostruzione euristica (la riga canonica vera non era la "più vicina per `event_id`" — coerente con quanto già osservato in Phase C: l'ordine di creazione delle righe SWEEP non segue l'ordine di `episodeSeq`).

## 4. Mapping causale — `episode_sweep_link`

**Non tocca la canonicalizzazione**: un solo evento SWEEP per `(structural_level_id, bar)` resta invariato. Aggiunge una struttura research-only separata che permette la relazione **molti `episodeSeq` → un `canonical_event_id`**:

```mql5
struct SNXSEpisodeSweepLink {
   string   direction;             // NXS_DirName(sw.dir) - sempre valido (BUY/SELL)
   int      episode_seq;
   string   structural_level_id;
   long     canonical_event_id;    // 0 = nessuna riga prodotta (MALFORMED_SKIPPED)
   string   attach_result;         // NEW_CANONICAL | ATTACHED_EXISTING | MALFORMED_SKIPPED
   datetime timestamp;
};
```

Scritta nei **3 punti di uscita già esistenti** di `NXS_Structural_ObserveSweep` (mai un punto nuovo, mai un ramo nuovo di logica):

```mql5
if(sw.dir == DIR_NONE || sw.levelTag == "" || sw.level <= 0){
   g_nxsSweepMalformedSkipped++;
   if(episodeSeq != 0)
      _NXS_EpisodeLink_Record(NXS_DirName(sw.dir), episodeSeq, outLevelId, 0, "MALFORMED_SKIPPED", iTime(g_sym, tf, 0));
   return;
}
...
if(idx >= 0){
   ...
   if(episodeSeq != 0)
      _NXS_EpisodeLink_Record(NXS_DirName(sw.dir), episodeSeq, outLevelId,
                               g_nxsStructEvents[idx].event_id, "ATTACHED_EXISTING", obsTime);
   ...
}
// nuovo evento canonico
...
if(episodeSeq != 0)
   _NXS_EpisodeLink_Record(NXS_DirName(sw.dir), episodeSeq, outLevelId, ev.event_id, "NEW_CANONICAL", obsTime);
```

**`NXS_Strategies_SMC.mqh` non è stato toccato in questa fase** — nessuna modifica alla state machine, nessun rischio aggiuntivo lato trading. Export in `nxs_episode_sweep_link.csv` (nuova chiamata `NXS_EpisodeLink_ExportCSV()` in `OnDeinit`, additiva, gated da `InpStructuralResearchEventLog`).

Lato Python: `assign_episodes_v3()` in `build_structural_dataset_v1.py` usa questa mappa come fonte autorevole per risolvere `episodio → riga SWEEP canonica`, sostituendo la dipendenza dal singolo campo `sh_bms_episode_seq` sulla riga (che può contenere un solo valore — la causa stessa della collisione).

## 5. Causal integrity

Verificato nel codice: `_NXS_EpisodeLink_Record(...)` è chiamata **solo ed esclusivamente** dall'interno di `NXS_Structural_ObserveSweep`, che a sua volta è chiamata in modo sincrono da `NXS_SHBMS_UpdateSide` **esattamente** nel ramo IDLE→SWEPT, nello stesso istante in cui `st.episodeSeq++` avviene. Nessun nearest-timestamp, nessun nearest-level, nessuna euristica: il link è scritto con l'informazione già in scope in quell'istante (`sw`, `tf`, `episodeSeq`, `outLevelId`), mai ricostruito dopo.

## 6. Regression

| Run | Trade | SHA256 |
|---|---|---|
| Baseline | 104 | `cb25cc93d10a4662ecdb9f800f03f3cc7ab15200681071f486b52e0fd0397094` |
| OFF (con `episode_sweep_link`) | 104 | `cb25cc93d10a4662ecdb9f800f03f3cc7ab15200681071f486b52e0fd0397094` |
| ON (con `episode_sweep_link`) | 104 | `cb25cc93d10a4662ecdb9f800f03f3cc7ab15200681071f486b52e0fd0397094` |

**Stessi trade, stesso digest.** Nessuna modifica al codice MQL5 dopo questa verifica (confermato via `git diff` prima della raccolta finale) — parità garantita per l'intera raccolta.

## 7. Rebuild population — PRE (v2) vs POST (v3)

Stesse 6 finestre, stesso R/orizzonte, stessa policy di esclusione post-close di `causal_thread3_true_break_quality.py` (isolato in uno script di audit dedicato, `phase_c1_orphan_audit.py`, che **non** esegue discovery).

| | PRE (v2, commit `3c1c296`) | POST (v3, `episode_sweep_link`) |
|---|---|---|
| Orphan TRUE_BREAK | 288 | **0** |
| Esclusioni post-close/redundant | 0 | 0 |
| TRUE_BREAK validi | 270 | **558** |
| AMBIGUOUS_SAME_BAR | 111 (41.1%) | 214 (38.4%) |
| CENSORED | 0 | 0 |
| **RISOLTI** | **159** | **344** |

Non è stato necessario né ricercato un aumento del campione — è la conseguenza diretta e corretta di non scartare più episodi reali che condividono un bar canonico con un altro episodio. L'obiettivo era correttezza, non quantità.

## 8. Impatto sui 159 outcome — Thread 3 provvisorio

**Population NON identica bit-for-bit.** Confronto per `(window_id, true_break_event_id, esito)`:
- Rimossi rispetto a v2: **0** (tutti i 159 originali restano, invariati, con lo stesso esito).
- Aggiunti rispetto a v2: **185** (episodi prima orphan, ora correttamente linkati e risolti).

Poiché la population cambia, **il precedente verdict Thread 3 (`NO_PROMISING_HYPOTHESIS`, ottenuto automaticamente durante la validazione di Phase C) è da considerarsi provvisorio** e va rieseguito come thread separato con la population v3 (344 risolti), non in questa fase — nessuna discovery multivariata è stata eseguita qui, per istruzione esplicita.

## Verdict

### **ORPHAN_ROOT_CAUSE_FULLY_EXPLAINED**

- Orphan esatti: **288** (283 era un bug cosmetico di conteggio, ora corretto).
- Attribution: **100% CANONICAL_DEDUP_EPISODE_COLLISION** (verità causale via `episode_sweep_link`) — 0% Ipotesi A, 0% UNEXPLAINED.
- Fix: mapping additivo `episode_sweep_link`, causale, scritto nell'istante della transizione — nessuna duplicazione della canonicalizzazione, `NXS_Strategies_SMC.mqh` non toccato.
- Trading parity: confermata (104/104, stesso SHA256, OFF e ON).
- Population: 270→558 TRUE_BREAK validi, 159→344 risolti, 0 rimossi, 185 aggiunti.
- Thread 3: verdict precedente **provvisorio**, da rieseguire come thread separato (fuori scope qui).
- Commit: da eseguire subito dopo questo report (fix validato).
