"""Jarvis executive conversation: free-form questions -> NEXUS_EXECUTIVE_STATE_V1.

Pure functions: `detect` maps a message (plus the bounded conversation
context) to an executive intent and a decision policy; `answer` composes a
short Italian briefing from the state.  Structured numbers are always read
from the state, never from a model; ASK_MISTRAL is only chosen for "why"
questions and CREATE_TASK only for real analysis requests (both handled by
the caller in service.py).
"""
from __future__ import annotations

import re

POLICIES = ("ANSWER_FROM_EXECUTIVE_STATE", "ANSWER_FROM_DOMAIN_STATE", "ANSWER_FROM_VAULT",
            "ASK_MISTRAL", "CREATE_TASK", "REQUEST_APPROVAL")

DOMAIN_PATTERNS = (
    ("revenue", r"revenue|ricav\w*|vendit\w*|\blead\b|prospect\w*|ventur\w*|incass\w*"),
    ("trading", r"trading|strategi\w*|\bconto\b|\bpnl\b|\bea\b|\bedge\b|mercat\w*"),
    ("ai_fashion_agency", r"agenzia|agency|modell[ae]\b|fashion"),
    ("social", r"social|tiktok|instagram|\bpost\b"),
    ("system", r"sistema|deploy|\bci\b|server|backend|mistral|infrastruttura|render"),
    ("finance", r"spes[aei]|spend\w*|cost[io]\b|budget|finanz\w*"),
    ("tasks", r"\btask\b"),
)
DOMAIN_LABEL = {"revenue": "Revenue", "trading": "Trading", "ai_fashion_agency": "Agenzia",
                "social": "Social", "system": "Sistema", "finance": "Costi",
                "tasks": "Task", "infrastructure": "Infrastruttura", "approvals": "Approvazioni"}

_CHANGES = re.compile(r"cosa [eè] cambiat|cosa c'?\s?[eè] di nuovo|novit[aà]|\bda ieri\b|cambiat\w* da")
_APPROVALS = re.compile(r"cosa devo approvare|cosa c'?\s?[eè] da approvare|decisioni (?:da prendere|in attesa)|"
                        r"cosa (?:aspetta|attende) (?:me|una mia decisione)|devo decidere")
_TOP = re.compile(r"problema pi[uù] (?:importante|grave|urgente)|priorit[aà] pi[uù] importante|"
                  r"qual [eè] la priorit[aà]|cosa (?:non va|non funziona)\b(?! e)|il problema principale")
_WORKING = re.compile(r"cosa (?:sta funzionando|funziona)")
_SPEND = re.compile(r"quanto (?:stiamo|sto|abbiamo|ho|stai) (?:spendendo|speso|guadagnando|guadagnato)|"
                    r"quanto spendiamo|quanto guadagniamo|quanto (?:costa|ci costa)")
_ACTIVITY = re.compile(r"cosa sta facendo (?:nexus|il sistema|jarvis)|su cosa (?:sta lavorando|lavora)")
_OVERVIEW = re.compile(r"a che punto (?:[eè]|siamo con) (?:nexus|il progetto|il sistema)|come (?:sta|va) nexus|"
                       r"stato (?:di|del) nexus|stato generale|panoramica|come stanno andando le cose|"
                       r"a che punto siamo\b")
_DOMAIN_ASK = re.compile(r"come (?:va|vanno|sta|stanno|procede|procedono)(?: andando)?\b|"
                         r"(?:a che punto|situazione|aggiornamento)\b|\binvece\b|"
                         r"\bstato (?:del|della|dei|delle|di|dello)\b")
_WHY = re.compile(r"\bperch[eé]\b")
_ANALYSIS = re.compile(r"\b(?:analizza|confronta|valuta|studia)\b.*\b(?:business|potenziale|"
                       r"opportunit\w*|venture|strategi\w*)")
_FIX_FOLLOWUP = re.compile(r"risolver\w*|risolvi(?:amo)?|sistemar\w*|si pu[oò] (?:sistemare|risolvere)|"
                           r"come (?:lo |la )?(?:risolviamo|sistemiamo)|chi (?:lo|la) (?:risolve|sistema)")
_NEXT_FOLLOWUP = re.compile(r"^\s*e (?:poi|gli altri|le altre|dopo)\b|^\s*altro\b|^\s*e\?\s*$")
_ELLIPTIC = re.compile(r"^\s*e\s+(?:il|la|le|lo|l'|i|gli)?\s*")

# Known remediation facts per alert code: owner + what fixes it.  Facts only;
# Jarvis never promises a timeline it cannot observe.
PLAYBOOK = {
    "CI_BLOCKING_DEPLOY": ("Codex (test MT5/MACD)",
                           "chiudere i test CI falliti; con CI verde Safe Deploy parte da solo",
                           "dipende da quando Codex chiude quei test: non è un fix che posso fare da qui"),
    "LOCAL_WORKER_UNREACHABLE": ("tu, dal PC",
                                 "avviare start_local_inference.ps1 e aggiornare "
                                 "JARVIS_MINISTRAL_GATEWAY_URL su Render",
                                 "sì, se il PC è acceso: è un riavvio del tunnel, pochi minuti"),
    "APPROVALS_PENDING": ("tu", "rispondere alle decisioni in attesa", "sì, dipende solo da te"),
    "REVENUE_RUNNER_DISABLED": ("tu", "decidere se attivare l'automazione Revenue",
                                "sì, è un flag di configurazione — ma va deciso, non è un bug"),
    "TRADING_TELEMETRY_UNAVAILABLE": ("EA/MT5", "avviare l'EA con telemetria verso il backend",
                                      "sì, se il terminale MT5 è disponibile"),
}


def _domains_in(text):
    return [d for d, pattern in DOMAIN_PATTERNS if re.search(pattern, text)]


def detect(text, context=None, *, agency_query=False):
    """Return {"intent", "policy", "domains"} or None (= not an executive question)."""
    value = (text or "").strip().lower()
    ctx = context or {}
    in_executive = ctx.get("last_view") == "EXECUTIVE"
    domains = _domains_in(value)
    short = len(value.split()) <= 8

    if in_executive and short:
        if _FIX_FOLLOWUP.search(value) and ctx.get("last_executive_topic"):
            return {"intent": "TOPIC_FOLLOWUP", "policy": "ANSWER_FROM_EXECUTIVE_STATE", "domains": []}
        if _NEXT_FOLLOWUP.search(value):
            return {"intent": "NEXT_PROBLEMS", "policy": "ANSWER_FROM_EXECUTIVE_STATE", "domains": []}
        if _ELLIPTIC.match(value) and domains:
            return {"intent": "DOMAIN", "policy": "ANSWER_FROM_DOMAIN_STATE", "domains": domains[:1]}
    if _ANALYSIS.search(value):
        return {"intent": "ANALYSIS", "policy": "CREATE_TASK", "domains": domains}
    if _WHY.search(value) and domains and not re.search(r"\btask\b", value):
        return {"intent": "WHY", "policy": "ASK_MISTRAL", "domains": domains[:1]}
    if _CHANGES.search(value):
        return {"intent": "CHANGES", "policy": "ANSWER_FROM_EXECUTIVE_STATE", "domains": []}
    if _APPROVALS.search(value):
        return {"intent": "APPROVALS", "policy": "ANSWER_FROM_EXECUTIVE_STATE", "domains": []}
    if _TOP.search(value):
        return {"intent": "TOP_PROBLEM", "policy": "ANSWER_FROM_EXECUTIVE_STATE", "domains": []}
    if _WORKING.search(value):
        return {"intent": "WORKING_VS_NOT", "policy": "ANSWER_FROM_EXECUTIVE_STATE", "domains": []}
    if _SPEND.search(value):
        return {"intent": "SPEND", "policy": "ANSWER_FROM_DOMAIN_STATE", "domains": ["finance"]}
    if _ACTIVITY.search(value):
        return {"intent": "ACTIVITY", "policy": "ANSWER_FROM_EXECUTIVE_STATE", "domains": []}
    if _OVERVIEW.search(value) or re.search(r"\bnexus\b", value) and _DOMAIN_ASK.search(value):
        return {"intent": "OVERVIEW", "policy": "ANSWER_FROM_EXECUTIVE_STATE", "domains": []}
    business = [d for d in domains if d not in {"tasks", "finance"}]
    if business and _DOMAIN_ASK.search(value):
        if agency_query and business == ["ai_fashion_agency"] and not in_executive:
            return None  # the Agency's own richer answers keep handling single-agency questions
        return {"intent": "DOMAIN", "policy": "ANSWER_FROM_DOMAIN_STATE", "domains": business}
    return None


# ---- composition -----------------------------------------------------------

STATUS_IT = {"OK": "in ordine", "ATTENTION": "operativo, con punti di attenzione",
             "DEGRADED": "DEGRADED", "CRITICAL": "in stato CRITICO"}


def _n(count, singular, plural):
    return f"{count} {singular if count == 1 else plural}"


def _m(state, domain):
    return state[domain]["key_metrics"]


def system_line(state):
    m, infra = _m(state, "system"), _m(state, "infrastructure")
    parts = ["backend sano" if infra.get("ready") is True else
             "backend non verificato" if infra.get("ready") == "UNAVAILABLE" else "backend con problemi"]
    if m.get("ci") == "FAILING":
        parts.append(f"il deploy è bloccato da {m.get('ci_failing_tests')} failure CI")
    elif m.get("ci") == "UNAVAILABLE":
        parts.append("stato CI non noto")
    if m.get("mistral") in {"UNREACHABLE", "NOT_CONFIGURED"}:
        parts.append("Mistral locale non è raggiungibile")
    elif m.get("mistral") == "UNKNOWN_NOT_PROBED":
        parts.append("Mistral locale non ancora verificato")
    if m.get("deploy_behind_main") is True:
        parts.append("produzione indietro rispetto a main")
    head, rest = parts[0], parts[1:]
    if not rest:
        return head
    joined = rest[0] if len(rest) == 1 else ", ".join(rest[:-1]) + " e " + rest[-1]
    return head + ", ma " + joined


def domain_brief(state, domain):
    sec = state[domain]
    m = sec["key_metrics"]
    label = DOMAIN_LABEL.get(domain, domain)
    if sec["status"] == "UNAVAILABLE":
        return f"{label}: dati non disponibili ({sec['blockers'][0]['detail'] if sec['blockers'] else 'n/d'})."
    if domain == "revenue":
        text = (f"Revenue ({sec['status']}): automazione {'attiva' if m['runner_running'] is True else 'disattivata' if m['runner_enabled'] is False else 'ferma'}, "
                f"{m['prospects']} prospect, {m['qualified_leads']} lead qualificati, {m['drafts_ready']} bozze, "
                f"{m['followups_due']} follow-up, {m['sales']} vendite, ricavi €{m['revenue_eur']:.2f}.")
    elif domain == "trading":
        by = m["strategies_by_registry_status"]
        account = ("conto non disponibile (telemetria EA assente o vecchia, non mostro PnL)"
                   if m["account_state"] == "UNAVAILABLE" else
                   f"balance {m['balance']}, equity {m['equity']}, floating {m['floating_pnl']}, "
                   f"rischio {m['risk_state']}")
        text = (f"Trading ({sec['status']}): {m['strategies_total']} strategie a registro "
                f"({by.get('ACTIVE', 0)} attive nel codice, {by.get('RESEARCH_ONLY', 0)} solo ricerca), "
                f"{m['strategies_candidate']} candidate non refutate su {m['strategies_analyzed']} "
                f"analizzate, {m['validated']} validate, "
                f"{m['shadow']} in demo, {m['live']} live; {account}.")
        if sec.get("next_experiments"):
            text += " Prossimi esperimenti: " + "; ".join(sec["next_experiments"][:2]) + "."
    elif domain == "ai_fashion_agency":
        text = (f"Agenzia ({sec['status']}): {m['models_active']}/{m['models_total']} modelle attive, "
                f"{m['products_found']} prodotti trovati ({m['store_ready']} store-ready), "
                f"{m['content_ready']} contenuti pronti, "
                f"{_n(m['awaiting_approval'], 'decisione', 'decisioni')} in attesa, "
                f"ricavi €{m['revenue']:.2f}, crediti spesi {m['credits_spent']:g}.")
    elif domain == "social":
        text = (f"Social ({sec['status']}): {m['accounts_active']} account attivi, {m['drafts']} bozze, "
                f"{m['scheduled']} programmati, {m['published']} pubblicati; inbound/DM non disponibili.")
    elif domain == "system":
        text = f"Sistema: {system_line(state)}."
    elif domain == "finance":
        return spend_answer(state)
    elif domain == "tasks":
        text = (f"Task: {m['running']} in esecuzione, {m['queued']} in coda, {m['blocked']} bloccate, "
                f"{m['waiting_approval']} in attesa di approvazione, {m['completed_recently']} completate nelle ultime 24h.")
    else:
        text = f"{label}: {sec['status']}."
    if sec["blockers"]:
        text += " Blocker: " + sec["blockers"][0]["detail"] + "."
    if sec["next_actions"]:
        text += " Prossimo passo: " + str(sec["next_actions"][0]) + "."
    return text


def approvals_answer(state):
    items = state["decisions_required"]
    if not items:
        return "Non hai decisioni in attesa."
    parts = []
    for a in items[:4]:
        cost = a.get("cost") or {}
        parts.append(a["reason"] + (f" per {cost['credits']:g} crediti" if cost.get("credits") else ""))
    noun = "decisione" if len(items) == 1 else "decisioni"
    more = f" (+{len(items) - 4} altre)" if len(items) > 4 else ""
    return f"Hai {len(items)} {noun}: " + "; ".join(parts) + more + "."


def top_alert(state):
    return state["alerts"][0] if state["alerts"] else None


def top_problem_answer(state):
    alert = top_alert(state)
    if not alert:
        return "Non vedo problemi aperti: nessun alert attivo.", None
    detail = alert["details"][0] if alert["details"] else alert["code"]
    text = f"Il problema più importante ({alert['severity']}): {detail}."
    if alert["code"] in PLAYBOOK:
        owner, fix, _ = PLAYBOOK[alert["code"]]
        text += f" Chi può sbloccarlo: {owner}. Cosa serve: {fix}."
    return text, {"kind": "ALERT", "code": alert["code"]}


def topic_followup_answer(state, topic):
    code = (topic or {}).get("code")
    still = any(a["code"] == code for a in state["alerts"])
    if not still:
        return f"{code} non risulta più attivo: è già risolto."
    if code in PLAYBOOK:
        owner, fix, today = PLAYBOOK[code]
        return f"Su {code}: {today}. Responsabile: {owner}; passo necessario: {fix}."
    return f"{code} è ancora attivo; non ho una procedura nota per stimare se si risolve oggi."


def next_problems_answer(state, topic):
    code = (topic or {}).get("code")
    rest = [a for a in state["alerts"] if a["code"] != code][:3]
    if not rest:
        return "Non ci sono altri problemi aperti."
    return "Poi: " + "; ".join(f"{a['code']} ({a['severity']})" for a in rest) + "."


def spend_answer(state):
    m = state["finance"]["key_metrics"]
    if state["finance"]["status"] == "UNAVAILABLE":
        return "Costi: dati non disponibili."
    premium = m["premium_model_cost_usd"]
    text = (f"Spesa nota: €{m['known_costs_eur']:.2f} (Agenzia €{m['agency_costs_eur'] if m['agency_costs_eur'] != 'UNAVAILABLE' else 0:.2f}, "
            f"Revenue €{m['revenue_costs_eur'] if m['revenue_costs_eur'] != 'UNAVAILABLE' else 0:.2f}), "
            f"crediti Higgsfield spesi {m['higgsfield_credits_spent']}, "
            f"{m['premium_model_calls']} chiamate premium"
            + (f" (${premium:g})" if isinstance(premium, (int, float)) and premium else "") +
            f". Ricavi osservati: €{m['known_revenue_eur']:.2f}.")
    return text + " Non misurati: costo del modello locale e dell'infrastruttura Render."


def working_answer(state):
    good = [DOMAIN_LABEL[d] for d in ("system", "infrastructure", "tasks", "revenue", "trading",
                                      "ai_fashion_agency", "social")
            if state[d]["health"] == "GREEN"]
    bad = [f"{a['code']}" for a in state["alerts"] if a["severity"] in {"CRITICAL", "IMPORTANT", "WARNING"}]
    return ("Funziona: " + (", ".join(good) or "niente di pienamente verde") + ". "
            "Non funziona o è bloccato: " + (", ".join(bad[:5]) or "nulla di rilevante") + ".")


def activity_answer(state):
    t = state["tasks"]
    m = t["key_metrics"]
    running = ", ".join(w["title"] or w["task_id"] for w in t["active_work"][:3]) or "nessuna task in esecuzione"
    agency = state["ai_fashion_agency"]["active_work"]
    return (f"In questo momento: {running}; {m['queued']} in coda, {m['blocked']} bloccate."
            + (f" Agenzia: {agency[0]}." if agency else ""))


def changes_answer(state, change_set):
    if not change_set or change_set.get("baseline_at") is None:
        return ("Non ho ancora uno snapshot precedente con cui confrontare: da ora registro lo stato, "
                "e alla prossima domanda dopo almeno un'ora potrò dirti cosa è cambiato.")
    parts = []
    if change_set["changes"]:
        parts.append("; ".join(change_set["changes"][:5]))
    if change_set["new_approvals"]:
        parts.append("nuove decisioni: " + "; ".join(change_set["new_approvals"][:3]))
    if change_set["new_alerts"]:
        parts.append("nuovi alert: " + ", ".join(change_set["new_alerts"]))
    if change_set["resolved_alerts"]:
        parts.append("risolti: " + ", ".join(change_set["resolved_alerts"]))
    head = f"Dal {change_set['baseline_at'][:16].replace('T', ' ')} UTC: "
    body = ", ".join(parts) if parts else "nessun cambiamento nei fatti tracciati"
    tail = (" Restano: " + ", ".join(change_set["persisting_alerts"][:3]) + ".") \
        if change_set["persisting_alerts"] else ""
    return head + body + "." + tail


def overview_answer(state):
    progress = state["overall_progress"]
    prog = (f" Maturità business {progress['value']}%." if progress["value"] != "UNAVAILABLE" else "")
    lines = [f"NEXUS è {STATUS_IT[state['overall_status']]}: {system_line(state)}.{prog}"]
    for d in ("revenue", "trading", "ai_fashion_agency"):
        sec = state[d]
        m = sec["key_metrics"]
        if d == "revenue":
            lines.append(f"Revenue {sec['status']}: {m['sales']} vendite, {m['qualified_leads']} lead qualificati.")
        elif d == "trading":
            lines.append(f"Trading {sec['status']}: {m['strategies_candidate']} candidate, "
                         f"{m['validated']} validate, {m['live']} live.")
        else:
            if sec["status"] != "UNAVAILABLE":
                lines.append(f"Agenzia {sec['status']}: {_n(m['awaiting_approval'], 'decisione', 'decisioni')}, "
                             f"{m['store_ready']} prodotti store-ready.")
    if state["decisions_required"]:
        lines.append(approvals_answer(state))
    top, _ = top_problem_answer(state)
    if state["alerts"]:
        lines.append("Priorità: " + top.split(": ", 1)[-1])
    return " ".join(lines)


def answer(intent, state, *, context=None, change_set=None):
    """Return (text, new_context_fields)."""
    ctx = context or {}
    kind = intent["intent"]
    topic = ctx.get("last_executive_topic")
    if kind == "OVERVIEW":
        alert = top_alert(state)
        return overview_answer(state), {"last_executive_topic":
                                        {"kind": "ALERT", "code": alert["code"]} if alert else None}
    if kind == "DOMAIN":
        texts = [domain_brief(state, d) for d in intent["domains"]]
        return " ".join(texts), {"last_executive_domain": intent["domains"][-1]}
    if kind == "APPROVALS":
        return approvals_answer(state), {"last_executive_topic": {"kind": "APPROVALS",
                                                                  "code": "APPROVALS_PENDING"}}
    if kind == "TOP_PROBLEM":
        text, new_topic = top_problem_answer(state)
        return text, {"last_executive_topic": new_topic}
    if kind == "TOPIC_FOLLOWUP":
        return topic_followup_answer(state, topic), {}
    if kind == "NEXT_PROBLEMS":
        return next_problems_answer(state, topic), {}
    if kind == "SPEND":
        return spend_answer(state), {"last_executive_domain": "finance"}
    if kind == "WORKING_VS_NOT":
        return working_answer(state), {}
    if kind == "ACTIVITY":
        return activity_answer(state), {"last_executive_domain": "tasks"}
    if kind == "CHANGES":
        return changes_answer(state, change_set), {}
    if kind == "WHY":
        return domain_brief(state, intent["domains"][0]), {"last_executive_domain": intent["domains"][0]}
    raise ValueError(f"unsupported executive intent {kind}")
