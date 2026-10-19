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

1. **Deterministic** — run `python3 scripts/edge_freeze_check.py` and
   `python3 -m unittest server/research_scripts/phase7/phase7_28_defect_impact_batch/test_phase_7_28.py`.
2. **Done in Phase 7.28** — same-feed A/B for BAR_UPDN (MATERIAL) + BB_SQUEEZE (LOW);
   TF guards applied to all remaining persistent-state DEFECT_CONFIRMED; TSI registry reconciled.
   Artifacts: `server/research_scripts/phase7/phase7_28_defect_impact_batch/`.
3. **Done in Phase 7.29** — LIQ_SWEEP OOS failure mode: `HABITAT_REGIME + SETUP_MIX_SHIFT`
   (not execution bug). Stays CANDIDATE / regime-conditional.
   Artifacts: `server/research_scripts/phase7/phase7_29_liq_sweep_oos_failure/`.
4. **Phase 7.30 confirmatory package ready** — hypothesis `LIQ-SWEEP-BUY-TREND-RM-001`
   prereg frozen; exploratory replay **NOT_PROMOTABLE** (`DISCOVERY_REUSE`).
   Confirmatory forward window **2026.09.28–2026.10.19** prepared
   (`PREPARED_AWAITING_WINDOWS_MT5`). Launch/collect/analyze + Windows runbook:
   `server/research_scripts/phase7/phase7_30_liq_sweep_buy_trend/`
   (`RUNBOOK_CONFIRMATORY_WINDOWS.md`). Cloud cannot run MT5 — research PC only.

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
