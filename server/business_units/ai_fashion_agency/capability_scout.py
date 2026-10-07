"""CAPABILITY_SCOUT_V1: missing capability -> registry search -> candidate ->
vet -> sandbox -> eval -> register.

Uses the canonical SkillRegistry/agent registry for the search step and the
canonical TRUST_STATES vocabulary.  It only *records* the pipeline position of
each candidate: nothing is installed, enabled or granted from here.
"""
from __future__ import annotations

from jarvis_v1.local_operations import TRUST_STATES

STAGES = ("MISSING", "REGISTRY_SEARCHED", "CANDIDATE", "VETTED", "SANDBOXED", "EVALUATED",
          "REGISTERED", "REJECTED")

# Candidates reviewed on 2026-10-07 for the Agency's four gaps.  trust_level
# stays EXPERIMENTAL until a sandbox eval passes; nothing here is installed.
CANDIDATES = {
    "social_publishing": [
        {"candidate": "Postiz", "kind": "OSS_SELF_HOSTED+AGENT_SKILL", "stage": "CANDIDATE",
         "trust_level": "EXPERIMENTAL",
         "why": "multi-platform scheduler + analytics; skill already present in workspace",
         "next_step": "sandbox instance, one test account, dry-run payload only"},
        {"candidate": "Activepieces", "kind": "OSS_AUTOMATION", "stage": "REJECTED",
         "trust_level": "REJECTED", "why": "duplicates Orchestrator/scheduler responsibilities"},
    ],
    "web_scouting": [
        {"candidate": "Session web search/fetch (Claude/Codex)", "kind": "SUPPLIED_TOOL",
         "stage": "REGISTERED", "trust_level": "VETTED_EXTERNAL",
         "why": "used under human supervision; evidence captured with provenance"},
        {"candidate": "SearXNG", "kind": "OSS_SELF_HOSTED", "stage": "CANDIDATE",
         "trust_level": "EXPERIMENTAL", "why": "metasearch with no API keys; needs hosting"},
        {"candidate": "Crawl4AI", "kind": "OSS_LIBRARY", "stage": "CANDIDATE",
         "trust_level": "EXPERIMENTAL", "why": "page->markdown extraction; must respect robots/ToS"},
        {"candidate": "Playwright MCP", "kind": "MCP", "stage": "CANDIDATE",
         "trust_level": "EXPERIMENTAL", "why": "JS-heavy pages; heavier, last resort"},
    ],
    "analytics": [
        {"candidate": "Postiz analytics", "kind": "OSS_SELF_HOSTED", "stage": "CANDIDATE",
         "trust_level": "EXPERIMENTAL", "why": "same component as publishing; avoids a 2nd tool"},
        {"candidate": "Native TikTok/Instagram insights", "kind": "PLATFORM_API",
         "stage": "CANDIDATE", "trust_level": "EXPERIMENTAL",
         "why": "authoritative numbers; requires created accounts + app review"},
    ],
    "store_integration": [
        {"candidate": "External store / affiliate link adapters", "kind": "INTERNAL_ADAPTER",
         "stage": "REGISTERED", "trust_level": "TRUSTED_CANONICAL",
         "why": "store_integration.py; no live store needed"},
        {"candidate": "Shopify (plugin connected in workspace, needs auth)", "kind": "MCP",
         "stage": "CANDIDATE", "trust_level": "EXPERIMENTAL",
         "why": "real catalog/listing checks once a store exists; opening a store needs approval"},
    ],
}


def scout(capability, *, skill_registry=None, agent_registry=None):
    """Registry search first; external candidates only if nothing canonical fits."""
    if capability not in CANDIDATES:
        raise ValueError("unknown agency capability gap")
    internal_skills = [s["skill_id"] for s in (skill_registry.list() if skill_registry else [])
                       if capability in s["capabilities"]]
    internal_agents = [a["agent_id"] for a in (agent_registry or {}).get("agents", [])
                       if capability in a.get("capabilities", [])]
    candidates = CANDIDATES[capability]
    assert all(c["trust_level"] in TRUST_STATES and c["stage"] in STAGES for c in candidates)
    return {"schema_version": "CAPABILITY_SCOUT_V1", "capability": capability,
            "registry_search": {"skills": internal_skills, "agents": internal_agents},
            "resolution": "INTERNAL" if internal_skills or internal_agents else "EXTERNAL_CANDIDATES",
            "candidates": candidates, "installed_now": []}


def scout_all(**registries):
    return [scout(c, **registries) for c in CANDIDATES]
