# Edge Credit-Safe Operating Loop V1

Date: 2026-10-19. One page. No new orchestrator. No new agent stack.

**Goal:** reach a confirmable edge (or an honest fail) without burning premium
agent credits on work that should be free, local, or deterministic.

## Honest diagnosis

You already designed the right structure. It lives here:

| Piece | Where |
|---|---|
| Premium = escalation only | `docs/architecture/18_ORCHESTRATOR_AGENT_ROUTING_V1.md` |
| Local coding worker boundary | `docs/NEXUS_FREE_CODING_WORKER_V1_ROUTING_HARDENING.md` |
| Research cycle (no scheduler) | `docs/RESEARCH_LOOP_V1.md` |
| Power before claims | `docs/NEXUS_POWER_GATE_V1.md` |
| Local model pick for your PC | `server/orchestrator_v1/model_recommendation_v1.json` |

What was missing was not another architecture. It was an **operating loop**
that refuses expensive work until cheaper tiers are exhausted, and a **freeze**
so defective ACTIVE strategies stop consuming attention.

## Default routing (use this every time)

```
1. DETERMINISTIC script / pytest / registry rebuild / git blame
2. LOCAL Ollama (Qwen2.5 3B fast / 7B coding) via Orchestrator
3. Premium agent ONLY if:
   - scientific adjudication, OR
   - multi-file complex code after local fail+classify, OR
   - human explicitly escalates
```

Never open a premium session to: rebuild a registry, parse logs, recompute
metrics, write boilerplate, re-explain the same Phase 7 docs, or invent a
parallel “super agent system”.

## Live shortlist (attention budget)

Keep mental/agent focus on ≤6:

`FVG_CONT`, `LIQ_SWEEP`, `ORDER_BLOCK`, `BREAKOUT_ACC`, `Z_SCORE_BREAKOUT`, `EMA_PULLBACK`

Everything else: research-only until a defect is closed and power allows a claim.

## Freeze applied in this change

| Strategy | Action |
|---|---|
| `BB_SQUEEZE`, `TSI`, `SH_BMS_RTO`, `SILVER_BULLET` | `default_enabled=false` in edge registry + EA inputs default `false` |
| `FVG_CONT` SLReclaim provenance | `defect_status=REMEDIATED` (commits `50e9ec7`, `1ac0437`, `a225aa3`; code still has `CommonExposurePreflight`) |

Remediation ≠ edge. FVG_CONT stays `CANDIDATE`. Production remains **NO-GO**.

## Next three tasks (order fixed, cheap first)

1. **Deterministic** — run `python3 scripts/edge_freeze_check.py` in CI/local; fix any new DEFECT_BLOCKED that reappears as enabled.
2. **Local / scripted** — same-feed A/B/C impact measure for the remaining DEFECT_CONFIRMED strategies (harness already exists from Phase 7.9/7.13). No premium agent needed to *run* it; escalate only to interpret ambiguous causal results.
3. **One falsifiable experiment** — Contextual Edge Phase 1 on MACD (`docs/CONTEXTUAL_EDGE_DISCOVERY_V1_DESIGN.md`). Premium agent only for preregistration adjudication if the local plan fails the Power Gate / provenance checks.

Stop condition for each task: a Decision Card with GO / INVESTIGATE / STOP.
No card → no next premium session.

## What not to build now

- A second orchestrator, second research loop, or “auto everything” wrapper
- New strategies / new ICT families
- Live / prop attempts on the 28-strategy soup
- Spending premium credits to redesign this document

If a future automation pass is needed, it should only **wire** the existing
Tier-0→local→premium policy into one Jarvis/Orchestrator entrypoint — not
redesign the policy.
