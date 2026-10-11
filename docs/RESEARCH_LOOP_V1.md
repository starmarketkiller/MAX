# Research Loop V1 (RI-02)

Status: implemented, run on request only. There is no scheduler, no network access and no model call.
It builds on `docs/RESEARCH_INTELLIGENCE_V1.md` (RI-01).

- Code: `server/research_scripts/research_intelligence_v1/`: `loop.py`, `authorization.py`, `approval_bridge.py`,
  `planner.py`, `overfitting.py`, `evaluation.py`, `agents.py`
- Tests: `server/tests/test_research_loop_v1.py`
- Contract: `contracts/research-memory-v1.schema.json`, extended additively

The goal of the loop is better research, not more strategies. A cycle counts as successful when it produces
information: findings, eliminated hypotheses, errors caught, duplicates avoided, plans that are worth running.
The number of backtests is reported only as a cost.

## 1. Audit: what is reused and what is new

| Need | Reused | New in RI-02 |
|---|---|---|
| Persistent, verifiable state | RI-01 Research Memory: append-only, hash chain, external checkpoints, gates enforced inside the store | Record types `LOOP_TRANSITION`, `EXPERIMENT_PLAN`, `ACTION`, `EVALUATION`, `IMPROVEMENT_TRIAL` (additive schema extension) |
| Review, generation, dedup, budgets, queue, briefing | RI-01 `review`, `generator`, `hypotheses`, `priority_queue`, `lessons` | Triggers that work on any family (`spec_from_record`); ablation trigger |
| Approval of real-data work | Orchestrator V1 `TaskQueue` ACCEPT_ONLY path: Jarvis decides it, the dispatcher never claims it, `Orchestrator` refuses to execute it. `EventLedger` `APPROVAL_REQUIRED` event | `TaskQueue.submit_accept_only_proposal` (additive, atomic: created directly in WAITING_APPROVAL) and `approval_bridge.py` |
| Post-hoc control | `phase7/engine/post_hoc_quarantine.py` | Called by `overfitting.POST_HOC` |
| Split access | `phase7/policies/validation_access_policy_v1.json` via `gates.protected_splits` | none |
| Agents | `orchestrator_v1/agent_capability_registry_v1.json` | `agents.py` maps roles to existing agents; no new agent |
| Statistics | Bonferroni over the correlated family for planning; FDR at run time stays in `phase7/engine/multiple_testing_v2.py` | Synthetic power analysis (stdlib, bounded) as an AUTO_SAFE dry run |

| Candidate evidence path | `phase7/engine/candidate_lifecycle.py` (GENERATED → … → SUPPORTED), the "Discovery Engine v2" that `EXTERNAL_TRADING_SYSTEMS_REUSE_GAP_ANALYSIS_V1.md` names for the R→D loop | Not duplicated. That state machine moves one candidate when a real run produces evidence. The loop is the process cycle around it and never moves a candidate (PROMOTE_STRATEGY is PROHIBITED) |
| Business loop | `funding_v1/self_funding_loop.py` | Different domain (revenue opportunities). Not touched |

Not created: a second orchestrator, a second approval system, a second ledger, a new statistical engine, a scheduler.

## 2. State machine

```
CYCLE_OPENED -> OBSERVE -> REVIEW -> LEARN -> HYPOTHESIZE -> PRIORITIZE -> PLAN -> EXECUTE -> EVALUATE -> CYCLE_CLOSED
                  (each step: STARTED -> COMPLETED | FAILED; at most 3 attempts, then CYCLE_ABANDONED)
```

| Step | Owner role | What it does |
|---|---|---|
| OBSERVE | research-memory-curator | Integrity check of the memory (the loop halts if `verify()` fails). Ingests reports given in `--inbox` (AUTO_SAFE), reads approval decisions from the orchestrator queue, and lists experiments not yet reviewed |
| REVIEW | improvement-reviewer | Runs `review.review` on each of those experiments. Proposals now carry a `baseline` and a `success_criterion` |
| LEARN | statistical-reviewer | Writes the improvement trials (baseline and result) and the per-family briefings |
| HYPOTHESIZE | strategy-researcher | Runs the triggers: low selectivity, and ablation after an INCONCLUSIVE or NEGATIVE result with no alternative explanation. Applies dedup, the family budget and a per-cycle cap. A source already mined is not mined again |
| PRIORITIZE | research-director | Runs `priority_queue.build_queue` |
| PLAN | research-director + statistical-reviewer | Drafts preregistrations for the top candidates, within the cycle budget |
| EXECUTE | safety-gate | Classifies every action. Runs only AUTO_SAFE runners, sends APPROVAL_REQUIRED actions to the approval bridge, refuses PROHIBITED ones |
| EVALUATE | improvement-evaluator | Writes the cycle metrics as an `EVAL-<cycle>` record and a memory checkpoint |

How the loop survives interruptions:

- **Resume:** the open cycle continues from the first step that has no COMPLETED record.
- **Crash reconciliation:** a STARTED step with no outcome is first recorded as `FAILED: interrupted`, then retried.
- **Idempotency:** every write has a deterministic id (review, plan, action, trial, evaluation), and approval requests use the action id as their idempotency key. A retried step therefore never duplicates anything.
- **Auditability:** each transition stores the memory head it started from, so the sequence can be checked.

## 3. Authorization (`authorization.py`, enforced in code)

| Mode | Actions | What the loop does |
|---|---|---|
| AUTO_SAFE | INGEST_AVAILABLE_REPORT, REVIEW_EXPERIMENT, INTEGRITY_CHECK, DEDUP_CHECK, GENERATE_PROPOSALS, SYNTHETIC_DRY_RUN (≤ 60 s, ≤ 100k rows) | Runs it, only through `loop.AUTO_RUNNERS` |
| APPROVAL_REQUIRED | RUN_EXPERIMENT_REAL_DATA, EXPENSIVE_COMPUTE, NEW_VARIANT, METHOD_CHANGE, RESTRICTED_DATASET_ACCESS, EXTEND_FAMILY_BUDGET; also anything using real data, more than 30 minutes of compute, or an authorized dataset | Creates an ACCEPT_ONLY task in the orchestrator queue. Approval records consent only: the run itself stays manual, on the research PC |
| PROHIBITED | READ_PROTECTED_SPLIT, MODIFY_PREREGISTERED_PARAMS, LIVE_TRADING, CHANGE_OPERATIONAL_RISK, PROMOTE_STRATEGY, MODIFY_SAFETY_COMPONENT; also any action that touches a one-shot split, changes preregistered parameters, requests promotion, or mentions the EA, live trading or risk settings | Recorded as REFUSED |

How the modes are enforced:

- Unknown action kinds are PROHIBITED: the classifier fails closed.
- Dynamic checks can only make a mode stricter (tested over the whole catalog).
- The memory gate recomputes the classification for every `ACTION` record. A record whose mode does not match, or whose status is impossible for its mode (an executed APPROVAL_REQUIRED action, an approval request with no orchestrator task), is refused, and `verify()` reports it if it was written by hand.

## 4. Planning and learning without overfitting

`planner.plan_cycle` reads the queue and, within the per-cycle budget (default 2 plans, 1 per family):

- **Skips repeated work:** plans already made (exact key: signature, dataset, split, period), experiments already run, and plans that are substantially equivalent to existing ones (same event, direction, features and operators, every threshold within 5%).
- **Reuses earlier lessons:** if an earlier cycle's synthetic power analysis found a dataset underpowered at the same expected sample, it does not plan on that dataset again ("learned from ACT-…").
- **Runs the overfitting checks** (`overfitting.py`):

| Check | Rule |
|---|---|
| PERIOD_REUSE | Same dataset and period used 3 times → WARN; more → BLOCK |
| MULTIPLE_TESTING | Per-test alpha = 0.05 / max(hypotheses in the correlated family, tests run or planned) |
| CORRELATED_LEAKAGE | ALTERNATIVE_TO, DERIVED_FROM and REFINES relations make one alpha family |
| PROTECTED_SPLIT | One-shot splits → BLOCK |
| POST_HOC | A hypothesis derived from some data cannot be tested on that data. Implemented with `post_hoc_quarantine` |
| EVIDENCE_CLASS | Discovery reaches at most DISCOVERY_ONLY. A generated hypothesis is first tested on discovery |

- **Statistical review:** the reviewer rejects plans with a BLOCK check, no falsification criterion, no mechanism, or fewer than 30 expected events.
- **The resulting plan:** a passing plan becomes a `DRAFT_PREREGISTRATION` with a decision rule, an alpha and a minimum sample, and three actions: dedup check, synthetic power analysis, real-data run.
- **Underpowered plans:** if the power analysis finds the plan underpowered, the real-data run is refused with the numbers, so no approval is requested.
- **AI output is not evidence:** generated hypotheses and AI results are never counted as evidence. Gates keep them NONE_PROPOSAL, and the metric `ai_or_rule_results_counted_as_evidence` is fixed at 0.

## 5. Did research improve? (`evaluation.py`)

**Cycle metrics (`EVAL-<cycle>`):**

- new information (findings by area, experiments, observations);
- hypotheses eliminated, strengthened or left inconclusive;
- errors identified;
- duplicates avoided (hypotheses, linked proposals, equivalent plans);
- plans skipped because of an earlier finding;
- resources per step;
- proposal quality (mechanism and falsification declared, share passing statistical review);
- conclusion reliability (share of confirmatory evidence);
- actions by mode.

**Improvement trials:**

- Every proposal's metric is the rate of reviewed experiments in its family that show its finding.
- BASELINE is recorded when a person accepts the proposal.
- RESULT is recorded after at least 3 experiments reviewed after the IMPLEMENTED decision. These are independent of the baseline set.
- Success means the rate drops by at least 50%. The verdict is `IMPROVED`, `NOT_IMPROVED` or `INSUFFICIENT_EVIDENCE`, and failed improvements stay in memory.

## 6. Agent collaboration (`agents.py`)

The roles are research-director, research-memory-curator, improvement-reviewer, data-quality-auditor,
strategy-researcher, market-researcher, statistical-reviewer, safety-gate and improvement-evaluator. They are shared
services for every family and every company (the `project` field travels in the records).

- Every role runs deterministic code by default.
- Escalation targets are existing registry agents (CLAUDE_TIER3, LOCAL_STRONG_MINISTRAL3B), reached only through the
  orchestrator and never called automatically.
- No paid API is required.
- `validate_roles()` checks the mapping against the registry.

## 7. Pilot results (BL-H4M15, synthetic catalog estimate)

The loop was run on a copy of the RI-01 seed memory, with a declared catalog for the BL discovery split (no tick data was read).

- **Plans:** it planned `NULL-NO-PB` first (highest information value), with per-test alpha 0.0083 over the 6-hypothesis family.
- **Power:** synthetic power analysis gave power ≈ 0.24 at about 80 expected events. About 372 events are needed to detect a +8 pp effect on `p_target_first`.
- **Real-data run refused:** the real-data run was refused as underpowered, and the next cycle did not plan the siblings on the same dataset.
- **Implication for BL-01:** the preregistered discovery window (2023-02..2024-08) is probably too short to detect an effect of that size. This is a design question for a person (extend the period under a new preregistration, or state a larger minimum effect). The loop did not change BL-01.

## 8. Usage

```bash
cd server/research_scripts
python -m research_intelligence_v1.cli roles
python -m research_intelligence_v1.cli loop-status
python -m research_intelligence_v1.cli loop-run --available ID --catalog catalog.json [--inbox run/summary.json]
#   catalog.json: {"<data_needed id>": {"dataset_id", "split", "period", "real_data", "estimated_seconds",
#                                       "expected_events", "requires_authorization"}}
#   --no-approval-channel: refuse APPROVAL_REQUIRED instead of queueing it
```

Approval requests appear in the orchestrator queue as `TASK_RI_*` in WAITING_APPROVAL. A person approves or rejects them
through the existing Jarvis ACCEPT_ONLY path, and the next cycle reads the decision in OBSERVE.

## 9. Limits

- **Expected events are declared, not measured:** they come from the catalog, so the power analysis is only as good as that estimate.
- **The loop never runs real experiments:** approval records consent, and a person runs Behavior Lab and gives the summary back via `--inbox`.
- **Two trigger families only:** low selectivity and ablation. Macro, liquidity and literature triggers are designed, not built.
- **Improvement metrics are finding rates:** an improvement that changes something reviews do not measure needs its own metric.
- **Bonferroni is conservative** by design.
- **Decisions are not authenticated:** a decision record names a person but is not signed. Memory changes still land through reviewed PRs.
- **Single process:** the orchestrator queue is single-process V1.
