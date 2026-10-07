"""NEXUS_EXECUTIVE_STATE_V1 builder.

Providers are zero-argument callables wired in app.py to the existing
projections; each is called at most once per build and isolated: a failing
provider turns its section UNAVAILABLE instead of failing the whole state.
Builds are cached for a few seconds so a burst of Jarvis questions reads one
snapshot instead of hitting every subsystem per message.
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timezone

from . import sections as S

SCHEMA = "NEXUS_EXECUTIVE_STATE_V1"
DOMAINS = ("system", "tasks", "approvals", "revenue", "trading", "social",
           "ai_fashion_agency", "finance", "infrastructure")

# overall_progress method (auditable): maturity weight per business domain.
PROGRESS_DOMAINS = ("revenue", "trading", "ai_fashion_agency", "social")
MATURITY_WEIGHTS = {"FOUNDATION": 0.25, "PARTIAL": 0.5, "OPERATIONAL": 0.75,
                    "SHADOW": 0.85, "LIVE": 1.0, "BLOCKED": 0.0}
MIN_KNOWN_FOR_PROGRESS = 3

SEVERITY = {
    "DISPATCHER_STOPPED": "CRITICAL", "READINESS_FAILING": "CRITICAL",
    "DATABASE_NOT_WRITABLE": "CRITICAL",
    "CI_BLOCKING_DEPLOY": "IMPORTANT", "LOCAL_WORKER_UNREACHABLE": "IMPORTANT",
    "APPROVALS_PENDING": "WARNING", "TASK_BLOCKED": "WARNING", "FOLLOWUP_DUE": "WARNING",
    "TRADING_EXPERIMENT_BLOCKED": "WARNING", "LOCAL_BRIDGE_OFFLINE": "WARNING",
    "LOCAL_WORKER_OUTPUT_REJECTED_BY_VERIFIER": "WARNING",
    "REVENUE_RUNNER_DISABLED": "INFO", "TRADING_TELEMETRY_UNAVAILABLE": "INFO",
    "SOCIAL_NOT_OPERATIONAL": "INFO", "AGENCY_STORE_BLOCKED": "INFO",
    "PROJECTION_UNAVAILABLE": "WARNING",
}
SEVERITY_ORDER = ("CRITICAL", "IMPORTANT", "WARNING", "INFO")
HEALTH_ORDER = ("RED", "AMBER", "UNKNOWN", "GREEN")


def _now():
    return datetime.now(timezone.utc).isoformat()


def unified_approvals(*, tasks, revenue_drafts, agency_state):
    items = []
    for r in tasks:
        if r.get("state") != "WAITING_APPROVAL":
            continue
        m = r.get("manifest") or {}
        items.append({"approval_id": r["task_id"], "domain": "TASKS",
                      "reason": m.get("title") or "task in attesa di approvazione", "cost": None,
                      "risk": m.get("risk_level"), "created_at": r.get("updated_at"),
                      "action": f"approva o rifiuta {r['task_id']}"})
    for d in revenue_drafts or []:
        if d.get("status") != "READY_FOR_REVIEW":
            continue
        items.append({"approval_id": d["draft_id"], "domain": "REVENUE",
                      "reason": f"bozza {d.get('type')} per lead {d.get('lead')}", "cost": None,
                      "risk": "OUTREACH", "created_at": d.get("created_at"),
                      "action": "rivedi la bozza prima di qualsiasi invio"})
    for a in (agency_state or {}).get("approvals", []):
        credits = a.get("credits") or 0
        items.append({"approval_id": a["id"], "domain": "AI_FASHION_AGENCY", "reason": a["what"],
                      "cost": {"credits": credits} if credits else None,
                      "risk": "SPEND_CREDITS" if credits else a["kind"],
                      "created_at": None,
                      "action": (f"approva {a['what']} ({credits:g} crediti)" if credits
                                 else f"approva {a['what']}")})
    return items


def alert_engine(sections_by_domain, approvals):
    merged = {}
    for domain, sec in sections_by_domain.items():
        for b in sec.get("blockers", []):
            code = b["code"]
            entry = merged.setdefault(code, {"code": code, "severity": SEVERITY.get(code, "WARNING"),
                                             "domains": [], "details": []})
            if domain not in entry["domains"]:
                entry["domains"].append(domain)
            if b.get("detail") and b["detail"] not in entry["details"]:
                entry["details"].append(b["detail"])
    if approvals:
        merged["APPROVALS_PENDING"] = {"code": "APPROVALS_PENDING", "severity": "WARNING",
                                       "domains": sorted({a["domain"] for a in approvals}),
                                       "details": [f"{len(approvals)} decisioni in attesa"]}
    alerts = sorted(merged.values(), key=lambda a: (SEVERITY_ORDER.index(a["severity"]), a["code"]))
    for a in alerts:
        a["count"] = len(a["details"]) or 1
        a["details"] = a["details"][:3]
    return alerts


def overall_progress(sections_by_domain):
    basis = {d: sections_by_domain[d]["status"] for d in PROGRESS_DOMAINS}
    known = {d: s for d, s in basis.items() if s in MATURITY_WEIGHTS}
    method = ("mean of MATURITY_WEIGHTS over business domains with a known maturity "
              f"{PROGRESS_DOMAINS}; UNAVAILABLE if fewer than {MIN_KNOWN_FOR_PROGRESS} known")
    if len(known) < MIN_KNOWN_FOR_PROGRESS:
        return {"value": S.UNAVAILABLE, "method": method, "basis": basis,
                "weights": MATURITY_WEIGHTS}
    value = round(100 * sum(MATURITY_WEIGHTS[s] for s in known.values()) / len(known))
    return {"value": value, "unit": "maturity_percent", "method": method, "basis": basis,
            "weights": MATURITY_WEIGHTS}


def _safe(fn, default=None):
    try:
        return fn() if fn else default, None
    except Exception as exc:  # projection isolation: report class, never payload
        return default, type(exc).__name__


class ExecutiveStateBuilder:
    def __init__(self, providers, *, cache_seconds=10, clock=time.monotonic):
        self.providers = dict(providers)
        self.cache_seconds = cache_seconds
        self.clock = clock
        self._lock = threading.Lock()
        self._cached = None
        self._cached_at = None

    def build(self, *, force=False):
        with self._lock:
            if (not force and self._cached is not None and
                    self.clock() - self._cached_at < self.cache_seconds):
                return self._cached
            state = self._build()
            self._cached, self._cached_at = state, self.clock()
            return state

    def _get(self, name, default=None):
        return _safe(self.providers.get(name), default)

    def _build(self):
        errors = {}

        def get(name, default=None):
            value, err = self._get(name, default)
            if err:
                errors[name] = err
            return value

        tasks = get("tasks", []) or []
        agency_store = get("agency_store")
        agency_state = agency_slice = agency_snapshot = agency_rev = None
        if agency_store is not None:
            from business_units.ai_fashion_agency.projection import agency_state as _as
            from business_units.ai_fashion_agency.projection import executive_slice
            from business_units.revenue import agency_revenue_projection
            queue = get("queue")
            agency_state, err1 = _safe(lambda: _as(agency_store, queue=queue))
            agency_slice, err2 = _safe(lambda: executive_slice(agency_store, queue=queue))
            agency_snapshot, err3 = _safe(agency_store.snapshot)
            agency_rev, err4 = _safe(lambda: agency_revenue_projection(agency_store))
            for name, err in (("agency_state", err1), ("agency_slice", err2),
                              ("agency_snapshot", err3), ("agency_revenue", err4)):
                if err:
                    errors[name] = err
        revenue_ops = get("revenue_operations")
        revenue_drafts = get("revenue_drafts", []) or []

        def build_section(domain, fn):
            value, err = _safe(fn)
            if err:
                errors[domain] = err
                return S.unavailable(domain, f"projection error {err}")
            return value

        secs = {
            "system": build_section("system", lambda: S.system_section({
                "version": get("version"), "dispatcher": get("dispatcher"),
                "multi_stage": get("multi_stage"), "bridge": get("bridge"),
                "gateway": get("gateway"), "observations": get("observations")})),
            "infrastructure": build_section("infrastructure",
                                            lambda: S.infrastructure_section({"ready": get("ready")})),
            "tasks": build_section("tasks", lambda: S.tasks_section(tasks)),
            "revenue": (build_section("revenue", lambda: S.revenue_section(
                {"operations": revenue_ops, "store": get("revenue_store")}))
                if revenue_ops is not None else S.unavailable("revenue", "revenue non configurata")),
            "trading": build_section("trading", lambda: S.trading_section({
                "registry": get("trading_registry"), "control_plane": get("trading_control_plane"),
                "account": get("trading_account")})),
            "social": build_section("social", lambda: S.social_section(agency_snapshot)),
            "ai_fashion_agency": build_section("ai_fashion_agency", lambda: S.agency_section(
                agency_slice, agency_state or {})),
        }
        approvals = unified_approvals(tasks=tasks, revenue_drafts=revenue_drafts,
                                      agency_state=agency_state)
        secs["approvals"] = S.approvals_section(approvals)
        secs["finance"] = build_section("finance", lambda: S.finance_section({
            "ledger_events": get("ledger_events", []), "agency_revenue": agency_rev,
            "revenue": secs["revenue"]["key_metrics"] if secs["revenue"]["status"] != "UNAVAILABLE"
            else None}))
        if (revenue_ops or {}).get("followups_due"):
            secs["revenue"]["blockers"].append({"code": "FOLLOWUP_DUE",
                                                "detail": f"{revenue_ops['followups_due']} follow-up dovuti"})
        alerts = alert_engine(secs, approvals)
        healths = [secs[d]["health"] for d in DOMAINS]
        worst = min(healths, key=HEALTH_ORDER.index)
        severities = {a["severity"] for a in alerts}
        overall_status = ("CRITICAL" if "CRITICAL" in severities else
                          "DEGRADED" if "IMPORTANT" in severities or worst == "RED" else
                          "ATTENTION" if severities & {"WARNING"} else "OK")
        return {"schema_version": SCHEMA, "generated_at": _now(),
                "overall_status": overall_status, "overall_health": worst,
                "overall_progress": overall_progress(secs), "alerts": alerts,
                "decisions_required": approvals, **{d: secs[d] for d in DOMAINS},
                "provider_errors": errors}
