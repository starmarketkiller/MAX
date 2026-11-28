# Riconciliazione infrastrutturale — CHART-INFRA-FIX-02 (Fase 09, NEXUS-CHART-MULTISCALE-DISCOVERY-01)

Nessuna modifica all'infrastruttura approvata (`docker-entrypoint.sh`, `chart_authority_ctl.py`, `Dockerfile`, workflow, guardia/store/API dati): diff dei commit di questa missione = 0 file infra.

## 1. Approvazione indipendente di CHART-INFRA-FIX-02
* Registrata come **dichiarata dall'owner** nel brief di missione del 2026-11-28 ("la review indipendente… è gestita separatamente", candidato `7bd569ba`).
* Il **documento di review non è nel repository né nei miei file di lavoro**: questa riga attesta la dichiarazione, non il contenuto della review. Da allegare dall'owner (riferimento, hash e verdetto del reviewer) prima di usarla come prova di approvazione.
* Stato della mia consegna originale: `INFRASTRUCTURE_STATUS = CANDIDATE_READY`, **non auto-approvato**; `RENDER_READINESS = BLOCKED` finché non sono attestate le verifiche di piattaforma (shell root, sticky/chown sul disco Render, spazio e snapshot di `/data`, restart vs rebuild per le variabili, deploy di un commit fuori `main`, staging).

## 2. Controllo Linux 231 → 230: riconciliato
| Run | SHA | Totale | PASS | FAIL |
|---|---|---|---|---|
| #46051988603 | `956090a7` | 231 | 225 | 6 |
| #46053059804 | `7bd569ba` | 230 | 230 | 0 |

Confronto per nome dei controlli (`results.tsv`): **un solo controllo presente nella prima run e assente nella seconda**: `http_RB_rollforward_store_reinstalled_still_denied_until_publish`; nessun controllo nuovo nella seconda. Causa: il commit `7bd569ba` ha riordinato la fase RB (lo store in quarantena viene **reinstallato prima** dell'asserzione di diniego, perché con lo store in quarantena l'API risponde `200 STORE_UNREACHABLE` e non isola l'autorità). Il vecchio controllo "store reinstallato, ancora negato fino alla pubblicazione" è stato **fuso** in `http_RB_rollforward_denied_until_operator_publishes`, che ora lo copre (diniego con store presente). I 6 FAIL della prima run erano difetti dello script di verifica, già documentati; i 144 controlli storici restano tutti presenti e PASS (`evidence/regression_144_preserved.json`). Aritmetica: 144 + 87 = 231; 144 + 86 = 230.
Conclusione: **nessun controllo è andato perso senza sostituto**; la copertura semantica del controllo rimosso è preservata. (Verificato su `results.tsv` delle due run, non a memoria.)

## 3. Provenienza del commit storico `74ad2138`
* `74ad2138` — *CHART-REAL-DATA-V1-FIX-02: atomic authorization (single immutable authority snapshot per response; FIX01R-01)* — 2026-11-27, autore `starmarketkiller`, co-autore Claude; modifica `server/chart_guard.py` e `server/tests/test_chart_fix02_atomic_authority.py`. Esiste **solo sul branch locale `fix/chart-real-data-v1-fix-02`** (non su `origin`), mai deployato.
* **Non è antenato** di `7bd569ba` né di `dev/chart-multiscale-discovery-01`: la linea Chart-only è stata ricostruita come commit unico `6994b654` ("CHART_ONLY: real-data Chart … on top of live 16eff18b", antenato comune = live `16eff18b`).
* **Il contenuto è però presente e identico**: `git rev-parse` dei blob `server/chart_guard.py` (`33dc58001d…`) e `server/tests/test_chart_fix02_atomic_authority.py` (`b2aae34e85…`) coincide fra `74ad2138` e `7bd569ba`. Quindi la logica FIX-02 (snapshot immutabile + `verify_all`) è nel candidato; la cronologia individuale del commit no. Provenienza conservata qui; il branch storico va mantenuto finché la review non l'ha archiviato.

## 4. Verifica Linux/Docker del nuovo candidato — **preparata, NON eseguita**
Perché serve: il candidato Geometry/Discovery aggiunge tabelle SQLite (stessa `nexus.db` su `/data`), migrazioni additive e endpoint; il vincolo Render è **512 MiB per il backend** (il browser non conta).
Preparato (additivo, nessun file infra modificato):
* `tools/linux_geometry_smoke.py write|verify`: crea sessione, geometria, scheda evento, stato della ricerca, export; dopo `docker restart` e dopo ridistribuzione della stessa immagine sullo stesso volume verifica persistenza senza variazioni (stesso sha256), `NOT_VALIDATED`, rifiuto di `epistemic_mode`, 404 uniforme. Eseguito in locale contro il backend di sviluppo: **11/11** (6 write + 5 verify); non ancora su Linux.
* Procedura proposta: copiare lo script nel job dopo la fase "restart" del workflow esistente (richiede una modifica al workflow = **autorizzazione necessaria**), oppure eseguirlo a mano nel runner; misurare RSS del backend a riposo e dopo 4 pane equivalenti di richieste OHLC (limite cgroup 512 MiB, già verificato 73 MiB di picco nel run `46053059804` per la sola Chart).
* Esecuzione = push su un branch `infra/…` (il workflow `Chart-only runtime verify` parte su `infra/**`, repository pubblico, nessun costo). **Non eseguito**: nessun push su `infra/**` senza tua autorizzazione esplicita; Safe Deploy resta `disabled_manually`.
