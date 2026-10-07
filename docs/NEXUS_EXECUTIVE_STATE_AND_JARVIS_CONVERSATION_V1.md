# NEXUS Executive State + Jarvis Executive Conversation V1

Marker: `NEXUS_EXECUTIVE_STATE_AND_JARVIS_CONVERSATION_V1_PARTIAL`
(Executive State + conversazione naturale funzionanti e verificati sul runtime locale;
deploy bloccato dalla CI preesistente → `EXECUTIVE_CONVERSATION_DEPLOY_BLOCKED_BY_CI`;
Mistral reale non verificabile da questa sessione).

## Architettura

```
Domain projections (esistenti)                 server/executive_v1/
 TaskQueue · OperationsProjection.revenue ──►  state.py      ExecutiveStateBuilder (provider isolati, cache 10s)
 FirstRevenueStore · strategy registry         sections.py   builder puri per sezione
 company control plane · EA telemetry          snapshots.py  snapshot leggeri + diff ("cosa è cambiato")
 AgencyStore (executive_slice/agency_state)    conversation.py intent + policy + briefing italiani
 gateway_status · dispatcher · local bridge    priority.py   P0 interactive gate
 /api/ready · executive_observations_v1.json
                     │
           NEXUS_EXECUTIVE_STATE_V1 (contracts/nexus-executive-state-v1.schema.json)
                     │
   JarvisService._dispatch_classifier → executive_state_answer (stesso Jarvis, stesso store conversazioni)
```

Nessun secondo Jarvis, database, orchestratore o coda. Unica modifica al core: parametro
opzionale `yield_predicate` del `DurableQueueDispatcher` (default invariato).

## Stato

- Sezioni: `system, tasks, approvals, revenue, trading, social, ai_fashion_agency, finance,
  infrastructure`, ognuna con `status, health, last_updated, source, confidence, key_metrics,
  active_work, blockers, next_actions`.
- Provider che fallisce → sezione `UNAVAILABLE` + `provider_errors` (solo classe eccezione).
- **Nessun numero inventato**: conto/PnL solo con telemetria EA online e < 10 min, altrimenti
  `UNAVAILABLE`; inbound/DM, costo modello locale e infrastruttura dichiarati non misurati.
- **CI / ultimo deploy**: il backend non può osservarli; li legge da
  `$JARVIS_STATE_DIR/executive_observations_v1.json` (o `NEXUS_CI_STATUS`). Assenti → "stato CI non noto".
- **overall_progress**: media di `MATURITY_WEIGHTS` (FOUNDATION .25, PARTIAL .5, OPERATIONAL .75,
  SHADOW .85, LIVE 1, BLOCKED 0) sui domini business con maturità nota
  (revenue, trading, agenzia, social); `UNAVAILABLE` se meno di 3. Metodo e basi esposti nello stato.
  Maturità per dominio da regole deterministiche (es. Revenue LIVE solo con vendite reali).
- **Alert**: un alert per codice (deduplicato tra domini), severità INFO/WARNING/IMPORTANT/CRITICAL.
- **Approvazioni unificate**: task `WAITING_APPROVAL` + bozze Revenue `READY_FOR_REVIEW` +
  decisioni Agency (crediti, listing, post), con `approval_id, domain, reason, cost, risk, created_at, action`.
- **What changed**: snapshot compatti (stati, metriche chiave, codici alert, id approvazioni,
  sha) al massimo 1/ora, 60 conservati; diff verso lo snapshot più vicino a 24h fa.

## Conversazione

Decision policy: `ANSWER_FROM_EXECUTIVE_STATE` / `ANSWER_FROM_DOMAIN_STATE` (deterministiche,
nessun modello per i numeri) → `ASK_MISTRAL` solo per i "perché" (fatti deterministici +
spiegazione; se Mistral non risponde lo dice e restituisce i fatti) → `CREATE_TASK` solo per
analisi vere, tramite la bozza esistente che richiede conferma (nessuna task creata da sola).

Priorità: l'executive interviene solo su classificazioni deboli (QUERY/UNKNOWN/FOLLOW_UP/
STATE_QUERY); comandi `/…`, mutazioni, riferimenti di approvazione, creazione task e domande
specifiche sull'agenzia mantengono i loro percorsi. I follow-up contestuali ("e il trading
invece?", "e possiamo risolverlo oggi?", "e poi?") valgono solo dentro una conversazione
executive (`last_view=EXECUTIVE`, TTL del conversation store).

Risorse: durante una sintesi Mistral interattiva il dispatcher non prende nuovo lavoro
background (P1–P4); il lavoro in corso non viene interrotto; riprende subito dopo.

## Verifica

- `tests/test_executive_state_and_conversation_v1.py` (20): schema, blocker reali, nessun
  numero inventato, telemetria vecchia nascosta, isolamento provider + cache, metodo progress,
  9 domande libere, multi-turn, priorità degli intent esistenti, analisi → bozza, "perché" con
  Mistral assente/presente (gate attivo, numeri dallo stato), diff snapshot, yield del dispatcher.
- Smoke sul runtime `app.py` con startup, osservazioni CI reali (run 733 rossa, 14 test) e
  store Agency reale: risposte corrette a tutte le domande, 0 errori schema/provider, 0 task create.
- Suite: 1050 passati; restano solo i 14 failure preesistenti (MT5 guard / contextual edge).

## Blocker

1. CI rossa (14 test MT5/MACD, lavoro Codex) → nessun deploy; Telegram live non verificabile.
2. Mistral reale: gateway non raggiungibile da questa sessione; i "perché" ripiegano sui fatti dichiarandolo.
3. `executive_observations_v1.json` va scritto su Render (o `NEXUS_CI_STATUS`) per avere lo stato CI in produzione.
4. Telemetria EA assente in questo ambiente → stato conto Trading `UNAVAILABLE` (corretto, non un bug).
