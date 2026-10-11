# Research Intelligence V1 (RI-01)

Status: proposal layer, manual use only. No schedule, no daemon, no network, no model call.
Code: `server/research_scripts/research_intelligence_v1/` · Contract: `contracts/research-memory-v1.schema.json`
Tests: `server/tests/test_research_intelligence_v1.py` · Seed memory: `research_intelligence_v1/memory/research_memory_v1.jsonl`

RI-01 lets NEXUS research learn from its own experiments: every concluded experiment is reviewed by fixed
rules, problems become classified improvement proposals, results become new hypotheses, and everything is kept
in one append-only scientific memory shared by all strategy families and, through `project`, by future
companies. It proposes; it never applies. Masterplan §25 still holds: research agents may compare evidence,
identify missing tests and generate hypotheses; they may not promote a strategy or alter live parameters.

## 1. Architectural inventory and reuse

| Need | Already in the repo | RI-01 decision |
|---|---|---|
| Hypothesis / experiment / exposure / failure registries | `phase7/phase7_26/*.json`, read by `server/research_control_plane.py` | **Imported read-only** (`ingest.import_phase7_26`), each record cites file + sha256. Registries stay the source; nothing is rewritten. |
| Dedup of hypotheses | `phase7/engine/candidate_signature.py` (deterministic, no semantic AI, by §24) | **Reused as is** for every hypothesis signature. |
| Lifecycle vocabulary | phase7_26 lifecycle (OBSERVATION → … → SUPPORTED/REJECTED/INCONCLUSIVE) | **Reused**; generated hypotheses cannot start beyond HYPOTHESIS. |
| Failure taxonomy | `failure_map_v1.json` (18 modes) | **Reused** as schema enum. |
| Split access | `phase7/policies/validation_access_policy_v1.json` | **Reused** by `gates.protected_splits()`: one-shot splits are never queued or read automatically. |
| Priority criteria | `research_priority_queue_v1.json` (8 criteria, unweighted 1-5, PF never a criterion) | **Reused** + 4 declared criteria (contamination, compute, data availability, ecosystem relevance). |
| Append-only, hash-chained log | `orchestrator_v1/core/ledger.py`, trade event chain | **Same pattern**, own file: research memory is not task state and not trading state (doc 18 §11 keeps those ledgers separate). |
| JSON-schema validation | `orchestrator_v1/nxs_schema_validator.py` (stdlib) | **Reused**; no new dependency. |
| Behavior Lab runs | `behavior_lab_v1` (PR #39) `summary.json` | **Adapter** `ingest.import_behavior_lab_summary`. |
| Learning records for code reviews | `review_pipeline_v1/learning_telemetry.py` | Different domain (code-task outcomes). Not merged, not duplicated. |
| Strategy claim strength | `knowledge/evidence_engine.py` | Evidence levels here are aligned in spirit (never PF-based); no second claim engine. |

Duplications found and **not** created: no second hypothesis registry (phase7_26 remains the curated source,
memory is the cross-family index with relations and reviews), no second signature algorithm, no new agent
runtime, no second access policy.

## 2. Research Memory (`memory.py`, schema `research-memory-v1`)

One JSONL file, one record per line, record types `EXPERIMENT`, `HYPOTHESIS`, `OBSERVATION`, `REVIEW`,
`IMPROVEMENT_PROPOSAL`, `PRIORITIZATION`. Every record has provenance (file/commit/PR/run with sha256),
typed relations (`TESTS`, `DERIVED_FROM`, `ALTERNATIVE_TO`, `CONTRADICTS`, `SUPPORTS`, `SUPERSEDES`, …),
`origin` (`HUMAN`, `REGISTRY_BACKFILL`, `RULE_ENGINE`, `AI_PROPOSAL`), `prev_hash` and `record_hash`.

- Experiment body: hypothesis and version, datasets with hash / split / exposure, method with params sha256,
  code commit, preregistration, control and multiple-testing family, metrics, data checks, resources, limits,
  anomalies, alternative explanations, conclusions, failure modes, evidence level, decision.
- No update, no delete: a correction is a new record that `SUPERSEDES` the old one; the old one stays
  readable. `verify()` detects any rewritten or removed line.
- Relations must point to existing records. Duplicate ids are refused.
- **Gates live in the store**: `memory.append` runs `gates.check_record` on every record, whatever the caller
  (register, review, decide or a raw append), and `verify()` replays the same checks on every line, so a
  hand-edited file that breaks a gate is reported too.
- **External checkpoints** (`research_memory_v1.checkpoints.jsonl`, append-only, itself hash-chained): each entry
  stores `{count, head_hash}`. The chain alone cannot see a removed last record or a chain recomputed from
  scratch; a checkpoint can. Both files are committed, so git history is the outer anchor: undoing a
  checkpointed record means editing an older checkpoint line, which is a visible diff and breaks the checkpoint
  chain. Run `cli checkpoint` after each session that adds records, before committing.
- Evidence levels: `NONE_PROPOSAL < EXPLORATORY < DISCOVERY_ONLY < MECHANICAL_VERIFICATION <
  INTERNAL_VALIDATION < LOCKED_VALIDATION < INDEPENDENT_FORWARD`. AI or rule proposals are always
  `NONE_PROPOSAL`.

## 3. Post-experiment review (`review.py`, rules `RI_REVIEW_RULES_V1`)

Tier 0 of doc 18 (deterministic). Areas and checks:

| Area | Checks |
|---|---|
| DATA_QUALITY | dataset hash missing, failed data checks, detector firing status not NORMAL |
| METHODOLOGY | params/commit missing, confirmatory level without prereg, no control, no multiple-testing family, open implementation defect |
| CAUSALITY_LEAKAGE | one-shot split read, exposed data used as confirmation, exposure unknown |
| STATISTICAL_POWER | n < 30 closed, CI crossing zero, LOW_SAMPLE failure mode |
| RESOURCES / TOOLING | slow or heavy run, resources not recorded |
| INFORMATION_VALUE | negative/inconclusive without alternative explanations, unexplained anomalies |

Each finding is classified `PROCESS_IMPROVEMENT`, `NEW_HYPOTHESIS`, `DEFECT_FIX`, `INSUFFICIENT_EVIDENCE`
(or `NONE`). Each actionable finding becomes one `IMPROVEMENT_PROPOSAL` with id `PROP-<check>-<hash(family,check)>`:
an open proposal for the same family and check is linked, not duplicated. At most 10 proposals per review.
Same rules version + same experiment = same review id: re-running writes nothing.

## 4. Improvement proposal registry (`proposals.py`)

`PROPOSED → ACCEPTED | REJECTED`, `ACCEPTED → IMPLEMENTED | REJECTED`, `IMPLEMENTED → REVERTED`.
Each transition is a new record (`<id>.D<n>`, `SUPERSEDES`) with `decided_by` a person: decisions by
`rule*`, `ai*`, `jarvis*`, `auto*` are refused. Requirements per class (enforced by `gates.check_proposal`):

- DEFECT_FIX: deterministic reproduction + regression test + impact analysis.
- NEW_HYPOTHESIS: new preregistration under a new id.
- PROCESS_IMPROVEMENT touching method: validation on a dedicated test, never on protected results.
- Anything mentioning EA, MQL5, live, risk or deploy must be flagged `touches_frozen_or_live` and needs human approval.
- Every proposal is reversible and carries a revert plan.

## 5. Hypothesis generation (`generator.py`, `hypotheses.py`)

Triggers read observations and results and emit candidate specs from declared templates. Each candidate declares
mechanism, falsification, data needed, overfitting risk and expected information value (missing → refused). All
candidates go through signature dedup and a per-family budget (default 6 hypotheses): refusals are reported, not
dropped silently. A model can propose through the same `register_candidates` path with origin `AI_PROPOSAL`.
Templates available now: `LOW_SELECTIVITY` (pullback filter that barely selects). Price/session, volatility,
liquidity, macro and literature triggers are added as templates the same way.

## 6. Priority queue and anti-contamination (`priority_queue.py`)

Excluded before ranking, with reason recorded: lifecycle past HYPOTHESIS, data not available (caller declares
availability; nothing is fetched), data on a one-shot split. Ranking: 12 criteria, simple sum. Budget recorded with
every queue: per-family hypothesis cap, family alpha 0.05 split by Bonferroni over the family,
`max_runs_without_approval = 0` — the queue orders work, a person starts it.

## 6b. Learning loop (`lessons.py`)

`cli brief FAMILY` gives what memory already knows before the next experiment: refuted hypotheses and
negative results, failure modes seen, data already exposed, open proposals by class, remaining budget, per-test
alpha. The queue uses it: a family with an open DEFECT_FIX is held until a person marks the fix
IMPLEMENTED or REJECTED. Reviews link to proposals already open instead of repeating them; budgets and novelty
count what is already in memory.

### Operational today vs designed only

| Capability | Status |
|---|---|
| Review a concluded experiment, find data/method/leakage/power/resource problems | **Operational** (fixed rules, run on request) |
| Classified, traceable proposals (provenance = review record + experiment hash) | **Operational** |
| Falsifiable hypotheses from results | **Operational for declared templates** (LOW_SELECTIVITY); other triggers designed |
| Dedup and useless variants | **Operational** (signature dedup, family budget, Bonferroni alpha) |
| Record what was learned | **Operational** (append-only memory, decisions as records, checkpoints) |
| Use it in the next research | **Partly operational**: briefing, open-defect hold, novelty/budget from memory. Not automatic: accepted process improvements do not rewrite review rules or preregistrations; a person applies them in a PR |
| Automatic triggering after each run | **Not enabled by design** (no schedule); `ingest-bl01` reviews immediately when called |
| Model-written hypotheses (Tier 1–3) | **Designed**: same `register_candidates` path, no model wired |

## 7. Safety gates (`gates.py`)

| Rule | Where |
|---|---|
| No change to frozen params | store refuses a preregistered experiment whose params sha differs from an earlier one of the same hypothesis; a revised hypothesis must keep its signature |
| No automatic protected-holdout access | store refuses non-human experiment records on one-shot splits; queue exclusion; review BLOCKER |
| No promotion on discovery alone | store refuses SUPPORTED below INTERNAL_VALIDATION (MECHANICAL_VERIFICATION only for code/data claims flagged as such in phase7_26); generated hypotheses stay NONE_PROPOSAL; lifecycle changes need HUMAN origin |
| No self-approval | store refuses decided proposals unless origin HUMAN, a human `decided_by`, and SUPERSEDES the proposal. The name is declared, not authenticated: the real control is that memory changes land only through a reviewed PR |
| No live risk increase / EA change | `check_proposal` live markers + human approval; package has no MT5, order or network code (tested) |
| No deletion of negative evidence | append-only chain + `negative_evidence_preserved` |
| No unlimited self-modification | proposals only, max 10 per review, human decisions, budgets |
| Every improvement reversible | revert plan required; `REVERTED` transition |
| Reproducible, auditable | rule versions, input hashes, provenance sha256, `verify()` |

## 8. Agent roles (logical, mapped to existing tiers — no new agents)

| Role | Implementation today | Escalation (doc 18) |
|---|---|---|
| Research Memory Curator | `memory.py`, `ingest.py`, `pilot.py` (Tier 0) | none needed |
| Improvement Reviewer | `review.py` rules (Tier 0) | Tier 2 local strong for narrative, Tier 3 Claude for design questions |
| Data Quality Auditor | review DATA_QUALITY rules + behavior_lab data checks | Tier 2 |
| Statistical Reviewer | review STATISTICAL_POWER rules + `phase7/engine` diagnostics | Tier 3 for new designs |
| Strategy Researcher / Market Researcher | `generator.py` templates; models propose via `register_candidates` (`AI_PROPOSAL`) | Tier 1–3 by context size |
| Research Director | `priority_queue.py` ranking; the human starts runs | human |

Roles bind to entries of `AGENT_CAPABILITY_REGISTRY_V1` (LOCAL_*_MINISTRAL3B, CLAUDE_TIER3, CODEX_TIER4) when a
task needs a model; premium agents stay escalation, never default. `project` keeps memories of different
companies apart while sharing the same schema and tooling.

## 9. BL-01 pilot

Seeded in the committed memory:

- `HYP-BL-H4M15-IPC-001` — preregistered, HUMAN, params sha `7c66d51c…`, commit `613a9a8` (PR #39). Not modified.
- `OBS-BL-H4-SELECTIVITY-2019-2022` — 183 impulses (3.81% of 4809 H4 bars), 167 pullbacks, conversion 0.913,
  both detectors NORMAL, on MARKET_STATE_V1 (2019-02..2022-02, `outside_splits`, `DISCOVERY_REUSE`).
  `EXPLORATORY`, explicitly **not evidence for** the hypothesis, its parameters or any BL-01 split.
- `EXP-BL-01-DISCOVERY` — NOT_RUN placeholder (tick data only on the research PC).
- Five generated alternatives (`ALT-DEEP-PB`, `ALT-ATR-PB`, `ALT-2BAR-IMPULSE`, `NULL-NO-PB`, `ALT-MACRO-WINDOW`),
  all `NONE_PROPOSAL`, `ALTERNATIVE_TO` the preregistered one; the sixth (`ALT-SESSION-OVERLAP`) was refused by the
  family budget. `ALT-MACRO-WINDOW` stays out of the queue until a historical macro calendar exists.
- Reviews of the 9 phase7_26 experiments and of the BL-01 placeholder, with their proposals.

### Ingesting the real BL-01 report (research PC)

```bash
cd server/research_scripts
python -m research_intelligence_v1.cli ingest-bl01 <run_dir>/summary.json   # adds EXP, SUPERSEDES the placeholder, reviews it
python -m research_intelligence_v1.cli queue --available DUKASCOPY_XAUUSD_TICKS_2022-11_2024-08 --dry-run
python -m research_intelligence_v1.cli checkpoint --note "BL-01 discovery ingested"
python -m research_intelligence_v1.cli verify
```

Then commit the memory file in a PR. Next improvement cycle: a person reads the review, decides proposals
(`proposals.decide`), and preregisters any alternative under its own id before any run.

## 9b. BL-01 power and BL-02

Power verification of BL-01 under its own decision rule, the H4-frequency vs trade-count distinction, and the
BL-02 draft (unseen 2008-2018 data, same frozen hypothesis) are in `docs/BL01_POWER_AND_BL02_PROPOSAL.md`.

## 10. Research loop (RI-02)

The cycle that drives these modules (state machine, authorization, planning, improvement evaluation) is in
`docs/RESEARCH_LOOP_V1.md`.

## 11. Not done in V1

- Real BL-01 discovery numbers (data only on the research PC).
- Macro, liquidity and literature triggers (templates to add; no paid data or API).
- UI projection in the Research Control Plane (read model can consume the JSONL as is).
