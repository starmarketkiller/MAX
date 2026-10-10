# NEXUS TASK #0012 — Lead Research Cycle V1

Il primo ciclo che può incassare. Non è il trading e non è Agency.

Offerta: `OFFER_LEAD_RESEARCH_25`, 15–20 lead con fonte https, 25 EUR.
Il servizio non invia posta e non muove denaro.
Un pagamento entra solo con un riferimento Revolut osservato, e solo dopo un sì (`INTERESTED`) e il pacco già allegato.

Rotte, dietro login:

- `GET /api/revenue/lead-research/status`
- `POST /api/revenue/lead-research/open`
- `POST /api/revenue/lead-research/delivery`
- `POST /api/revenue/lead-research/payment`

PNT non è stato marcato `CONTACTED`: nel vault non c'è l'impronta del messaggio né la ricevuta Gmail. Inventarle avrebbe falsificato l'invio.

Test: `server/tests/test_lead_research_cycle_v1.py`.
Non è in produzione finché questo branch non viene deployato.
