# NEXUS MASTERPLAN V4 — Modello di Coordinamento dei Responsabili di Reparto

**Stato di questo documento: PROPOSTA, non implementata.** Il census su Executive State/Capability Registry ha trovato: nessuna interfaccia formale `DepartmentResponsabile` esiste oggi. Ogni reparto è cablato ad hoc in `service.py`; "mai aggirare l'Orchestrator" è rispettato per convenzione osservata (confermato in ogni census di reparto — zero bypass trovati), non imposto da un contratto verificabile.

## Cosa esiste già (il punto di partenza, non da reinventare)

`server/executive_v1/sections.py` produce già, per 9 domini reali, una forma identica:

```python
{status, health, source, confidence, key_metrics, active_work, blockers, next_actions}
```

Questa È quasi esattamente la forma richiesta dalla task originale per l'output di un responsabile di reparto ("provenienza, stato di verifica, eventuali errori, priorità, necessità di approvazione"). Il gap non è la forma — è che oggi `executive_v1` LEGGE dati di dominio già prodotti altrove (lettura aggregata, sola lettura), non è il contratto che un reparto usa per PRODURRE il proprio output in primo luogo.

## Design proposto: `DEPARTMENT_RESPONSABILE_OUTPUT_V1`

Estensione additiva della forma già esistente, non un'interfaccia nuova da zero:

```json
{
  "schema_version": "DEPARTMENT_RESPONSABILE_OUTPUT_V1",
  "department": "trading | revenue | ai_fashion_agency | social_content | system_development | finance_cost | jarvis_automation",
  "status": "...",
  "health": "...",
  "provenance": {
    "source_module": "es. server/business_units/revenue.py",
    "generated_at": "ISO 8601",
    "based_on_events": ["event_id", "..."]
  },
  "verification_state": "VERIFIED | UNVERIFIED | VERIFICATION_FAILED",
  "errors": [],
  "priority": "P0-P4 (vedi nota terminologica sotto)",
  "approval_required": {
    "needed": false,
    "reason": null,
    "approval_id": null
  },
  "key_metrics": {},
  "blockers": [],
  "next_actions": []
}
```

**Campi riusati 1:1 da `executive_v1/sections.py`**: `status`, `health`, `key_metrics`, `blockers`, `next_actions`. **Campi nuovi, richiesti esplicitamente dalla task**: `provenance`, `verification_state`, `errors`, `priority`, `approval_required`.

## Nota terminologica — P0-P4 vs URGENT/HIGH/NORMAL/LOW

Il census infrastruttura ha trovato che `TaskQueue` usa `URGENT/HIGH/NORMAL/LOW`, non lo schema `P0-P4` che l'infografica e questa proposta usano. **Questa discrepanza va risolta esplicitamente, non ignorata silenziosamente**, prima di implementare questo schema — o si mappa P0-P4→URGENT-LOW in modo esplicito e documentato, o si estende `TaskQueue` in modo additivo. Decisione per l'utente, non presa qui.

## Come un reparto "diventa" un responsabile (senza aggirare l'Orchestrator)

```
Reparto (es. Revenue) → produce DEPARTMENT_RESPONSABILE_OUTPUT_V1
                       → SOLO leggendo dati che l'Orchestrator/EventLedger
                         già possiede per quel reparto (stesso principio
                         già verificato: zero reparto bypassa l'Orchestrator
                         oggi, per convenzione)
                       → Jarvis legge questo output (mai il reparto stesso
                         che notifica direttamente l'utente — stesso
                         principio già reale: AI Fashion Agency non pubblica
                         mai da sola, Revenue non invia mai da sola)
                       → Jarvis resta l'unica interfaccia executive
                         (già IMPLEMENTED: Telegram passa sempre da
                         service.py)
```

**Questo non crea un nuovo agente per reparto.** È una funzione pura (stesso spirito di `_safe()` in `executive_v1/state.py` — un provider isolato che non può far crashare l'aggregazione) che ogni modulo di reparto espone, chiamata da Jarvis on-demand o dal Council proposto (vedi documento Self-Improvement), mai un processo a sé stante.

## Perché questo soddisfa il vincolo "nessun responsabile deve aggirare l'Orchestrator o inviare notifiche incontrollate"

- **Aggirare l'Orchestrator**: impossibile per costruzione — il responsabile produce solo una *proiezione* di dati che l'Orchestrator/EventLedger già possiede, non ha un percorso di scrittura proprio verso l'esterno (stesso pattern già verificato per `business_units/revenue.py::agency_revenue_projection()`, che il census Revenue ha confermato essere "additiva, sola lettura, non un secondo sistema revenue").
- **Notifiche incontrollate**: impossibile per costruzione — solo Jarvis invia notifiche verso Telegram/l'utente (`notification_sink` già centralizzato in `app.py`, confermato nel census Jarvis & Automation). Un responsabile non ha un canale di notifica proprio.

## Implementazione incrementale proposta (non eseguita ora)

1. Pilota su **un solo reparto** (candidato: AI Fashion Agency o Revenue, entrambi già hanno funzioni di aggregazione dati reali da adattare).
2. Validare lo schema contro quel pilota.
3. Estendere agli altri 6 solo dopo conferma che lo schema non richiede modifiche strutturali impreviste.

## Checklist prima di implementare
- [ ] Conferma utente sul design e sulla risoluzione P0-P4 vs URGENT-LOW.
- [ ] Reparto pilota scelto.
- [ ] Schema JSON formale in `contracts/` solo dopo validazione sul pilota (non prematuramente).
