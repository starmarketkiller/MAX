# 04 — Regole di validazione (Canonical Schema v1)

Formali in [schema_v1.json](schema_v1.json) (V01-V12). Le più importanti, con il perché:

| # | Regola | Perché esiste |
|---|---|---|
| V01 | Run senza strategia solo se il parse fallisce → `completed=false` + issue | mai run "orfane" silenziose |
| V02 | Un TimelineEvent appartiene a esattamente UNA strategia | la storia è per-strategia, non ambigua |
| V03 | Il checksum di un Artifact non cambia mai | file cambiato = artefatto nuovo, la storia non si riscrive |
| V04 | Import duplicati vietati (stesso checksum = skip) | idempotenza |
| V05 | `identity_mismatch` → run mai eleggibile come baseline, severity high | protezione post incidente S01/LIQ_SWEEP: il Core è il secondo livello di difesa |
| V06 | Passata attesa mancante nel round baseline → issue `missing_artifact` | i buchi diventano entità interrogabili (caso S04) |
| V07 | Evento senza data determinabile → NON creato (gap dichiarato) | "do not invent": meglio un buco onesto di una data inventata |
| V08 | Ogni run/bug referenziato da un evento deve esistere | integrità referenziale |
| V09 | Run append-only, mai sovrascritte | round diversi coesistono (caso TSI ×4) |
| V10 | `artifact.status` avanza solo in avanti | discovered→imported→parsed→validated, mai retrocessioni |
| V11 | Campi run-derived scritti solo dall'importer; campi curati solo da revisione | due proprietari, mai in conflitto |
| V12 | Nulla entra nella Knowledge senza validazione | nessun bypass del lifecycle |

Dove sono implementate: V01-V06, V09-V11 in `import_engine.py`; V02, V07, V08 in `timeline_engine.py`; V12 è la composizione di tutte.
