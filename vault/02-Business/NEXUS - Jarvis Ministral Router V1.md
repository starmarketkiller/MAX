# NEXUS — Jarvis Ministral Router V1

**Commit:** `75b5110` (router + gateway), `ced3d59` (fix prompt enum esplicito). Dipendenze: Jarvis V1 core, Local Agent Bridge V1.

## Decisione

Aggiungere Ministral come livello di interpretazione cognitiva **opzionale** davanti al classifier regex esistente, mai in sostituzione — e mai una dipendenza runtime a pagamento: Claude (in sessione) resta il "supervisore offline" che scrive i prompt/template; nessuna chiamata Claude API automatica, nessun costo ricorrente aggiunto.

## Architettura

```
Telegram → Jarvis → classify() deterministico (comandi già inequivocabili)
                   → se NON inequivocabile e router abilitato:
                        Local Inference Gateway (confine di sicurezza, 127.0.0.1-only,
                        auth token, rate limit) → Ollama locale (ministral-3:3b)
                        SHADOW: risposta reale resta il classifier, confronto solo loggato
                        ACTIVE: usa Ministral solo se schema valido + confidence alta
                   → fallback sempre al classifier esistente su qualunque anomalia
```

`JARVIS_MINISTRAL_ROUTER_ENABLED=false` di default ovunque — zero impatto in produzione finché non attivato esplicitamente. Mai wired in modalità ACTIVE in produzione ad oggi.

## Evidenza/test

42 test automatici (router, gateway, integrazione) con Ollama mockato — CI non ha Ollama. Benchmark reale contro il Ministral locale (2026-10-05, i5-7200U, nessuna GPU dedicata): 8 frasi, latenza media **45.7s**, p95 **49.7s**, **4 tok/s** costanti, schema-valid 100% (dopo il fix dell'enum esplicito), **agreement col classifier solo 37.5%** (3/8) — Ministral tende a rispondere `needs_clarification=true` anche su frasi che il classifier gestisce già bene.

## Limiti dichiarati

- Hardware-gated: su questa macchina (CPU-only) Ministral non è utilizzabile come frontend conversazionale in tempo reale — confermato, non ipotizzato.
- L'intento Ministral riusa gli stessi valori di `request_class`, ma **non riscrive il testo del messaggio** — i metodi canonici (`create_task`, `state_query`, ecc.) continuano a fare il proprio parsing sul testo grezzo. Ministral sceglie solo QUALE metodo e QUALE task, non i parametri.
- Tunnel/SHADOW mai attivati in produzione — il gateway locale è stato avviato e poi fermato per liberare risorse (vedi `LocalBridge/start_gateway.ps1`, non ancora committato).

## Blocker

Nessuno attivo. La decisione esplicita è stata: non investire altro tempo nel router finché non emerge un segnale di mercato reale (vedi First Revenue).

## Prossimo passo

Nessuno pianificato immediatamente — pausa deliberata a favore di `MINISTRAL_TASK_COMPILER_V1` (delega bounded, più preziosa nel breve) e poi FIRST_REVENUE.
