# Nexus — Query Examples (M5)

Esempi reali eseguiti sulla base di conoscenza corrente (baseline `e6ce816`,
sweep S01-S08 importate). Gli output sono estratti letterali del motore:
rilanciando gli stessi comandi si ottengono byte identici.

## 1. Lookup di una strategia

```
python3 knowledge/query_engine.py strategy_by_id strategy_id=MACD
```
→ `status: ok`, 1 risultato con `matched_fields` (nome, selector_index 3, stato),
`confidence` = affidabilità dati dichiarata dal database, e `links` verso le sue
run (5), gli eventi timeline, i claim di evidenza e i bug che la citano.

## 2. Chi NON ha ancora una baseline, e perché (campo M4.1)

```
python3 knowledge/query_engine.py baseline_availability state=expected_but_missing
```
```json
{
 "status": "ok",
 "result_count": 1,
 "results": [{
   "entity_type": "evidence_claim",
   "entity_id": "clm-03825a61c8cf",
   "matched_fields": {
     "claim_type": "baseline_run_missing",
     "subject_id": "SAR",
     "evidence_status": "supported",
     "evidence_strength": "strong",
     "baseline_availability_state": "expected_but_missing"
   },
   "source_ids": ["knowledge/data_quality_issues.json"],
   "links": {"evidence_links": ["evl-38a9a67f9daa"], "subject": ["strategy::SAR"]}
 }]
}
```
Con `state=not_yet_observed` si ottengono le 29 strategie non ancora raggiunte
dallo sweep (stato normale, non anomalia); con `state=available` le 7 con
baseline valida; senza filtro, tutte e 37.

## 3. Run del round baseline

```
python3 knowledge/query_engine.py runs_by_round round=sweep37-baseline-e6ce816
```
→ 7 run, ciascuna con metriche signal-level nei `matched_fields`, `confidence`
dell'import, link all'artefatto (per checksum) e ai claim che la riguardano.
Round inesistente? → `error.code=unknown_id` con l'elenco `rounds_esistenti`.

## 4. Dall'anomalia S04 a tutto ciò che la tocca (traversal)

```
python3 knowledge/query_engine.py traverse \
    start_type=data_quality_issue \
    start_id=dqi-missing-S04-sweep37-baseline-e6ce816 depth=2
```
→ 22 nodi: l'issue, la strategia SAR, le sue 4 run storiche (round pre-baseline),
i claim di evidenza collegati (incluso `clm-03825a61c8cf` expected_but_missing)
e i bug che citano SAR. `edges` elenca ogni arco percorso come coppia ordinata
`"tipo::id" → "tipo::id"`; nessun nodo compare due volte (guardia anti-cicli).

## 5. Storia dei commit di una strategia

```
python3 knowledge/query_engine.py commit_history_of_strategy strategy_id=MACD
```
→ 3 commit in ordine di prima documentazione (es. `3cba036`, `d051ece`, …),
ognuno con gli eventi timeline che lo citano e/o i bug il cui fix lo referenzia.

## 6. Documentazione collegata a una strategia

```
python3 knowledge/query_engine.py documentation_of_strategy strategy_id=MACD
```
→ entità `document` (path dei file sorgente citati dagli eventi timeline),
ciascuna con il conteggio e gli id degli eventi che la referenziano.

## 7. Evidenze su un soggetto

```
python3 knowledge/query_engine.py evidence_for_subject \
    subject_type=strategy subject_id=SAR
```
→ tutti i claim con soggetto SAR (esistenza, baseline mancante, …), ciascuno con
`{evidence_status, evidence_strength}` in `confidence` — mai fusi con
Run.confidence.

## 8. Errori deterministici

```
python3 knowledge/query_engine.py strategy_by_id strategy_id=NON_ESISTE
→ {"status": "error", "error": {"code": "unknown_id", ...}, "results": []}

python3 knowledge/query_engine.py query_inventata
→ {"error": {"code": "unknown_query_type", "supported": [ ...21 tipi... ]}}

python3 knowledge/query_engine.py baseline_availability state=forse
→ {"error": {"code": "invalid_filter", "message": "state ammessi: [...]"}}
```

## 9. Igiene dei dati in una riga

```
python3 knowledge/query_engine.py open_bugs             # 7 bug aperti
python3 knowledge/query_engine.py incomplete_runs       # run completed=false
python3 knowledge/query_engine.py identity_mismatches   # oggi: nessuno
python3 knowledge/query_engine.py missing_artifacts     # DQI S04 + claim collegato
python3 knowledge/query_engine.py data_quality_issues status=open
```

## 10. Copertura timeline (terminologia M4.1)

```
python3 knowledge/query_engine.py strategies_by_timeline_coverage \
    coverage=complete_for_available_evidence
```
→ le 7 strategie la cui storia è completa **per le evidenze disponibili**
(mai storia assoluta).
