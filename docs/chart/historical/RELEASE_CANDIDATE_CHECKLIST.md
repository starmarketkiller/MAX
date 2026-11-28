# Candidato cumulativo — checklist di installazione, spazio, backup, rollback e verifica Render (Fase 07)

Stato: **PREPARATO, NON ESEGUITO, NON APPROVATO**. Nessun merge, nessun deployment, nessun push su rami che attivano workflow, nessuna modifica a `main` (`111431ad`). Safe Deploy resta `disabled_manually`.

## 1. Composizione e provenienza (nessun candidato precedente è stato modificato)
| Strato | Ramo / commit | Stato |
|---|---|---|
| CHART-INFRA-FIX-02 (infrastruttura) | `infra/chart-only-deploy-ready-01` · `7bd569ba` · Linux 230/230 (run 46053059804) | approvazione indipendente **dichiarata dall'owner**, documento non in mio possesso |
| Geometry-01 | `dev/chart-geometry-01` · `75c2bd5f` (+ `4c12c959`) | verifica dell'autore; review separata |
| Multiscale-Discovery-01 | `dev/chart-multiscale-discovery-01` · `f264a705` | verifica dell'autore; review separata |
| Historical-Expansion-01 | `dev/chart-historical-expansion-01` (HEAD finale in `MANIFEST`) | verifica dell'autore |
Il ramo di sviluppo corrente **contiene per costruzione** tutti e quattro gli strati (catena lineare di commit); il candidato cumulativo = il suo HEAD finale. Nome proposto: `release/chart-cumulative-01` (non corrisponde a nessun trigger).
Differenza rispetto all'infrastruttura approvata: **0 file** tra `docker-entrypoint.sh`, `chart_authority_ctl.py`, `Dockerfile`, `chart_guard.py`, `chart_store.py`, `chart_api.py`, test dell'autorità e `docker_runtime_verify.sh` (verificato con `git diff --name-only 7bd569ba HEAD`).

## 2. Trigger e assenza di deployment automatico (verificato sui file)
| Workflow | Trigger | Effetto |
|---|---|---|
| `ci.yml` | push `main`, `claude/**`, `feature/**`; PR su `main` | test; **non** parte da `dev/**`, `release/**`, `infra/**` |
| `safe-deploy.yml` | `workflow_run` di `CI`, solo se `head_branch == 'main'` | **disabilitato manualmente** nel repository |
| `chart-only-runtime-verify.yml` (approvato) | `workflow_dispatch`; push `infra/**` | verifica Docker con fixture sintetica; nessun secret, nessun deploy |
| `chart-cumulative-runtime-verify.yml` (**nuovo, non eseguito**) | `workflow_dispatch`; push `infra/chart-cumulative/**` | 3 job: script approvato (fixture standard), script approvato su **fixture sintetica di scala** (547 giorni M1, cgroup 512 MiB), smoke geometrie/Discovery attraverso restart e ridistribuzione |
Prima di ogni push infrastrutturale: (1) `gh api repos/<fork>/actions/workflows` → `Safe Deploy = disabled_manually`; (2) nessun nuovo trigger di produzione; (3) `git ls-remote origin main` invariato. **Un push su `infra/chart-cumulative/**` avvia anche il workflow approvato (`infra/**`): è voluto.** I rami `dev/**` e `release/**` non avviano nulla.

## 3. Cosa si installa (e cosa NO)
* **Codice**: l'immagine contiene già `server/research_scripts/phase7/*.json` (partizioni, sigillo): `.dockerignore` non li esclude; il codice dello store/Lab è in `server/` e `frontend/`.
* **Dati**: lo store storico (20,4 MB) **non è nel repository** e **non va pubblicato** sul fork pubblico (dati derivati Dukascopy). Si trasferisce dal PC con lo strumento dell'operatore (`chart-authority install-store --from … --manifest … --manifest-sha256 …`), come già per XM. Nessun tick va su Render.
* **Autorizzazione**: lo strumento `chart-authority publish` accetta **solo** `EXPLICIT_WINDOWS`. Il record di sviluppo (`PHASE7_PARTITIONS`) non è pubblicabile in produzione. Modello pronto, **da approvare dall'owner**: `docs/chart/historical/chart_authorization.persistent.cumulative.TEMPLATE.json` (Dukascopy: esattamente `2023-02-04T00:00:00Z → 2024-08-04T00:00:00Z`, XM invariato); test dedicati (4) provano che coincide con la partizione `development_discovery`, non tocca il sigillo né le altre partizioni e che la guardia reale ammette/nega i giorni attesi.
* **Variabili Render**: nessuna nuova. Il B64 è monouso (contratto FIX-02): rimuoverlo dopo il bootstrap. **Non modificate** variabili Render reali in questa missione.

## 4. Spazio (disco nominale 1 GB; lo spazio libero effettivo NON è noto)
| Voce | Stima / misura |
|---|---|
| Store Dukascopy 547 giorni + XM | 21,0 MB misurati (20,4 MiB) |
| Aggiornamento senza rollback (store nuovo accanto al vecchio durante `install-store`) | 2 × 21 MB = 42 MB |
| Rollback (conservare lo store precedente) | + 21 MB (63 MB totali) |
| Database SQLite (geometrie, schede, ricerche) | KB–pochi MB; crescita lineare con le revisioni (append-only) |
| Con opzioni X1+X2 (non richieste) | < 100 MB di store |
**Prima del rilascio misurare lo spazio libero reale** (`df -h /data` da shell root su Render) e confermare ≥ 200 MB liberi; con meno, non installare.

## 5. Backup e rollback
1. **Prima**: copia di `/data/nexus.db` (`sqlite3 .backup`), di `/data/chart_store`, `/data/chart_auth` e `/data/.chart_authority_ledger` in una cartella `backup_<UTC>` dello stesso disco (se c'è spazio) **e** fuori da Render (download dell'operatore).
2. **Rollback dell'immagine**: ridistribuire l'immagine precedente sullo stesso volume (provato in CI per `16eff18b` nel run 46053059804; per il cumulativo è prevista nel nuovo workflow). Lo schema SQLite cresce con migrazioni **additive** (`ALTER TABLE ADD COLUMN`, tabelle nuove): il codice vecchio ignora colonne/tabelle in più.
3. **Rollback dei dati**: `chart-authority install-store` dallo store precedente; revoca con `chart-authority revoke` (persistente ai restart, contratto FIX-02).
4. Criterio di rollback: health check `/api/ready` non sano, 5xx > 1% sulle rotte `/api/chart/*` in 10 minuti, RSS > 450 MiB, oppure `SEGMENT_HASH_MISMATCH`.

## 6. Verifica su Render prima di dichiarare pronto (RENDER_READINESS resta **BLOCKED** finché non sono attestate)
- [ ] Shell root disponibile (`id -u` = 0) e comportamento di `chown`/sticky sul disco reale (il probe dell'avvio lo verifica ma va letto nel log).
- [ ] Spazio libero reale di `/data` e quota snapshot.
- [ ] Una modifica di variabile fa solo restart o rebuild? (dipende dalla dashboard).
- [ ] Possibilità di deployare un commit fuori da `main` (ramo `release/…`) oppure decisione dell'owner sul processo.
- [ ] Esecuzione del workflow Linux del cumulativo (**autorizzazione richiesta**) con esito 100% PASS e picco cgroup < 512 MiB con la fixture di scala.
- [ ] Installazione dello store e del record di autorizzazione esplicito (decisione owner), poi `chart-authority verify` e prova HTTP: H4 completo = 2.393 barre, 403 su 2024-08-04, 403 su finestre sigillate.
- [ ] Review indipendente del cumulativo (non coincide con il test dell'autore).
- [ ] Nessun errore 5xx e RSS stabile dopo 20 minuti di uso con 4 grafici.

## 7. Limiti noti da dichiarare
Orologio e calendario del feed Dukascopy non verificati in modo indipendente; barre dal solo bid; feed diverso dal broker XM; nessuna misura di CPU/RAM Linux (solo Windows); Docker non disponibile sul PC di sviluppo.
