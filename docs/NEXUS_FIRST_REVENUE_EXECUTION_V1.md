# NEXUS First Revenue Execution V1

Minimal, local-first path:

`OPPORTUNITY → OFFER → LEAD → OUTREACH → DELIVERY → PAYMENT → REVENUE → LEARNING`

The existing Funding Framework remains the authority for opportunity scoring, evidence,
hard gates and lifecycle. This milestone adds only the missing operational bookkeeping:
Offer, Lead, observed Revolut Payment and Revenue records.

Delivery execution is deliberately not duplicated: an approved lead may reference a normal
NEXUS Queue task, which remains governed by Router, verifier and Approval Gate. Learning
continues through the existing Funding Framework learning records; Revenue is an observed
input to that process, not an automatic claim that an offer is validated.

## Safety boundaries

- No CRM, bank API or autonomous money movement.
- `CONTACTED` requires an explicit human approval record bound to a message fingerprint.
- A price not explicitly reviewed remains `DRAFT`.
- `PAID` requires an observed external reference; Revenue requires `PAID`.
- Market Scout receives only supplied evidence, has network/outreach/payment disabled and
  cannot choose the business, final target or final price.
- Codex review checks schema and grounding only. Commercial decisions remain human/Jarvis
  governance decisions.

## Real bounded local evaluation

`run_market_scout_example.py` submits the compiled task through the existing Orchestrator,
which selected `LOCAL_STRONG_MINISTRAL3B`. The first response failed deterministic validation
because `missing_info` exceeded the two-item limit. The canonical retry ran once, passed, and
the technical review found both evidence strings grounded in the supplied facts. The preserved
evaluation artifact is `first_revenue_market_scout_example_v1.json`; it is explicitly not a
business decision, outreach approval, payment authorization or evidence of market demand.

## Backlog outside first revenue

Automated prospect discovery, CRM synchronization, bank reconciliation, invoicing,
contracts, autonomous outreach, recurring billing and optimization are intentionally absent.
