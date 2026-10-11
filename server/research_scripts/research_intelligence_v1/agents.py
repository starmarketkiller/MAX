"""Research roles as shared services, bound to the existing agent capability registry.

One table for every strategy family and every NEXUS company (`project` travels in
the records, the roles do not change). Every role runs Tier 0 (deterministic
code in this package) by default; `escalation` names the registry agent a person
may route a task to through the orchestrator, never called automatically, and
never a paid API that is required to run the loop.
"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY = os.path.abspath(os.path.join(HERE, "..", "..", "orchestrator_v1", "agent_capability_registry_v1.json"))

ROLES = {
    "research-director": {"steps": ["PRIORITIZE", "PLAN"], "implementation": "priority_queue.py, planner.py",
                          "executor": "TIER0_DETERMINISTIC", "escalation": "CLAUDE_TIER3"},
    "research-memory-curator": {"steps": ["OBSERVE"], "implementation": "ingest.py, memory.py",
                                "executor": "TIER0_DETERMINISTIC", "escalation": None},
    "improvement-reviewer": {"steps": ["REVIEW"], "implementation": "review.py",
                             "executor": "TIER0_DETERMINISTIC", "escalation": "LOCAL_STRONG_MINISTRAL3B"},
    "data-quality-auditor": {"steps": ["REVIEW"], "implementation": "review.py (DATA_QUALITY rules)",
                             "executor": "TIER0_DETERMINISTIC", "escalation": "LOCAL_STRONG_MINISTRAL3B"},
    "strategy-researcher": {"steps": ["HYPOTHESIZE"], "implementation": "generator.py",
                            "executor": "TIER0_DETERMINISTIC", "escalation": "CLAUDE_TIER3"},
    "market-researcher": {"steps": ["HYPOTHESIZE"], "implementation": "generator.py templates",
                          "executor": "TIER0_DETERMINISTIC", "escalation": "CLAUDE_TIER3"},
    "statistical-reviewer": {"steps": ["PLAN", "LEARN"], "implementation": "planner.statistical_review, overfitting.py",
                             "executor": "TIER0_DETERMINISTIC", "escalation": "CLAUDE_TIER3"},
    "safety-gate": {"steps": ["EXECUTE"], "implementation": "authorization.py, gates.py",
                    "executor": "TIER0_DETERMINISTIC", "escalation": None},
    "improvement-evaluator": {"steps": ["LEARN", "EVALUATE"], "implementation": "evaluation.py",
                              "executor": "TIER0_DETERMINISTIC", "escalation": None},
}
STEP_OWNER = {"OBSERVE": "research-memory-curator", "REVIEW": "improvement-reviewer", "LEARN": "statistical-reviewer",
              "HYPOTHESIZE": "strategy-researcher", "PRIORITIZE": "research-director", "PLAN": "research-director",
              "EXECUTE": "safety-gate", "EVALUATE": "improvement-evaluator"}


def registry():
    with open(REGISTRY, encoding="utf-8") as handle:
        doc = json.load(handle)
    return {a["agent_id"]: a for a in doc.get("payload", doc)["agents"]}


def validate_roles():
    """Every escalation target exists in the registry and may take RESEARCH or CODE work;
    every step has exactly one owner role; no role needs a paid provider to run."""
    agents, problems = registry(), []
    for name, role in ROLES.items():
        esc = role["escalation"]
        if esc and esc not in agents:
            problems.append(f"{name}: escalation {esc} not in agent registry")
        elif esc and not {"RESEARCH", "CODE", "DOCUMENTATION"} & set(agents[esc].get("allowed_task_types", [])):
            problems.append(f"{name}: {esc} may not take research work")
        if role["executor"] != "TIER0_DETERMINISTIC":
            problems.append(f"{name}: default executor must be deterministic")
    for step, owner in STEP_OWNER.items():
        if step not in ROLES[owner]["steps"]:
            problems.append(f"{step}: owner {owner} does not declare it")
    return problems
