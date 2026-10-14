"""Research loop: OBSERVE -> REVIEW -> LEARN -> HYPOTHESIZE -> PRIORITIZE -> PLAN -> EXECUTE -> EVALUATE.

State lives in Research Memory as LOOP_TRANSITION records (append-only,
hash-chained, checkpointed): the loop has no other state. That gives:
- interruption and resume: a new ResearchLoop on the same memory continues
  the open cycle from the first step without a COMPLETED transition;
- crash reconciliation: a STARTED without COMPLETED/FAILED is closed as FAILED
  ("interrupted") before the retry, so the history shows the crash;
- safe retries: every step is idempotent (deterministic record ids, dedup by
  signature and equivalence key, idempotent approval requests), at most
  MAX_ATTEMPTS per step, then the cycle is ABANDONED for a person to look at;
- verifiable transitions: each one cites the memory head it started from.

The loop runs once per call (`run_cycle`). It has no scheduler: running it
periodically is a separate decision for a person.
"""
from __future__ import annotations

import math
import random
import statistics
import time

from . import authorization, evaluation, id_resolver, ingest, lessons, planner, priority_queue, review
from .agents import STEP_OWNER
from .generator import register_candidates, selectivity_alternatives, spec_from_record
from .hypotheses import FamilyBudget
from .memory import canonical, sha256_file, sha256_text

STEPS = ["OBSERVE", "REVIEW", "LEARN", "HYPOTHESIZE", "PRIORITIZE", "PLAN", "EXECUTE", "EVALUATE"]
MAX_ATTEMPTS = 3
DEFAULT_CYCLE_HYPOTHESES = 4


class LoopHalted(Exception):
    pass


# ---- AUTO_SAFE runners: the only actions the loop ever executes ------------------------------------
def _run_integrity(memory, params):
    problems = memory.verify()
    return {"problems": problems[:20], "ok": not problems}


def _run_dedup(memory, params):
    key = params["equivalence_key"]
    same = [p["record_id"] for p in memory.of_type("EXPERIMENT_PLAN") if p["body"]["equivalence_key"] == key]
    return {"plans_with_same_key": same, "unique": len(same) <= 1}


def _run_synthetic_power(memory, params):
    """Bounded Monte Carlo on synthetic Bernoulli outcomes: is the planned sample able
    to detect the effect at the planned alpha? No market data involved."""
    n = params.get("expected_events")
    alpha = params["alpha"]
    p0, effect = params.get("null_rate", 1 / 3), params.get("effect", 0.08)
    p1 = p0 + effect
    nd = statistics.NormalDist()
    za, zb = nd.inv_cdf(1 - alpha), nd.inv_cdf(0.8)
    n_needed = math.ceil(((za * math.sqrt(p0 * (1 - p0)) + zb * math.sqrt(p1 * (1 - p1))) / effect) ** 2)
    if not n:
        return {"n_needed_for_80pct_power": n_needed, "simulated_power": None, "verdict": "UNKNOWN_SAMPLE"}
    rng = random.Random(int(params["seed"], 16))
    reps = max(1, min(400, params.get("rows", 20_000) // max(n, 1)))
    crit = p0 + za * math.sqrt(p0 * (1 - p0) / n)
    hits = sum(1 for _ in range(reps) if sum(rng.random() < p1 for _ in range(n)) / n > crit)
    power = hits / reps
    return {"expected_events": n, "alpha": alpha, "null_rate": p0, "effect": effect, "replications": reps,
            "simulated_power": power, "n_needed_for_80pct_power": n_needed,
            "verdict": "ADEQUATE" if power >= 0.8 else "UNDERPOWERED"}


AUTO_RUNNERS = {"INTEGRITY_CHECK": _run_integrity, "DEDUP_CHECK": _run_dedup,
                "SYNTHETIC_DRY_RUN": _run_synthetic_power}


# ---- hypothesis triggers (rule-based; models would plug in through register_candidates) ------------
def _exploited(memory, source_id):
    """A source that already produced hypotheses is not mined again (avoids re-proposing)."""
    return any(rel["type"] == "DERIVED_FROM" and rel["target"] == source_id
               for h in memory.of_type("HYPOTHESIS") for rel in h["relations"])


def trigger_low_selectivity(memory):
    out = []
    for obs in memory.of_type("OBSERVATION"):
        if "conversion_impulse_to_pullback" not in (obs["body"]["values"] or {}) or _exploited(memory, obs["record_id"]):
            continue
        base = next((r["target"] for r in obs["relations"] if r["type"] == "SAME_FAMILY"), None)
        if base and memory.get(base):
            spec = spec_from_record(memory.get(base))
            out.append((base, obs["record_id"], selectivity_alternatives(memory.get(base)["family"], spec, obs)))
    return out


def trigger_ablation(memory):
    """INCONCLUSIVE or NEGATIVE result without alternative explanations -> drop one condition
    at a time: if the outcome does not move, that condition carries no information."""
    out = []
    for rev in memory.of_type("REVIEW"):
        if not any(f["check"] == "NO_ALTERNATIVE_EXPLANATIONS" for f in rev["body"]["findings"]) \
                or _exploited(memory, rev["record_id"]):
            continue
        exp = memory.get(rev["body"]["reviewed_record"])
        hyp_rel = next((r["target"] for r in exp["relations"] if r["type"] == "TESTS"), None)
        if not hyp_rel or memory.get(hyp_rel) is None:
            continue
        base = memory.current(hyp_rel)
        spec = spec_from_record(base)
        if "not declared" in spec["mechanism"]:
            continue
        cands = []
        for cond in spec["state_conditions"]:
            ablated = dict(spec, state_conditions=[c for c in spec["state_conditions"] if c is not cond],
                           mechanism=f"ablation of {cond['feature_id']}: tests whether it carries information "
                                     f"for '{spec['mechanism'][:80]}'",
                           falsification=f"the outcome without {cond['feature_id']} differs from the full rule "
                                         "beyond the month-block CI on fresh data",
                           overfitting_risk="LOW", expected_information_value="MEDIUM")
            hid = f"{base['body']['hypothesis_id']}-ABL-{cond['feature_id'].upper()}"[:70]
            cands.append((hid, ablated, f"ablation of {cond['feature_id']} after {exp['body']['result']} "
                                        f"result of {exp['record_id']}"))
        out.append((base["record_id"], rev["record_id"], cands))
    return out


TRIGGERS = [trigger_low_selectivity, trigger_ablation]


class ResearchLoop:
    def __init__(self, memory, *, bridge=None, availability=None, dataset_catalog=None, inbox=(),
                 cycle_budget=None, max_new_hypotheses=DEFAULT_CYCLE_HYPOTHESES, family_budget=6,
                 extra_actions=(), fault=None, created_at=None):
        self.memory = memory
        self.bridge = bridge
        self.availability = dict(availability or {})
        self.catalog = dict(dataset_catalog or {})
        self.inbox = list(inbox)
        self.cycle_budget = cycle_budget
        self.max_new_hypotheses = max_new_hypotheses
        self.family_budget = family_budget
        self.extra_actions = list(extra_actions)
        self.fault = fault
        self.created_at = created_at

    # ---- state -----------------------------------------------------------------------------------
    def transitions(self, cycle_id=None):
        return [r for r in self.memory.of_type("LOOP_TRANSITION")
                if cycle_id is None or r["body"]["cycle_id"] == cycle_id]

    def open_cycle_id(self):
        cycles = {}
        for t in self.transitions():
            cycles.setdefault(t["body"]["cycle_id"], []).append(t["body"]["status"])
        for cid in sorted(cycles):
            if not {"CYCLE_CLOSED", "CYCLE_ABANDONED"} & set(cycles[cid]):
                return cid
        return None

    def _write(self, cycle_id, step, status, attempt, output, error=None):
        n = STEPS.index(step) + 1 if step in STEPS else 0
        rid = f"LOOP-{cycle_id}-{n:02d}{step}-{status}-A{attempt}"
        body = {"cycle_id": cycle_id, "step": step, "status": status, "attempt": attempt,
                "input_sha256": sha256_text(canonical({"cycle": cycle_id, "step": step, "attempt": attempt,
                                                       "head": self.memory.head_hash()})),
                "output": output}
        if error:
            body["error"] = error
        return self.memory.append("LOOP_TRANSITION", rid, body, author=STEP_OWNER.get(step, "research-director"),
                                  origin="RULE_ENGINE", project="NEXUS_TRADING_RESEARCH", family="RESEARCH_LOOP",
                                  created_at=self.created_at)

    def _config(self):
        return {"availability": self.availability, "catalog": self.catalog,
                "inbox": [{"path": p, "sha256": sha256_file(p)} for p in self.inbox],
                "cycle_budget": self.cycle_budget, "max_new_hypotheses": self.max_new_hypotheses,
                "family_budget": self.family_budget}

    def status(self):
        cid = self.open_cycle_id()
        done = {t["body"]["step"] for t in self.transitions(cid) if t["body"]["status"] == "COMPLETED"} if cid else set()
        return {"open_cycle": cid, "completed_steps": [s for s in STEPS if s in done],
                "next_step": next((s for s in STEPS if s not in done), None) if cid else None,
                "cycles": sorted({t["body"]["cycle_id"] for t in self.transitions()})}

    # ---- driver ----------------------------------------------------------------------------------
    def run_cycle(self):
        cid = self.open_cycle_id()
        if cid is None:
            n = len({t["body"]["cycle_id"] for t in self.transitions()}) + 1
            cid = f"C{n:04d}"
            self._write(cid, "OBSERVE", "CYCLE_OPENED", 0,
                        {"start_index": len(self.memory.records), "config_sha256": sha256_text(canonical(self._config())),
                         "config": self._config()})
        opened = next(t for t in self.transitions(cid) if t["body"]["status"] == "CYCLE_OPENED")["body"]["output"]
        outputs, resources = {}, {}
        for step in STEPS:
            mine = [t["body"] for t in self.transitions(cid) if t["body"]["step"] == step
                    and t["body"]["status"] in ("STARTED", "COMPLETED", "FAILED")]
            done = next((t for t in mine if t["status"] == "COMPLETED"), None)
            if done:
                outputs[step] = done["output"]
                resources[step] = done["output"].get("_seconds")
                continue
            started = [t for t in mine if t["status"] == "STARTED"]
            closed = {t["attempt"] for t in mine if t["status"] == "FAILED"}
            for t in started:
                if t["attempt"] not in closed:  # crashed mid-step: reconcile before retrying
                    self._write(cid, step, "FAILED", t["attempt"], {}, error="interrupted; reconciled on resume")
            attempt = len(started)
            while True:
                attempt += 1
                if attempt > MAX_ATTEMPTS:
                    self._write(cid, step, "CYCLE_ABANDONED", attempt - 1, {"outputs": list(outputs)},
                                error=f"{step} failed {MAX_ATTEMPTS} times; a person must look")
                    return {"cycle_id": cid, "status": "ABANDONED", "failed_step": step}
                self._write(cid, step, "STARTED", attempt, {})
                t0 = time.perf_counter()
                try:
                    if self.fault:
                        self.fault(step, attempt)
                    out = getattr(self, f"_step_{step.lower()}")(cid, opened, outputs, resources)
                except Exception as exc:  # noqa: BLE001  (recorded, then retried)
                    self._write(cid, step, "FAILED", attempt, {}, error=f"{type(exc).__name__}: {exc}"[:500])
                    continue
                out["_seconds"] = round(time.perf_counter() - t0, 4)
                self._write(cid, step, "COMPLETED", attempt, out)
                outputs[step], resources[step] = out, out["_seconds"]
                break
        self._write(cid, "EVALUATE", "CYCLE_CLOSED", 0, {"evaluation": outputs["EVALUATE"].get("record")})
        self.memory.checkpoint(f"research loop {cid} closed")
        return {"cycle_id": cid, "status": "CLOSED", "outputs": outputs}

    # ---- steps -----------------------------------------------------------------------------------
    def _step_observe(self, cid, opened, outputs, resources):
        authorization.require_auto_safe("INTEGRITY_CHECK", {})
        integrity = _run_integrity(self.memory, {})
        if not integrity["ok"]:
            raise LoopHalted(f"memory integrity: {integrity['problems'][:3]}")
        ingested, skipped = [], []
        for path in self.inbox:
            authorization.require_auto_safe("INGEST_AVAILABLE_REPORT", {"description": path})
            import json
            with open(path, encoding="utf-8") as handle:
                summary = json.load(handle)
            exp_id = ingest.rid("EXP", summary.get("run_id", "BL-RUN"))
            hyp = id_resolver.resolve(self.memory, summary.get("hypothesis_id"))
            if self.memory.get(exp_id):
                skipped.append({"report": path, "reason": f"already ingested as {exp_id}"})
                continue
            if hyp is None:
                skipped.append({"report": path, "reason": f"HYP-{summary.get('hypothesis_id')} not in memory "
                                                          "and no valid manifest alias"})
                continue
            placeholder = next((e["record_id"] for e in self.memory.of_type("EXPERIMENT")
                                if e["body"]["hypothesis_id"] == summary.get("hypothesis_id")
                                and e["body"]["status"] == "NOT_RUN"
                                and self.memory.current(e["record_id"])["record_id"] == e["record_id"]), None)
            rec = ingest.import_behavior_lab_summary(self.memory, path, hyp, supersedes=placeholder)
            ingested.append(rec["record_id"])
        approvals = {}
        for act in self.memory.of_type("ACTION"):
            if act["body"]["status"] == "AWAITING_APPROVAL" and self.bridge:
                approvals[act["record_id"]] = self.bridge.status(act["body"]["orchestrator_task_id"])
        reviewed = {r["body"]["reviewed_record"] for r in self.memory.of_type("REVIEW")
                    if r["body"]["rules_version"] == review.RULES_VERSION}
        to_review = [e["record_id"] for e in self.memory.of_type("EXPERIMENT")
                     if e["record_id"] not in reviewed and e["body"]["status"] != "NOT_RUN"]
        return {"integrity_ok": True, "ingested": ingested, "skipped_reports": skipped,
                "approvals": approvals, "to_review": to_review}

    def _step_review(self, cid, opened, outputs, resources):
        reviews, new, linked = [], [], []
        for rid in outputs["OBSERVE"]["to_review"]:
            authorization.require_auto_safe("REVIEW_EXPERIMENT", {"description": rid})
            rev, n, l = review.review(self.memory, rid, created_at=self.created_at)
            reviews.append(rev["record_id"])
            new += [r["record_id"] for r in n]
            linked += l
        return {"reviews": reviews, "new_proposals": new, "linked": linked}

    def _step_learn(self, cid, opened, outputs, resources):
        trials = evaluation.update_trials(self.memory, created_at=self.created_at)
        families = sorted({self.memory.get(r)["family"] for r in outputs["REVIEW"]["reviews"]} |
                          {h["family"] for h in self.memory.of_type("HYPOTHESIS") if h["body"]["is_proposal_only"]})
        briefs = {f: lessons.briefing(self.memory, f, max_per_family=self.family_budget) for f in families}
        results = {t: self.memory.get(t)["body"].get("verdict") for t in trials
                   if self.memory.get(t)["body"]["phase"] == "RESULT"}
        return {"trials_written": trials, "trial_verdicts": results, "briefings": briefs}

    def _step_hypothesize(self, cid, opened, outputs, resources):
        authorization.require_auto_safe("GENERATE_PROPOSALS", {})
        budget = FamilyBudget(self.memory, max_hypotheses_per_family=self.family_budget)
        report = {"registered": [], "duplicates": [], "over_budget": [], "cycle_limit": []}
        for trigger in TRIGGERS:
            for base, source, cands in trigger(self.memory):
                room = self.max_new_hypotheses - len(report["registered"])
                if room <= 0:
                    report["cycle_limit"] += [c[0] for c in cands]
                    continue
                fam = self.memory.get(base)["family"]
                r = register_candidates(self.memory, cands[:room] if room < len(cands) else cands,
                                        base_record=base, source_record=source, family=fam, budget=budget,
                                        author=f"{STEP_OWNER['HYPOTHESIZE']}-rules", created_at=self.created_at)
                report["registered"] += r["registered"]
                report["duplicates"] += r["duplicates"]
                report["over_budget"] += r["over_budget"]
                report["cycle_limit"] += [c[0] for c in cands[room:]] if room < len(cands) else []
        return report

    def _step_prioritize(self, cid, opened, outputs, resources):
        body = priority_queue.build_queue(self.memory, self.availability, family_budget=self.family_budget,
                                          created_at=self.created_at)
        return {"ranked": [{"record_id": r["record_id"], "total": r["total"]} for r in body["ranked"]],
                "excluded": len(body["excluded"]), "budget": body["budget"]}

    def _step_plan(self, cid, opened, outputs, resources):
        ranked = {"ranked": outputs["PRIORITIZE"]["ranked"]}
        return planner.plan_cycle(self.memory, ranked, cid, self.catalog, budget=self.cycle_budget,
                                  created_at=self.created_at)

    def _action(self, cid, plan_id, kind, params, refuse_reason=None):
        params = params or {}
        aid = f"ACT-{sha256_text(canonical({'plan': plan_id, 'kind': kind, 'params': params}))[:16].upper()}"
        existing = self.memory.get(aid)
        if existing:  # resumed or retried: reconcile, never act twice
            st = existing["body"]["status"]
            if st == "AWAITING_APPROVAL" and self.bridge:
                return aid, f"{st}:{self.bridge.status(existing['body']['orchestrator_task_id'])}"
            return aid, st
        mode, reasons = authorization.classify(kind, params)
        body = {"cycle_id": cid, "kind": kind, "mode": mode, "reasons": reasons, "params": params,
                "params_sha256": sha256_text(canonical(params))}
        if plan_id:
            body["plan_record"] = plan_id
        if refuse_reason and mode != authorization.PROHIBITED:
            body["status"], body["reasons"] = "REFUSED", reasons + [refuse_reason]
        elif mode == authorization.AUTO_SAFE and kind in AUTO_RUNNERS:
            t0 = time.perf_counter()
            try:
                body["result"] = AUTO_RUNNERS[kind](self.memory, params)
                body["status"] = "EXECUTED"
            except Exception as exc:  # noqa: BLE001
                body["result"], body["status"] = {"error": str(exc)[:300]}, "FAILED"
            body["resources"] = {"seconds": round(time.perf_counter() - t0, 4)}
        elif mode == authorization.APPROVAL_REQUIRED and self.bridge:
            task_id, _ = self.bridge.request(aid, {"kind": kind, "params_sha256": body["params_sha256"],
                                                   "reasons": reasons,
                                                   "objective": f"{kind} for {plan_id or 'loop'}: {reasons[-1]}"})
            body["status"], body["orchestrator_task_id"] = "AWAITING_APPROVAL", task_id
        else:
            body["status"] = "REFUSED"
            if mode == authorization.APPROVAL_REQUIRED:
                body["reasons"] = reasons + ["no approval channel configured"]
            elif mode == authorization.AUTO_SAFE:
                body["reasons"] = reasons + ["no automatic runner for this kind"]
        rels = [{"type": "DERIVED_FROM", "target": plan_id}] if plan_id else []
        self.memory.append("ACTION", aid, body, author=STEP_OWNER["EXECUTE"], origin="RULE_ENGINE",
                           project="NEXUS_TRADING_RESEARCH",
                           family=self.memory.get(plan_id)["family"] if plan_id else "RESEARCH_LOOP",
                           relations=rels, created_at=self.created_at)
        return aid, body["status"]

    def _step_execute(self, cid, opened, outputs, resources):
        done = {}
        for pid in outputs["PLAN"]["planned"]:
            power = None
            for a in self.memory.get(pid)["body"]["actions"]:
                refuse = None
                if a["kind"] == "RUN_EXPERIMENT_REAL_DATA" and power and power.get("verdict") == "UNDERPOWERED":
                    refuse = (f"synthetic power analysis: power {power['simulated_power']:.2f} with "
                              f"{power['expected_events']} expected events, {power['n_needed_for_80pct_power']} "
                              "needed; not worth real data as planned")
                aid, st = self._action(cid, pid, a["kind"], a["params"], refuse_reason=refuse)
                done[aid] = st
                if a["kind"] == "SYNTHETIC_DRY_RUN":
                    power = (self.memory.get(aid)["body"].get("result") or {})
        for a in self.extra_actions:
            aid, st = self._action(cid, None, a["kind"], a.get("params"))
            done[aid] = st
        return {"actions": done}

    def _step_evaluate(self, cid, opened, outputs, resources):
        trials = evaluation.update_trials(self.memory, created_at=self.created_at)
        metrics = evaluation.cycle_metrics(self.memory, opened["start_index"], outputs,
                                           {"seconds_per_step": resources})
        notes = ["success is information gained and errors found, not runs executed",
                 "proposals and generated hypotheses are not evidence"]
        pending = [a for a, s in outputs["EXECUTE"]["actions"].items() if str(s).startswith("AWAITING_APPROVAL")]
        if pending:
            notes.append(f"{len(pending)} actions wait for a human decision in the orchestrator queue")
        eid = f"EVAL-{cid}"
        if not self.memory.get(eid):
            self.memory.append("EVALUATION", eid, {"cycle_id": cid, "metrics_version": evaluation.METRICS_VERSION,
                                                   "metrics": metrics, "notes": notes},
                               author=STEP_OWNER["EVALUATE"], origin="RULE_ENGINE", project="NEXUS_TRADING_RESEARCH",
                               family="RESEARCH_LOOP", created_at=self.created_at)
        return {"record": eid, "trials_written": trials, "pending_approvals": pending}
