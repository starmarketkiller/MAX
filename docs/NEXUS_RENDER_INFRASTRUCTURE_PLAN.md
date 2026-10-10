# NEXUS MASTERPLAN V4.1 — Render Infrastructure Plan

Fonte: census read-only dedicato di questa sessione. Nessun file toccato, nessun servizio modificato, nessun deploy eseguito.

## Topologia reale

Un solo servizio `type: web`, `nexus-backend`, runtime Docker. **Nessun worker/cron separato** — scelta deliberata: i dischi persistenti Render non possono essere montati sia dal servizio web sia da un servizio worker separato, quindi il Queue Dispatcher gira in-process nello stesso servizio. 28 variabili d'ambiente dichiarate in `render.yaml`. Disco persistente: `/data`, 1GB, `autoDeployTrigger: off`.

## Rischio reale #1 — tre classi di dati crescenti condividono lo stesso disco da 1GB

`NEXUS_DB_PATH` (SQLite primario), `NEXUS_DUKASCOPY_DIR` (cache storico tick multi-anno — per natura una classe di dati che può crescere molto), `NEXUS_BACKUP_DIR` (default: sottocartella dello stesso disco del DB primario) — **tutti e tre sullo stesso 1GB**. Nessun cap di dimensione o rotazione trovato per la cache Dukascopy in questa passata.

**Non è un problema già manifestato** (non verificato se il disco è oggi vicino al limite), ma è un rischio strutturale concreto, non ipotetico: tre classi di dati in crescita su un disco piccolo, condiviso.

## Rischio reale #2 — backup manuale, stesso disco del primario

`server/nexus_retention.py` esiste davvero (non è un gap — risolve un gap precedente documentato: "persistenza ≠ backup: nessuna procedura di copia consistente, nessun test di ripristino"). `POST /api/admin/backup` chiama `backup_database()`. Ma:

1. **Nessun trigger automatico/schedulato trovato** — il backup avviene solo se un umano chiama l'endpoint admin.
2. **Il backup vive sullo stesso disco del DB primario** — un guasto a livello di disco perde entrambi insieme, nessuna copia off-disk/off-region.

Questo è il rischio infrastrutturale più concreto trovato in tutto il census V4.1.

## Dockerfile — build multi-stage reale, 2 rischi auto-dichiarati nel codice stesso

Build: `node:24-bookworm-slim` (frontend) → `python:3.12-slim` (finale). Non-root (`uid 10001`, chown di `/data` prima di droppare i privilegi). `HEALTHCHECK` usa correttamente `/api/ready` (non la liveness-only `/api/health`).

**Due rischi che il Dockerfile stesso dichiara come difetti aperti, non nascosti**:
1. Immagine base pinnata al tag mutabile `python:3.12-slim`, non a un digest — build non riproducibile per ammissione esplicita nel codice (righe 9-22).
2. `requirements.lock.txt` è opzionale — fallback silenzioso (con warning in build log) a `requirements.txt` non pinnato se il lock manca.

**Nota rilevante per questo task**: `vault/`, `docs/`, `knowledge/*` vengono già inclusi nell'immagine a build time per il Knowledge Browser (`knowledge_browser.list_entries()`, asserzione `count > 0`) — significa che **i documenti di questo stesso Masterplan V4/V4.1 entreranno automaticamente in quel corpus una volta mergiati su main**, nessun collegamento aggiuntivo necessario.

## Monitoring/osservabilità

Nessun Sentry/Datadog/New Relic o equivalente trovato in `requirements.txt`/`render.yaml`/codice. Solo `/api/health` (liveness) e `/api/ready` (DB+migrazioni+security preflight) — nessuna aggregazione log oltre quella nativa di Render.

## Classificazione e raccomandazioni (non eseguite, solo proposte)

| Area | Classificazione | Raccomandazione |
|---|---|---|
| Topologia single-service | **KEEP** | Scelta corretta data la limitazione dei dischi Render condivisi |
| Disco condiviso DB+Dukascopy+backup | **STRUCTURAL, da monitorare** | Valutare un path di backup esterno (es. object storage) quando il volume lo giustifica — non urgente oggi, ma non ignorabile a lungo termine |
| Backup solo manuale | **HIGH_IMPACT, costo basso** | Aggiungere un trigger schedulato (cron esterno o job periodico) che chiama l'endpoint admin già esistente — riusa `nexus_retention.py`, non richiede un nuovo sistema |
| Immagine base non pinnata a digest | **QUICK_WIN** | Pinnare a un digest specifico — una riga di Dockerfile |
| `requirements.lock.txt` opzionale | **QUICK_WIN** | Renderlo obbligatorio in CI (fail se assente) invece di un warning |
| Nessun monitoring/alerting | **FUTURE** | Non urgente con un solo operatore e `/api/ready` già informativo; da rivalutare se il sistema cresce |

Questi item alimentano la lista unificata in [NEXUS_MASTERPLAN_V4_1.md](NEXUS_MASTERPLAN_V4_1.md).
