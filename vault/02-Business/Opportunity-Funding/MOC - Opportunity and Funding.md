---
type: moc
domain: opportunity-funding
status: adopted
tags: [business, funding, opportunity, nexus]
created: 2026-09-29
updated: 2026-10-05
---

# 💰 Opportunity & Funding

Namespace canonico, non trading-specifico, per il Funding Priority & Opportunity
Framework di NEXUS — introdotto qui in **NEXUS TASK #0007** (spostato da
`01-Trading/`, dove era finito perché nato durante una sessione di ricerca
trading, ma riguarda l'intero progetto: qualunque opportunity di business, non
solo quelle derivate dal trading).

## Framework canonico

Adottato ufficialmente in NEXUS TASK #0007 (`FUNDING_FRAMEWORK_V1_ADOPTED`).
Codice canonico: `server/funding_v1/` — schemi in `contracts/opportunity*.schema.json`,
`contracts/capability-coverage.schema.json`, `contracts/opportunity-lifecycle.schema.json`,
`contracts/self-funding-loop.schema.json`. Stato di adozione machine-readable in
`server/funding_v1/framework_adoption_decision_v1.json`.

Due assi di priorità **separati per costruzione** — `FUNDING_PRIORITY` (genera
cassa presto) e `TECHNICAL_PRIORITY` (avanza il core NEXUS) — mai fusi in un
unico punteggio, con hard gates fail-closed che una priorità alta non può mai
bypassare (capitale, capacità mancanti, rischio legale/policy, dati insufficienti).

## Note in questo dominio

- **[[NEXUS TASK 0005 - Funding Priority and Opportunity Framework V1]]** — design
  originale: schema OPPORTUNITY_V1, motore di scoring a due assi, 5 opportunity
  di esempio.
- **[[NEXUS TASK 0006 - Funding Framework Completion and Hardening]]** — hardening:
  hard gates, capital scenarios, capability coverage, lifecycle a 13 stati,
  self-funding loop, opportunity brief per Jarvis, dataset esteso a 18 opportunity
  — dimostrato che NEXUS estende un framework progettato da Claude usando solo
  TIER0/Ministral, zero escalation premium.
- **NEXUS TASK #0007** (questo spostamento) — adozione formale + pulizia
  namespace Vault, nessuna modifica a schema/scoring/gate.
- **[[NEXUS TASK 0010 - First Revenue Execution V1 (Codex)]]** — bookkeeping
  operativo (Offer/Lead/Payment/Revenue) aggiunto al framework, lavoro
  parallelo di Codex (`01e6180`), nessuna modifica a scoring/gate.
- **[[NEXUS TASK 0011 - First Revenue Manual Experiment (Lead Research Service)]]**
  — primo test reale: `OPP_LEAD_RESEARCH_SERVICE` portato fuori da
  PROVISIONAL, 10 prospect verificati, primo outreach manuale inviato
  (PNT Solutions, 2026-10-05).

## Stato attuale (2026-10-05)

17 delle 18 opportunity restano PROVISIONAL/HYPOTHESIS_BASED, non validate.
**`OPP_LEAD_RESEARCH_SERVICE` è l'unica in test di mercato reale** (primo
outreach manuale inviato, esito ancora in attesa — vedi NEXUS TASK #0011).
Nessuna opportunity ha ancora generato revenue osservata. Prossimo passo
naturale per le altre 17: restare `next_cheapest_validation_step` dichiarato
per ciascuna, mai un'azione commerciale reale senza approval esplicita.

## Come compilarlo

Nuove opportunity, decisioni di validazione, risultati reali (che alimenteranno
in futuro il `learning_record` di ciascuna opportunity) vanno qui — una nota per
opportunity/decisione è meglio di un unico file infinito, `[[wiki-link]]` per
collegarle a questo MOC.
