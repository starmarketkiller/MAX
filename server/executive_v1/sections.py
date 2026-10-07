"""Pure section builders for NEXUS_EXECUTIVE_STATE_V1.

Each builder turns one domain's *existing* projection (passed in as a plain
dict by state.py) into the common section shape.  No builder reads files,
calls models or infers numbers: a missing input becomes UNAVAILABLE.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

UNAVAILABLE = "UNAVAILABLE"
MATURITY = ("FOUNDATION", "PARTIAL", "OPERATIONAL", "SHADOW", "LIVE", "BLOCKED", "UNAVAILABLE")
HEALTH = ("GREEN", "AMBER", "RED", "UNKNOWN")


def _now():
    return datetime.now(timezone.utc).isoformat()


def section(*, status, health, source, confidence, key_metrics, active_work=None,
            blockers=None, next_actions=None, last_updated=None, extra=None):
    assert status in MATURITY and health in HEALTH and confidence in ("HIGH", "MEDIUM", "LOW")
    return {"status": status, "health": health, "last_updated": last_updated or _now(),
            "source": source, "confidence": confidence, "key_metrics": key_metrics,
            "active_work": list(active_work or []), "blockers": list(blockers or []),
            "next_actions": list(next_actions or []), **(extra or {})}


def unavailable(source, reason):
    return section(status="UNAVAILABLE", health="UNKNOWN", source=source, confidence="LOW",
                   key_metrics={}, blockers=[{"code": "PROJECTION_UNAVAILABLE",
                                              "detail": reason}])


def _blocker(code, detail):
    return {"code": code, "detail": detail}


# ---- system / infrastructure ----------------------------------------------

def system_section(raw):
    """raw: version, dispatcher, multi_stage, bridge, gateway, observations."""
    obs = raw.get("observations") or {}
    gateway = raw.get("gateway") or {}
    bridge = raw.get("bridge") or {}
    dispatcher = raw.get("dispatcher") or {}
    ci = obs.get("ci") or {}
    online_bridges = [b for b in bridge.get("items", []) if b.get("status") == "ONLINE"]
    if not gateway.get("gateway_configured"):
        mistral = "NOT_CONFIGURED"
    elif gateway.get("last_status") == "ERROR":
        mistral = "UNREACHABLE"
    elif gateway.get("last_status") == "OK":
        mistral = "REACHABLE"
    else:
        mistral = "UNKNOWN_NOT_PROBED"
    blockers, actions = [], []
    if ci.get("state") == "FAILING":
        blockers.append(_blocker("CI_BLOCKING_DEPLOY",
                                 f"CI rossa ({ci.get('failing_tests', '?')} test falliti): "
                                 "il deploy automatico non parte"))
        actions.append("sistemare i test CI falliti (lavoro Codex MT5/MACD)")
    if mistral in {"UNREACHABLE", "NOT_CONFIGURED"}:
        blockers.append(_blocker("LOCAL_WORKER_UNREACHABLE",
                                 f"Mistral locale {mistral.lower().replace('_', ' ')}"
                                 + (f" ({gateway.get('last_error')})" if gateway.get("last_error") else "")))
        actions.append("riavviare gateway/tunnel locale e aggiornare JARVIS_MINISTRAL_GATEWAY_URL")
    if bridge.get("configured") and not online_bridges:
        blockers.append(_blocker("LOCAL_BRIDGE_OFFLINE", "nessun local bridge online"))
    if dispatcher and dispatcher.get("enabled", True) and not dispatcher.get("running"):
        blockers.append(_blocker("DISPATCHER_STOPPED", "dispatcher task abilitato ma fermo"))
    deployed = (raw.get("version") or {}).get("git_sha")
    main_head = obs.get("main_head_sha")
    behind = bool(deployed and main_head and deployed != main_head)
    if behind:
        actions.append("deployare main quando la CI è verde")
    health = ("RED" if any(b["code"] == "DISPATCHER_STOPPED" for b in blockers) else
              "AMBER" if blockers or behind else
              "GREEN" if ci.get("state") == "PASSING" and mistral == "REACHABLE" else "UNKNOWN")
    return section(
        status="BLOCKED" if any(b["code"] == "CI_BLOCKING_DEPLOY" for b in blockers) else "OPERATIONAL",
        health=health, source="version + dispatcher + local bridge + ministral gateway_status "
                              "+ executive observations", confidence="MEDIUM" if obs else "LOW",
        key_metrics={"deployed_sha": deployed or UNAVAILABLE,
                     "main_head_sha": main_head or UNAVAILABLE,
                     "deploy_behind_main": behind if (deployed and main_head) else UNAVAILABLE,
                     "ci": ci.get("state", UNAVAILABLE),
                     "ci_failing_tests": ci.get("failing_tests", UNAVAILABLE),
                     "mistral": mistral, "local_bridges_online": len(online_bridges),
                     "dispatcher_running": dispatcher.get("running", UNAVAILABLE),
                     "dispatcher_enabled": dispatcher.get("enabled", UNAVAILABLE),
                     "multi_stage_running": (raw.get("multi_stage") or {}).get("running", UNAVAILABLE),
                     "last_deploy": obs.get("last_deploy", UNAVAILABLE),
                     "last_incident": obs.get("last_incident", UNAVAILABLE)},
        blockers=blockers, next_actions=actions)


def infrastructure_section(raw):
    ready = raw.get("ready") or {}
    checks = ready.get("checks") or {}
    db = checks.get("database") or {}
    blockers = []
    if ready and not ready.get("ok"):
        failing = sorted(k for k, v in checks.items() if isinstance(v, dict) and v.get("ok") is False)
        blockers.append(_blocker("READINESS_FAILING",
                                 "readiness non ok: " + (", ".join(failing) or "motivo non indicato")))
    if db and not db.get("writable", True):
        blockers.append(_blocker("DATABASE_NOT_WRITABLE", "database in sola lettura"))
    return section(
        status="OPERATIONAL" if ready.get("ok") else ("UNAVAILABLE" if not ready else "BLOCKED"),
        health="GREEN" if ready.get("ok") and not blockers else ("UNKNOWN" if not ready else "RED"),
        source="readiness checks (/api/ready)", confidence="HIGH" if ready else "LOW",
        key_metrics={"ready": ready.get("ok", UNAVAILABLE),
                     "database_writable": db.get("writable", UNAVAILABLE),
                     "migrations_ok": (checks.get("migrations") or {}).get("ok", UNAVAILABLE)},
        blockers=blockers)


# ---- tasks / approvals ----------------------------------------------------

def tasks_section(records, *, now=None):
    now = now or datetime.now(timezone.utc)
    by_state = {}
    for r in records:
        by_state.setdefault(r.get("state"), []).append(r)

    def count(*states):
        return sum(len(by_state.get(s, [])) for s in states)

    day_ago = now - timedelta(hours=24)
    completed_recently = [r for r in by_state.get("COMPLETED", [])
                          if _ts(r.get("updated_at")) and _ts(r["updated_at"]) >= day_ago]
    running = by_state.get("RUNNING", [])
    started = [_ts(r.get("started_at") or r.get("updated_at")) for r in running]
    started = [s for s in started if s]
    oldest = int((now - min(started)).total_seconds()) if started else None
    blocked = by_state.get("BLOCKED", []) + by_state.get("ESCALATION_REQUIRED", [])
    blockers = [_blocker("TASK_BLOCKED", f"{r['task_id']}: {(r.get('manifest') or {}).get('title', '')[:70]}")
                for r in blocked[:5]]
    return section(
        status="OPERATIONAL", health="AMBER" if blocked or count("FAILED") else "GREEN",
        source="TaskQueue", confidence="HIGH",
        key_metrics={"running": count("RUNNING"), "queued": count("QUEUED", "WAITING_DEPENDENCY"),
                     "waiting_context": count("WAITING_CONTEXT"),
                     "waiting_approval": count("WAITING_APPROVAL"),
                     "waiting_premium": count("WAITING_PROVIDER", "WAITING_REVIEW_PROVIDER"),
                     "blocked": len(blocked), "failed": count("FAILED"),
                     "completed_recently": len(completed_recently),
                     "oldest_running_age_seconds": oldest},
        active_work=[{"task_id": r["task_id"], "title": (r.get("manifest") or {}).get("title")}
                     for r in running[:5]],
        blockers=blockers)


def _ts(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def approvals_section(items):
    by_domain = {}
    for item in items:
        by_domain[item["domain"]] = by_domain.get(item["domain"], 0) + 1
    credits = round(sum(i["cost"]["credits"] for i in items
                        if isinstance(i.get("cost"), dict) and i["cost"].get("credits")), 4)
    return section(status="OPERATIONAL", health="AMBER" if items else "GREEN",
                   source="TaskQueue WAITING_APPROVAL + Revenue drafts + Agency decisions",
                   confidence="HIGH",
                   key_metrics={"pending": len(items), "by_domain": by_domain,
                                "credits_requested": credits},
                   next_actions=[i["action"] for i in items[:5]], extra={"items": items})


# ---- business domains -----------------------------------------------------

def revenue_section(raw):
    rev = raw.get("operations") or {}
    store = raw.get("store") or {}
    leads = store.get("leads", [])
    revenues = store.get("revenues", [])
    gross = round(sum(float(r.get("amount") or 0) for r in revenues), 2)
    costs = round(sum(float(r.get("cost") or 0) for r in revenues), 2)
    sales = len(revenues)
    blockers, actions = [], []
    if not rev.get("revenue_runner_enabled"):
        blockers.append(_blocker("REVENUE_RUNNER_DISABLED", "automazione Revenue disattivata"))
        actions.append("decidere se attivare NEXUS_REVENUE_AUTOMATION_ENABLED")
    if rev.get("followups_due"):
        actions.append(f"rivedere {rev['followups_due']} follow-up dovuti")
    if rev.get("drafts_ready"):
        actions.append(f"approvare o scartare {rev['drafts_ready']} bozze")
    if not leads and not rev.get("prospects_count"):
        actions.append("avviare il primo test di mercato reale di una venture")
    status = ("LIVE" if sales else "OPERATIONAL" if rev.get("revenue_runner_running") else
              "PARTIAL" if leads or rev.get("prospects_count") else "FOUNDATION")
    replies = sum(1 for lead in leads if lead.get("status") == "REPLIED")
    return section(
        status=status, health="GREEN" if sales else "AMBER", source="OperationsProjection.revenue + "
        "FirstRevenueStore", confidence="HIGH" if rev else "LOW",
        key_metrics={"runner_enabled": rev.get("revenue_runner_enabled", UNAVAILABLE),
                     "runner_running": rev.get("revenue_runner_running", UNAVAILABLE),
                     "prospects": rev.get("prospects_count", UNAVAILABLE),
                     "qualified_leads": rev.get("qualified_count", UNAVAILABLE),
                     "drafts_ready": rev.get("drafts_ready", UNAVAILABLE),
                     "followups_due": rev.get("followups_due", UNAVAILABLE),
                     "replies_waiting": replies, "sales": sales, "revenue_eur": gross,
                     "costs_eur": costs, "profit_eur": round(gross - costs, 2),
                     "ventures_ready_to_test": rev.get("ventures_ready_to_test", UNAVAILABLE),
                     "ventures_testing": rev.get("ventures_testing", UNAVAILABLE),
                     "last_activity": (rev.get("last_revenue_event") or {}).get("timestamp")
                     or UNAVAILABLE},
        blockers=blockers, next_actions=actions)


def trading_section(raw, *, telemetry_max_age_seconds=600):
    registry = raw.get("registry") or []
    plane = raw.get("control_plane") or {}
    account = raw.get("account")
    strategies = plane.get("strategies") or []
    counts = {}
    for s in registry:
        counts[s.get("status")] = counts.get(s.get("status"), 0) + 1
    ladder = [(s.get("evidence_ladder") or {}) for s in strategies]
    live = sum((l.get("live") or {}).get("status") == "PASS" for l in ladder)
    shadow = sum((l.get("demo") or {}).get("status") == "PASS" for l in ladder)
    refuted = sum(bool(s.get("evidence_is_refuted")) for s in strategies)
    validated = sum(bool(s.get("deployable")) for s in strategies)
    candidates = [s for s in strategies if not s.get("evidence_is_refuted")]
    experiments = [w for w in plane.get("work_items") or []
                   if w.get("normalized_status") in {"ACTIVE", "READY"}]
    blocked_items = [s for s in strategies if s.get("blocked_stage") or s.get("blockers")]
    fresh = bool(account and account.get("_online") and
                 isinstance(account.get("_updated_ago"), (int, float)) and
                 account["_updated_ago"] <= telemetry_max_age_seconds)

    def acc(key):
        value = (account or {}).get(key)
        return value if fresh and isinstance(value, (int, float)) else UNAVAILABLE
    balance, equity = acc("balance"), acc("equity")
    floating = (round(equity - balance, 2) if fresh and isinstance(balance, (int, float))
                and isinstance(equity, (int, float)) else UNAVAILABLE)
    protections = [name for name, key in (("ESL", "eslHit"), ("DPT", "dptHit"), ("NEWS", "newsBlock"),
                                          ("PAUSED", "eaPaused")) if fresh and account.get(key)]
    blockers, actions = [], []
    if not fresh:
        blockers.append(_blocker("TRADING_TELEMETRY_UNAVAILABLE",
                                 "telemetria EA assente o non aggiornata: stato conto non mostrato"))
    if blocked_items:
        blockers.append(_blocker("TRADING_EXPERIMENT_BLOCKED",
                                 f"{len(blocked_items)} strategie con stadio bloccato"))
    for s in candidates[:3]:
        if s.get("next_required_stage"):
            actions.append(f"{s['strategy_id']}: {s['next_required_stage']}")
    status = ("LIVE" if live else "SHADOW" if shadow else
              "PARTIAL" if strategies or registry else "UNAVAILABLE")
    return section(
        status=status, health="AMBER" if blockers else "GREEN",
        source="contracts/strategy-registry.json + company control plane + EA telemetry",
        confidence="HIGH" if strategies else "MEDIUM",
        key_metrics={"strategies_total": len(registry),
                     "strategies_by_registry_status": counts,
                     "strategies_candidate": len(candidates),
                     "strategies_analyzed": len(strategies),
                     "experiments_active": len(experiments), "validated": validated,
                     "shadow": shadow, "live": live, "edge_candidates": len(candidates),
                     "refuted": refuted,
                     "evidence_grade": (f"{refuted}/{len(strategies)} refutate, nessuna validata "
                                        "in demo/live" if strategies and not (live or shadow)
                                        else UNAVAILABLE if not strategies else
                                        f"{live} live, {shadow} demo"),
                     "account_state": "LIVE_TELEMETRY" if fresh else UNAVAILABLE,
                     "balance": balance, "equity": equity, "realized_pnl": acc("realized_pnl"),
                     "floating_pnl": floating, "drawdown": acc("drawdown"),
                     "gross_exposure": acc("gross_exposure"),
                     "risk_state": ("PROTECTION_ACTIVE" if protections else "NORMAL")
                     if fresh else UNAVAILABLE,
                     "kill_switch": ("ON" if "PAUSED" in protections else "OFF") if fresh
                     else UNAVAILABLE},
        blockers=blockers, next_actions=actions,
        extra={"next_experiments": actions})


def social_section(agency_snapshot):
    if agency_snapshot is None:
        return unavailable("AI Fashion Agency social layer", "agency store non configurato")
    posts = agency_snapshot.get("social_posts", [])
    accounts = [a for m in agency_snapshot.get("models", []) for a in m.get("social_accounts", [])]
    active = [a for a in accounts if a.get("status") == "ACTIVE"]

    def n(state):
        return sum(p.get("state") == state for p in posts)
    return section(
        status="FOUNDATION" if not active else ("OPERATIONAL" if n("PUBLISHED") else "PARTIAL"),
        health="AMBER" if not active else "GREEN",
        source="AgencyStore social_posts + model accounts", confidence="HIGH",
        key_metrics={"accounts_active": len(active), "accounts_not_created":
                     sum(a.get("status") == "NOT_CREATED" for a in accounts),
                     "drafts": n("DRAFT"), "review_required": n("READY_FOR_REVIEW"),
                     "scheduled": n("SCHEDULED"), "published": n("PUBLISHED"),
                     "inbound": UNAVAILABLE, "dm": UNAVAILABLE},
        blockers=[] if active else [_blocker("SOCIAL_NOT_OPERATIONAL",
                                             "nessun account social creato; pubblicazione disattivata")])


def agency_section(slice_, state):
    if slice_ is None:
        return unavailable("AI Fashion Agency", "agency store non configurato")
    blockers = [_blocker(b["error_code"], f"skill {b['skill']} {b['state']}")
                for b in state.get("worker_blockers", [])]
    blockers += [_blocker("AGENCY_STORE_BLOCKED",
                          f"prodotto '{p['title']}' fermo allo store gate ({p['status']})")
                 for p in state.get("blocked_products", [])[:3]]
    status = ("OPERATIONAL" if state.get("published") else
              "PARTIAL" if slice_["health"] != "NOT_STARTED" else "FOUNDATION")
    health = {"GREEN": "GREEN", "AMBER": "AMBER", "NOT_STARTED": "AMBER"}.get(slice_["health"], "UNKNOWN")
    return section(
        status=status, health=health, source="AgencyStore executive_slice + agency_state",
        confidence="HIGH",
        key_metrics={k: v for k, v in {**slice_, "models_total": state.get("models_total"),
                                       "store_pending": state.get("store_pending"),
                                       "credits_pending_approval": state.get("credits_pending_approval"),
                                       "credits_spent": state.get("credits_spent")}.items()
                     if k not in {"alerts", "next_actions", "business_unit_id", "health"}},
        active_work=[f"modelle al lavoro: {', '.join(state.get('models_working') or []) or 'nessuna'}"],
        blockers=blockers, next_actions=[a.get("what") or a.get("action")
                                         for a in slice_.get("next_actions", [])][:5],
        extra={"worker_blockers": state.get("worker_blockers", []), "alerts": slice_["alerts"]})


def finance_section(raw):
    ledger_events = raw.get("ledger_events") or []
    premium_calls = [e for e in ledger_events if e.get("event_type") == "PROVIDER_CALL_COMPLETED"]
    premium_cost = [float((e.get("payload") or {}).get("cost_usd") or 0) for e in premium_calls
                    if (e.get("payload") or {}).get("cost_usd") is not None]
    agency = raw.get("agency_revenue") or {}
    revenue = raw.get("revenue") or {}
    known_eur = (agency.get("costs_eur") or 0) + (revenue.get("costs_eur") or 0)
    gaps = ["local_model_cost: non misurato (elettricità/PC)",
            "infrastructure_cost: piano Render non presente nei dati"]
    if premium_calls and len(premium_cost) < len(premium_calls):
        gaps.append("alcune chiamate premium senza costo registrato")
    return section(
        status="PARTIAL", health="GREEN", source="EventLedger provider calls + Agency costs + "
        "Revenue costs", confidence="MEDIUM",
        key_metrics={"premium_model_calls": len(premium_calls),
                     "premium_model_cost_usd": round(sum(premium_cost), 4) if premium_cost
                     else (0 if not premium_calls else UNAVAILABLE),
                     "local_model_cost": "NOT_METERED",
                     "higgsfield_credits_spent": agency.get("credits_spent", UNAVAILABLE),
                     "agency_costs_eur": agency.get("costs_eur", UNAVAILABLE),
                     "revenue_costs_eur": revenue.get("costs_eur", UNAVAILABLE),
                     "trading_costs": UNAVAILABLE, "infrastructure_cost": UNAVAILABLE,
                     "known_costs_eur": round(known_eur, 2),
                     "known_revenue_eur": round((agency.get("gross_revenue_eur") or 0) +
                                                (revenue.get("revenue_eur") or 0), 2)},
        extra={"data_gaps": gaps})
