# NEXUS TASK #0011 — First Revenue Manual Experiment: Lead Research Service

**Baseline:** nessun commit di codice — esperimento di ricerca/outreach manuale, tracciato in questa conversazione e in `NOTES.md` (file locale non canonico, da considerare superato da questa nota una volta committata).

## Decisione

Dopo il pivot esplicito "NEXUS → FIRST REVENUE" (basta infrastruttura Jarvis senza segnale di mercato), l'opportunità scelta è stata **`OPP_LEAD_RESEARCH_SERVICE`**, già presente e rankata in `funding_v1/opportunity_priority_queue_v1.json`: un servizio di ricerca lead B2B, €25 per 15-20 lead qualificati, delivery interamente manuale per questo primo test (nessun CRM, nessuna integrazione di pagamento, nessuna automazione di outreach — coerente con `capability_coverage.py`, che classifica `crm` e `messaging` come `MISSING` e `payments` come `EXTERNAL_SERVICE_REQUIRED`).

Vincolo esplicito dell'utente: una sola opportunità concreta e vendibile subito, non la più elegante tecnicamente. Kill criterion: 1 offerta → 10 prospect → outreach manuale approvato → misurazione risposte/interesse/vendite, niente altro.

## Target e prospect

Micro-segmento: piccole web agency italiane (1-10 persone) che vendono siti/SEO/Google Ads a PMI. 10 prospect reali verificati via ricerca web pubblica (nessun dato inventato), ranked per fit 0-100.

**Top 3 scelti per il primo outreach:**
1. **PNT Solutions** — Gabriele Pantaleo, Torino.
2. **Orto Creativo** — Christian Paggiarin, Treviso.
3. **Eccolo Marketing** — Nicoletta e Valentina Russo, Ciampino.

Per ciascuno dei 3: lead demo (potenziali clienti reali per loro) riqualificati con trigger commerciali concreti e verificati (es. sito non aggiornato, dominio morto, nessuna presenza propria) — non semplicemente "l'azienda esiste". Pitch scritti con tono umano (niente linguaggio da agenzia AI), CTA soft ("ti mando 2-3 esempi gratis?"), corretti due volte su richiesta dell'utente (wording PNT ammorbidito su "sito irraggiungibile", wording Orto Creativo reso più cauto).

## Outreach — stato reale

| Prospect | Ora invio | Canale | Esito |
|---|---|---|---|
| PNT Solutions (Gabriele Pantaleo) | 2026-10-05 19:48 | Gmail — bozza creata da Claude via connettore Gmail Anthropic, **invio eseguito manualmente dall'utente** | In attesa di risposta |
| Orto Creativo (Christian Paggiarin) | — | — | Non contattato — in coda, solo dopo esito PNT |
| Eccolo Marketing (Nicoletta/Valentina Russo) | — | — | Non contattato — in coda, solo dopo esito Orto Creativo |

Sequenza concordata esplicitamente: PNT → osserva → Orto Creativo → osserva → Eccolo Marketing → osserva → eventuali altri 7 prospect solo con un segnale positivo reale. Nessun follow-up automatico pianificato o eseguito.

## Policy di approvazione applicata

Task eseguita sotto un gate esplicito: canale verificato + contesto re-verificato + oggetto/testo finale mostrati all'utente **prima** di ogni invio; nessun invio senza un "sì, invia"/istruzione equivalente esplicita. Per PNT, la bozza è stata preparata da Claude ma l'invio effettivo è stato fatto dall'utente di persona in Gmail, non tramite tool — scelta dell'utente, non un fallimento del gate.

## Nota tecnica: setup connettore Gmail (risolta)

Un primo tentativo di collegare Gmail tramite `claude mcp add --scope user gmail <URL indovinato>` ha creato una voce MCP parallela che falliva l'OAuth ("Incompatible auth server: does not support dynamic client registration") **e oscurava** il vero connettore Gmail di Anthropic, già autorizzato in precedenza dall'utente nelle impostazioni Connettori dell'app. Fix: `claude mcp remove --scope user gmail`, poi riavvio sessione (le modifiche a `claude mcp add/remove --scope user` non si applicano a un processo già in esecuzione) — dopo il riavvio il connettore corretto (`mcp__claude_ai_Gmail__*`, con `send_message`/`create_draft` reali) è apparso automaticamente, nessuna configurazione manuale aggiuntiva necessaria.

## Evidenza/test

Nessun test automatico applicabile (esperimento di business reale, non codice). Evidenza = i prospect stessi (fonti pubbliche verificate, non inventate) e il mini-log di tracking sopra, aggiornato con dati reali via via che arrivano risposte.

## Limiti dichiarati

- Nessuna risposta ricevuta ad oggi (2026-10-05) da PNT Solutions — zero segnale di validazione di mercato finora, solo un primo contatto inviato.
- Il lead PNT **non è ancora registrato** in `FirstRevenueStore` ([[NEXUS TASK 0010 - First Revenue Execution V1 (Codex)]]) — gap noto tra l'esperimento manuale e il bookkeeping automatico di Codex, non ancora riconciliato.
- Delivery (produzione reale dei 15-20 lead per il cliente, se arriva una vendita) non è ancora stata progettata in dettaglio — resta un passo successivo, condizionato a un "sì" di un prospect.

## Blocker

Nessuno attivo — in attesa pura di risposta umana esterna (Gabriele Pantaleo), non di alcuna azione interna.

## Prossimo passo

Attendere la risposta di PNT Solutions. Solo dopo un esito (positivo o negativo) si procede con Orto Creativo. Nessuna azione autonoma nel frattempo.
