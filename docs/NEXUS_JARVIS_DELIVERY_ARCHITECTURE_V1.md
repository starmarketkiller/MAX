# NEXUS MASTERPLAN V4.1 — Jarvis Delivery Architecture

**Stato: in parte IMPLEMENTED (canale Telegram), proposta per il resto.** Formalizza il Delivery Layer richiesto dalla task (sez.18) e il percorso futuro verso un assistente mobile.

## Stato reale oggi

| Canale | Stato |
|---|---|
| Telegram | IMPLEMENTED — `telegram_adapter.py` (338 righe, costruito in questa sessione), `notification_sink` cablato a `_operations_jarvis_sink` in `app.py` |
| Sito | PARTIAL — le pagine esistono (vedi [Website Audit](NEXUS_WEBSITE_ARCHITECTURE_AUDIT.md)), nessuna notifica push dal sito verso l'utente oggi |
| Notifiche | PARTIAL — `alert_engine()` di `executive_v1` produce alert strutturati, ma non tutti raggiungono un canale oggi |
| Siri/Shortcuts | PLANNED — nessun codice, percorso descritto sotto |
| App Jarvis dedicata | PLANNED — nessun codice |

## Delivery Layer proposto (non implementato)

Non un nuovo sistema di notifica — un **filtro + router** sopra quello che già esiste (`notification_sink`, `alert_engine()`), con i campi richiesti dalla task:

```
{
  priority: P0-P4 (vedi nota di mappatura in NEXUS_MASTERPLAN_V4.md),
  dedup_key: string,          // evita notifiche duplicate per lo stesso evento
  summary: string,             // mai il log grezzo, sempre un riepilogo
  channel_preference: TELEGRAM | SITE | BOTH,
  delivery_status: PENDING | DELIVERED | FAILED,
  source_event_ref: string     // event_id dell'EventLedger, sempre tracciabile
}
```

**Principio esplicito**: non inviare qualunque log all'utente. Oggi `telegram_adapter.py::render_response()` già fa questo filtraggio per le risposte dirette a un comando — il Delivery Layer generalizza lo stesso principio alle notifiche push (non richieste da un comando specifico, es. un alert di Executive State).

## Percorso futuro — Mobile Assistant

```
iPhone → Siri/Comandi Rapidi → Jarvis API (nuovo endpoint autenticato) → Orchestrator → Result → Delivery Layer
```

**Non implementabile oggi senza una decisione esplicita**: richiede un nuovo endpoint API pubblico autenticato (oggi l'unica superficie esterna autenticata equivalente è il webhook Telegram) — stesso rigore di auth già visto nel [Backend Module Map](NEXUS_BACKEND_MODULE_MAP.md) (3 meccanismi distinti per 3 confini di fiducia), un quarto meccanismo per "assistente vocale mobile" andrebbe progettato con lo stesso rigore, non con un bearer token generico.

Questo percorso resta **FUTURE** nella roadmap — nessuna azione in questa sessione oltre documentarlo.

## Cosa Jarvis può notificare (dalla task, verificato contro la realtà)

Task completata, incidente, decisione richiesta, rischio, opportunità, risultati di un esperimento, miglioramento proposto. Oggi solo i primi 4 hanno un percorso reale (`notification_sink` + comandi Telegram); "risultati di un esperimento" e "miglioramento proposto" dipendono dal [Self-Improvement V1](NEXUS_DISTRIBUTED_SELF_IMPROVEMENT_V1.md) ancora da implementare.

## Preferenze utente

`conversation_store.py` (IMPLEMENTED, già reale) già tiene `notification_mode`/`preferred_provider` per conversazione — base pronta per `channel_preference` del Delivery Layer proposto, nessun nuovo store necessario.

## Checklist prima di implementare
- [ ] Conferma utente sul design del Delivery Layer.
- [ ] Nessuna azione sul Mobile Assistant prima che l'utente lo richieda esplicitamente — resta un percorso documentato, non un prossimo passo implicito.
