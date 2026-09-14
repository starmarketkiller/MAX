# NEXUS Structural Dataset v1 — Causal Linkage Integrity Audit

> ⚠️ **Correzione post-commit (`ea3fb14` → vedi [[NEXUS - Structural Causal Experiment 1]])**: il CSV committato con questo report conteneva un secondo bug, indipendente dal linkage per episodio descritto sotto: `event_id` **non è univoco fra finestre diverse** (ogni run separata del Tester riparte da 1 — 2108/2382 valori di `event_id` risultavano condivisi da tutte e 4 le finestre). `build_episode_lifecycle_index()` indicizzava gli eventi lifecycle SOLO per `event_id`, causando collisioni cross-finestra che corrompevano i valori dei label in `at_sweep.csv`/`at_true_break.csv` (in particolare `w1` risultava quasi azzerata). La regola di linkage per episodio descritta in questo report resta corretta nella sua logica; l'implementazione è stata corretta indicizzando per `(window_id, event_id)`. I CSV in `results/structural_dataset_v1/` sono stati ri-rigenerati. Vedi l'esperimento collegato per i numeri corretti.

Segue [[NEXUS - Structural Dataset v1]] (commit `ac77d36`, verdict precedente `READY_FOR_STRUCTURAL_CAUSAL_EXPERIMENT` **non approvato** in revisione). Questo audit sostituisce il linkage lifecycle della v1 con una regola deterministica basata su identità di episodio, corregge un bug reale trovato (`sweep_event_id` vuoto), rinomina un label semanticamente scorretto e rimuove un campo temporale causalmente inaffidabile.

**Nessuna nuova run del Tester eseguita** — stesso `structural_events_w{1..4}.csv`/`nxs_m1_struct_w{1..4}.csv` raccolti per la v1, solo il dataset builder (`build_structural_dataset_v1.py`) è stato riscritto.

## 1. Causa dei 48 casi originali

`structural_level_id` (es. `Asia-High_2026.01.23`) identifica un **livello di prezzo** (tag + data), non un singolo episodio: lo stesso livello può essere sweepato, invalidato e ri-sweepato più volte nella stessa finestra, e la fonte SWEEP condivisa (Fase A.1) può emettere **più righe SWEEP consecutive per lo stesso episodio** quando `sw.confirmed` resta vero su barre successive (osservate solo da `DETECTOR`, perché SH_BMS_RTO è già uscito da `IDLE`). Il builder v1 collegava lifecycle a livello di `structural_level_id` intero (min/max timestamp su tutto il gruppo), ignorando quale SWEEP appartenesse a quale episodio — da cui sia i falsi ordinamenti "impossibili" sia (scoperto in questa revisione) `sweep_event_id` vuoti quando il timestamp del TRUE_BREAK (bar-anchor D1, sempre mezzanotte) risultava più piccolo del timestamp del vero SWEEP (bar-anchor H4, es. le 20:00 dello stesso giorno) — il filtro `timestamp <= true_break.timestamp` non trovava nessun candidato.

## 2. Causa degli 11 casi non risolti da event_id (v1)

Verificato con il caso esemplare `Asia-High_2026.01.23`/w1 (`structural_events.csv`, event_id 748-758):

```
748 SWEEP      observed_by=,DETECTOR,SH_BMS_RTO,   <- apre episodio 1
751 INVALIDATE observed_by=,SH_BMS_RTO,            <- chiude episodio 1
753 INVALIDATE observed_by=,SH_BMS_RTO,            <- NESSUNO SWEEP fra 751 e 753!
754 SWEEP      observed_by=,DETECTOR,SH_BMS_RTO,   <- apre episodio 2
755 SWEEP      observed_by=,DETECTOR,SH_BMS_RTO,   <- apre episodio 3 (chiude implicitamente il 2)
756 TRUE_BREAK observed_by=,SH_BMS_RTO,            <- appartiene all'episodio 3 (755), non al 748
757 INVALIDATE observed_by=,SH_BMS_RTO,            <- chiude episodio 3
758 INVALIDATE observed_by=,SH_BMS_RTO,            <- ridondante, nessuno SWEEP dopo 757
```

Il pattern "due INVALIDATE consecutivi senza uno SWEEP in mezzo" (751→753, 757→758) e "due SWEEP consecutivi entrambi osservati da SH_BMS_RTO senza una chiusura esplicita in mezzo" (754→755) sono entrambi artefatti del loop multi-TF-pass di `NXS_CollectAllSignals`: `g_shbmsBuy`/`g_shbmsSell` sono stato **condiviso** fra pass con `tf` diversi nello stesso tick reale, quindi la stessa transizione di stato può essere osservata/rivalutata più volte con bar-anchor diversi. Gli 11 casi non risolti da un semplice riordino per `event_id` a livello di `structural_level_id` erano gruppi con **più di un episodio** in cui il riordino ingenuo non bastava a capire quale SWEEP appartenesse a quale TRUE_BREAK — esattamente il problema che l'identità di episodio (§3) risolve.

## 3. Episode-linking rule (deterministica, mai nearest-timestamp)

Implementata in `assign_episodes()` (`build_structural_dataset_v1.py`), **solo in ordine di `event_id`** (mai per timestamp, mai pairing post-hoc per vicinanza):

1. Una riga SWEEP apre un **nuovo** `structural_episode_id` (`{structural_level_id}__ep{n}`) **solo se** `"SH_BMS_RTO"` compare nel suo `observed_by` — prova diretta, presente nei dati stessi, che lo stato di SH_BMS_RTO era `IDLE` in quel preciso momento di elaborazione (precondizione hardcoded nel suo codice per osservare un nuovo sweep). Una riga SWEEP osservata solo da `DETECTOR` riceve comunque un proprio `structural_episode_id` (resta popolazione valida in `at_sweep.csv`) ma non diventa mai bersaglio di lifecycle.
2. TRUE_BREAK/RETEST/INVALIDATE (prodotti solo da SH_BMS_RTO) si agganciano **sempre** all'ultimo episodio SH_BMS_RTO aperto fino a quel punto in ordine di `event_id` ("last_episode"). Se nessun episodio è mai stato aperto prima → **vero orphan**, mai agganciato per timestamp vicino (vedi §4).
3. RETEST/INVALIDATE chiudono l'episodio. TRUE_BREAK non chiude. Un evento lifecycle che arriva quando l'episodio è già chiuso resta agganciato all'ultimo episodio ma è marcato `redundant_after_close` (mai ignorato silenziosamente, mai riassegnato altrove).
4. Un nuovo SWEEP SH_BMS_RTO chiude **implicitamente** l'episodio precedente se ancora aperto (`closed_by="IMPLICIT_NEXT_SWEEP"`) — la sola esistenza di una nuova osservazione IDLE→SWEPT è prova che l'episodio precedente è terminato nella realtà, con o senza una riga di chiusura esplicita nel log.

Per costruzione, un evento lifecycle non può mai agganciarsi a un episodio con `event_id` maggiore del proprio (si aggancia sempre all'ULTIMO aperto PRIMA di esso in ordine di elaborazione) — l'ordine impossibile è strutturalmente escluso, non solo verificato a posteriori.

## 4. Orphan audit — prima/dopo

| | v1 (bug) | v2 (questo audit) |
|---|---|---|
| `at_true_break.csv` con `sweep_event_id` vuoto | **≥1 (bug confermato)** | **0/269** |
| Orphan TRUE_BREAK (nessun episodio aperto) | non misurato esplicitamente | **0** |
| Orphan RETEST (nessun episodio aperto) | non misurato esplicitamente | **0** |
| Orphan INVALIDATE (nessun episodio aperto) | non misurato esplicitamente | **0** |
| Impossible lifecycle order (verificato indipendentemente: `sweep_event_id >= true_break_event_id`) | 48/1989 gruppi (livello, non episodio) | **0/269** (verificato con script indipendente separato dal builder) |

Il bug `sweep_event_id` vuoto segnalato: causato esattamente dal meccanismo del §1 — un TRUE_BREAK con timestamp bar-anchor D1 (mezzanotte) confrontato con `<=` contro il timestamp bar-anchor H4 (es. 20:00) del vero SWEEP falliva il filtro. Risolto eliminando ogni confronto per timestamp nel linkage.

## 5. `time_to_true_break_sec` — rimosso

Rimosso da `at_true_break.csv`. Motivo: il campo `timestamp` di ogni evento è il bar-open del TF che ha innescato quella specifica transizione (D1/H4/H1/M15 a seconda del pass) — non un orologio uniforme fra eventi collegati dello stesso episodio se innescati da pass diversi (dimostrato empiricamente nel caso `Asia-High_2026.01.23`, dove il TRUE_BREAK del pass D1 mostra `00:00:00` mentre il suo SWEEP del pass H4 mostra `21:00:00` lo stesso giorno). `event_id` stabilisce correttamente l'**ordine** causale ma non rappresenta secondi — **nessuna conversione event_id→tempo è stata eseguita**, come esplicitamente richiesto. Il campo `episode_linkage_rule`/`time_to_true_break_removed_reason` in `metadata.json` documenta questa scelta. Ricostruirlo correttamente richiederebbe una nuova istrumentazione (un campo "real tick time" indipendente dal bar-anchor) — fuori scope per questo audit, candidato per una fase futura.

## 6. Label rinominati

`label_reclaim_or_false_break` (v1) → **`label_lifecycle_outcome`** (v2), con categorie rinominate per riflettere solo ciò che è realmente registrato nell'instrumentation (nessun evento `RECLAIM` esiste in `NXS_StructuralResearchLog.mqh` — mai inventato):

| Categoria v1 (v1, scorretta) | Categoria v2 (corretta) | Definizione causale |
|---|---|---|
| `TRUE_BREAK` | `TRUE_BREAK_OBSERVED` | l'episodio ha un evento TRUE_BREAK |
| `RECLAIM` | `INVALIDATED_NO_BREAK` | l'episodio ha un INVALIDATE con `state_before=="SWEPT"` (invalidato prima di qualunque MSS/displacement), nessun TRUE_BREAK |
| `NO_LIFECYCLE` | `NO_LIFECYCLE_OBSERVED` | nessun evento lifecycle agganciato a questo episodio/sweep (censura implicita: SH_BMS_RTO non lo tracciava, o l'episodio è terminato solo per chiusura implicita senza un INVALIDATE esplicito) |

**Effetto della correzione del linkage su questo label** (conseguenza diretta del passaggio da scope-livello a scope-episodio, non un secondo bug separato): `TRUE_BREAK_OBSERVED` scende da 789 (19.5%, v1, sovrastimato per leakage fra episodi diversi dello stesso livello) a **47 (1.16%, v2, corretto)** — la v1 attribuiva a OGNI sweep di un livello il TRUE_BREAK di QUALUNQUE episodio di quel livello, anche episodi diversi e temporalmente distanti.

## 7. Rebuild — row count finali

| File | Righe (invariato nel totale grezzo, cambia solo il linkage/i label) |
|---|---|
| `structural_events.csv` | 8118 (+ colonna `structural_episode_id`) |
| `at_sweep.csv` | 4045 |
| `at_true_break.csv` | 269 |

Nuove metriche episodio (in `metadata.json`):

| Metrica | Valore |
|---|---|
| `unique_structural_episodes` | **2411** |
| `episodes_closed_explicit` (RETEST/INVALIDATE osservato) | 1968 |
| `episodes_closed_implicit_next_sweep` | 410 |
| `episodes_open_at_window_end` (right-censored) | 33 |
| `lifecycle_redundant_after_close` (evento arrivato dopo chiusura, riassegnato all'ultimo episodio noto, mai scartato) | 1934 |
| `true_break_after_close` (sottoinsieme di cui sopra, specificamente TRUE_BREAK) | 98 |

## 8. Data quality — acceptance

| Criterio | Esito |
|---|---|
| 0 ambiguous episode linkage | ✅ (regola deterministica, un solo candidato possibile per costruzione) |
| 0 orphan TRUE_BREAK | ✅ |
| 0 orphan RETEST | ✅ |
| 0 impossible lifecycle order | ✅ (verificato con script indipendente: 0/269) |
| Nessun `time_to_true_break_sec` causalmente falso | ✅ (campo rimosso) |
| Label names semanticamente corretti | ✅ (`label_lifecycle_outcome`, categorie derivate solo da campi realmente registrati) |
| Duplicate keys / malformed | ✅ 0 (invariato dalla v1) |

## 9. Blockers

Nessuno. Limite dichiarato: 1934 eventi lifecycle "ridondanti dopo chiusura" e 410 chiusure solo implicite riflettono un artefatto noto e pre-esistente (desync di stato condiviso fra pass multi-TF di `NXS_CollectAllSignals`) — non corretto qui (fuori scope, tocca la strategia SH_BMS_RTO, non l'instrumentazione), ma ora completamente **tracciato e trasparente** nei nuovi contatori invece di essere nascosto in un linkage impreciso.

## Verdict

### **READY_FOR_STRUCTURAL_CAUSAL_EXPERIMENT**

Tutti i criteri di accettazione superati: linkage deterministico per episodio (mai nearest-timestamp), zero orphan, zero ordine impossibile, nessun campo temporale causalmente falso, label rinominato per riflettere solo eventi realmente registrati. Il dataset (`at_sweep.csv`, `at_true_break.csv`, `structural_events.csv`, `metadata.json`) è ora affidabile per un futuro esperimento causale — non ancora eseguito in questa fase.
