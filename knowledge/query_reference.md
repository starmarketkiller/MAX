# Nexus — Query Reference (M5)

`query_engine.py` v1.0.0 — motore di interrogazione **deterministico** sulla base
di conoscenza canonica (`knowledge/*.json`). Solo filtri esatti e attraversamento
di relazioni: niente ricerca semantica, niente embedding, niente LLM, niente
riassunti in linguaggio naturale. Stessa query ⇒ output **byte-identico**.

## Invocazione

```
python3 knowledge/query_engine.py <query_type> [chiave=valore ...]
python3 knowledge/query_engine.py --list        # elenco query supportate
python3 knowledge/query_engine.py --validate    # integrita' referenziale completa
python3 knowledge/query_engine.py --selftest    # 14 test deterministici
```

API Python: `run_query(KB(), query_type, params_dict)` → dict.

## Busta di risposta (sempre identica)

```json
{
 "query_engine_version": "1.0.0",
 "knowledge_schema_version": 2,
 "query": {"type": "...", "params": {...}},
 "status": "ok | empty | error",
 "result_count": N,
 "error": {"code": "...", "message": "..."},   // solo su status=error
 "results": [ <entita'> ]
}
```

Ogni entità restituita contiene sempre: `entity_type`, `entity_id`,
`matched_fields` (campi che hanno soddisfatto la query), `source_ids` (file/fonti
da cui i valori sono verificabili), `confidence` (quando applicabile: Run.confidence,
event confidence, oppure `{evidence_status, evidence_strength}` per i claim — mai
fusi tra loro) e `links` (id delle entità collegate, per tipo).

## Codici di errore deterministici

| code | quando |
|---|---|
| `unknown_query_type` | tipo di query non supportato (l'errore elenca `supported`) |
| `unknown_id` | id esatto non presente nel database interrogato |
| `invalid_filter` | parametro mancante, valore fuori enum, depth fuori range |

Risultati vuoti da filtri validi ⇒ `status: "empty"` con `results: []` (non è un
errore). Riferimenti rotti incontrati in `traverse` ⇒ campo `broken_references`
nella busta (mai risolti in silenzio).

## Query supportate (21)

| query_type | parametri | note |
|---|---|---|
| `strategy_by_id` | `strategy_id` | una delle 37 strategie |
| `run_by_id` | `run_id` | |
| `artifact_by_checksum` | `checksum` (sha256) | |
| `bug_by_id` | `bug_id` (BUG-NNN) | |
| `decision_by_id` | `decision_id` (DEC-NNN) | |
| `timeline_of_strategy` | `strategy_id` | eventi in ordine cronologico (timestamp, event_id) |
| `evidence_for_claim` | `claim_id` (clm-…) | |
| `evidence_for_subject` | `subject_type`, `subject_id` | tutti i claim su un soggetto |
| `data_quality_issues` | `status?` (open/resolved) | |
| `baseline_availability` | `state?`, `strategy_id?` | usa il campo M4.1 `baseline_availability_state` |
| `strategies_by_timeline_coverage` | `coverage?` | enum M4.1 `complete/partial_for_available_evidence` |
| `runs_by_round` | `round` | l'errore elenca i round esistenti |
| `artifacts_by_type` | `artifact_type` | l'errore elenca i tipi esistenti |
| `open_bugs` | — | stato ≠ "risolto…" |
| `resolved_bugs` | — | stato "risolto…" |
| `identity_mismatches` | — | run identity_ok=false + issue + claim dedicati |
| `incomplete_runs` | — | completed=false |
| `missing_artifacts` | — | issue missing_artifact + claim artifact_missing |
| `documentation_of_strategy` | `strategy_id` | documenti citati dagli eventi timeline |
| `commit_history_of_strategy` | `strategy_id` | commit da eventi timeline + commit_fix dei bug |
| `traverse` | `start_type`, `start_id`, `depth?` (1..4, default 2) | BFS deterministica, guardia anti-cicli |

## Attraversamento relazioni (`traverse`)

Grafo tipizzato navigabile in entrambe le direzioni documentate:

```
strategy ─┬→ runs ──→ artifact ──→ claims
          ├→ timeline_events ─→ commit / document / run / claims
          ├→ claims (evidence)
          └→ bugs ──→ claims
run ──→ strategy / artifact / claims / timeline_events
data_quality_issue ──→ strategy / run / claims
decision ──→ claims        bug ──→ claims
```

- ogni nodo è visitato **una sola volta** (set `visited` ⇒ nessun loop ciclico);
- frontiera e vicini ordinati ⇒ stesso grafo a ogni esecuzione;
- `edges` restituiti come lista ordinata `["tipo::id", "tipo::id"]`;
- nodi terminali senza tabella propria (`commit`, `document`) restituiti come
  entità con `matched_fields` vuoti;
- riferimenti non risolvibili finiscono in `broken_references`, mai inventati.

## Garanzie di determinismo

1. Nessun timestamp o stato di esecuzione nell'output.
2. Risultati sempre ordinati: per (`entity_type`, `entity_id`), tranne le query
   cronologiche (timeline, commit history) ordinate per timestamp documentato.
3. `--validate` verifica: tutti i riferimenti tra database risolvono; traverse a
   profondità massima termina senza duplicati; doppia esecuzione byte-identica.
4. La base è aperta in sola lettura; il motore non scrive alcun file.

## Limiti

- **Nessuna interpretazione**: il motore restituisce fatti registrati, non
  giudizi (le query "quale strategia è migliore" non esistono per design).
- Nessuna ricerca full-text o fuzzy: gli id devono essere esatti.
- `bugs ↔ strategy` usa il campo v1 `strategie_coinvolte` (testo libero, match
  per sottostringa deterministica): erediterà la tipizzazione dalla proposta P2
  se mai approvata.
- Le metriche esposte restano **signal-level** (mai equity di conto).
- I nodi `commit`/`document` sono terminali: niente lettura del contenuto.

## Punti di estensione futuri (non implementati)

- filtri composti (AND su più campi) e paginazione;
- query su `imports_ledger` e `backtest_database` (campagne storiche);
- attraversamento con proiezione dei campi (ridurre il payload);
- esposizione HTTP read-only per la Dashboard M6 (stessa API `run_query`);
- versionamento delle risposte se lo schema v2 introdurrà campi tipizzati.
