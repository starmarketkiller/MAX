# NEXUS MASTERPLAN V4.1 — GitHub CI/CD Governance

Fonte: census read-only dedicato di questa sessione. Nessun file toccato, nessun workflow modificato.

## Sequenza reale: commit → CI → Safe Deploy → Render

```
push (main/claude/**/feature/**) o PR→main
  → ci.yml: backend-tests (validate_registry.py + pytest) ∥ security-preflight ∥ docker-smoke ∥ frontend-build
  → (solo su push a main, dopo successo CI) safe-deploy.yml, trigger workflow_run
  → classify_deploy_risk.py → LOW_RISK | MEDIUM_RISK | HIGH_RISK
  → LOW/MEDIUM: deploy automatico, nessun passo umano (environment "nexus-production-low-medium-risk")
  → HIGH: environment protetto "nexus-production-high-risk" (approvazione richiesta)
           salvo evaluate_auto_approval.py qualifichi per "nexus-production-high-risk-auto"
  → verify_render_deploy.py: verifica SHA live, readiness, dispatcher
  → su fallimento: istruzione esplicita "non dichiarare successo, rollback manuale all'ultimo SHA sano"
```

## `security-preflight` — contiene un test "negativo" reale, non solo positivo

Un passo verifica che credenziali deboli/di default sotto `NEXUS_ENV=LIVE` vengano **rifiutate** da `app.security_preflight()` — se il preflight le accettasse mai, questo step stesso fallisce. È un test di regressione su un gate fail-closed, non solo "il codice compila".

## `classify_deploy_risk.py` — cosa rende un deploy HIGH_RISK

`HIGH_PATHS`: `MQL5/`, `server/nexus_security.py`, `server/command_contract.py`, `server/settings_contract.py`, `server/nexus_retention.py`, `server/migrations/`, `server/auth`, `contracts/command`, `contracts/approval`, `render.yaml`, il workflow Safe Deploy stesso e il classificatore stesso. `HIGH_WORDS`: regex su secret/password/billing/payment/live-trading/order-send/approval-gate/DROP TABLE/DELETE FROM nel testo della patch. Tutto il resto sotto `server/`/`frontend/`/`contracts/`/`deploy/` è `MEDIUM_RISK` (auto-deploy consentito); fuori da questi percorsi è `LOW_RISK`.

## `evaluate_auto_approval.py` — un secondo livello di protezione, deliberatamente ridondante

Veto rigido su chi tocca la macchina di deploy/approvazione stessa, valutato usando la versione **pre-commit** del file (un commit non può mai riscrivere le proprie regole di approvazione). Liste hard-veto **duplicate intenzionalmente** (non importate) rispetto a `classify_deploy_risk.py` — "cintura e bretelle" contro un bug del classificatore che allarghi silenziosamente cosa è sicuro. Limite massimo di dimensione diff (`MAX_DIFF_LINES_DEFAULT = 150`).

**Questo livello di rigore sul deploy è tra i più solidi trovati in tutto il sistema NEXUS** — da preservare esplicitamente, non da "semplificare".

## Governance mancante

**Nessun file `.github/CODEOWNERS` trovato.** La branch protection, se esiste, non è verificabile dal solo repository locale (vive nella configurazione GitHub, non nel codice).

## Classificazione

| Area | Classificazione | Nota |
|---|---|---|
| Pipeline CI (4 job) | **KEEP** | Rigorosa, reale, non aspirazionale |
| Safe Deploy (classify→deploy, doppio livello di protezione) | **KEEP** | Il pezzo di governance più maturo del sistema |
| `security-preflight` con test negativo | **KEEP** | Pattern di test di alta qualità, da replicare altrove se utile |
| Assenza CODEOWNERS | **QUICK_WIN** (se desiderato) | Costo minimo, aggiunge revisione obbligatoria per aree sensibili — decisione dell'utente, non eseguita qui |
| Rollback | **PARTIAL** | Solo manuale, nessuna automazione — coerente con la cautela generale del sistema su azioni irreversibili, non necessariamente un gap da colmare |

## Raccomandazione

Non toccare nulla di questa pipeline senza necessità — è già tra le parti meglio costruite di NEXUS. L'unico item a costo quasi zero è valutare un `CODEOWNERS` per le aree `HIGH_PATHS` già identificate da `classify_deploy_risk.py` (userebbe la stessa lista già esistente, nessuna nuova tassonomia).
