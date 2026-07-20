# Nexus — Query Tests (M5)

Test deterministici del Query Engine. Esecuzione:

```
python3 knowledge/query_engine.py --selftest    # 14 test
python3 knowledge/query_engine.py --validate    # integrita' referenziale completa
```

Nessun test dipende da rete, orologio o stato mutabile: girano sulla base
canonica corrente e falliscono in modo esplicito se la base viola un invariante.

## I 14 selftest

| # | Test | Cosa dimostra |
|---|---|---|
| 1 | `strategy_by_id MACD` | lookup entità: id, matched_fields, link alle run |
| 2 | `run_by_id` (prima run in ordine) | la run espone `confidence` (import) e artefatto |
| 3 | `artifact_by_checksum` roundtrip | checksum → artifact_id → stesso artefatto |
| 4 | `open_bugs` + `resolved_bugs` = 31 | la partizione dei bug è totale ed esclusiva |
| 5 | `baseline_availability` (37 claim) + SAR | copertura completa; SAR=`expected_but_missing` dal solo campo enum |
| 6 | `timeline_of_strategy MACD` | ordine cronologico (timestamp,event_id); conteggio = timelines JSON |
| 7 | `evidence_for_claim` | claim con `{evidence_status, evidence_strength}` e link alle fonti |
| 8 | `traverse` strategy→depth 2 | raggiunge run/evidenze, zero nodi duplicati (anti-ciclo), edges ordinati |
| 9 | errori | `unknown_id`, `unknown_query_type` (con elenco supported), `invalid_filter`, round inesistente: tutti strutturati |
| 10 | tutti i 21 query type ×2 | ogni tipo è idempotente: doppia esecuzione ⇒ stringa JSON byte-identica |
| 11 | `incomplete_runs` | coerente col conteggio diretto su runs_database |
| 12 | `validate()` | riferimenti risolti, traverse a depth max senza duplicati, ordinamento stabile |
| 13 | `strategies_by_timeline_coverage` | usa il campo canonico M4.1, non le etichette umane |
| 14 | `missing_artifacts` | include la DQI S04 e il claim `artifact_missing`/`baseline_run_missing` collegato |

Copertura richiesta da M5 → test: entity lookup (1,2,3), relationship traversal
(8,12), missing entities (9), baseline availability (5), timeline (6), bug (4),
artifact checksum (3), evidence (7), stable ordering (8,10,12), idempotent
output (10,12).

## `--validate` (integrità referenziale)

Controlla su tutta la base, non su un campione:

- ogni `artifact_checksum` delle run risolve in artifacts_database;
- ogni `strategy` citata da run/eventi/issue esiste tra le 37;
- ogni `run_id` citato da artefatti/eventi esiste;
- ogni `related_*_id` degli evidence link risolve nel rispettivo database;
- `traverse` a profondità massima (4) termina senza nodi duplicati (anti-ciclo);
- tre query campione eseguite due volte producono byte identici.

Esito corrente: `validation: ok`, `errors: []`.

## Risultati correnti (base al 20/07, S01-S08 importate)

```
selftest: OK (14/14)
--validate: ok, 0 errori
```

## Come estendere i test

Un nuovo query type richiede: (a) handler registrato in `QUERIES`;
(b) parametri di esempio nel test 10 (idempotenza) — il test fallisce se il tipo
non è coperto da parametri validi e restituisce errore non deterministico;
(c) un test dedicato se introduce semantica nuova (non solo un filtro in più).
