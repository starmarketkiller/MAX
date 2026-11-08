"""Projection of the nucleus register. It does not replace overall_progress
and it does not repair local-operation defects.

Three surfaces stay separate: criterion score and validity, service
availability observed now, and inference that was actually verified.
A closed port is OFFLINE. A health response is not an inference.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

SCHEMA = "NEXUS_NUCLEUS_PROGRESS_V1"
TELEMETRY_MAX_AGE_SECONDS = 600
FROZEN_DENOMINATOR = 20
FROZEN_POINTS_PER_PASS = 5
FROZEN_MAX_POINTS = FROZEN_DENOMINATOR * FROZEN_POINTS_PER_PASS

BLOCK_ACTIONS = {
    "HEALTH_NOT_INFERENCE": "tenere health e inferenza su campi distinti; un 200 non certifica una generazione",
    "HTTP_DEFAULT_MODEL_FAILED": "in un task successivo far fallire in modo esplicito il modello predefinito assente, oppure selezionare un modello installato sul percorso HTTP",
    "WARMUP_OK_WITHOUT_GENERATION": "in un task successivo dichiarare il warmup ok solo dopo una generazione non vuota",
    "ROUTER_TIMEOUT_SHORTER_THAN_COLD_START": "in un task successivo alzare il timeout del router sopra il cold start misurato, oppure lasciare il router spento",
    "GATEWAY_START_NOT_IDEMPOTENT": "in un task successivo far uscire start_gateway.ps1 quando la porta e' gia' in ascolto",
    "STABLE_ENDPOINT_PREPARED_NOT_APPLIED": "applicare endpoint stabile e startup solo dopo un'autorizzazione esplicita",
    "REMOTE_CONNECTION_UNCERTIFIED": "certificare il collegamento remoto in una prova separata; reboot e tunnel non eseguiti restano non certificati",
    "TASK_CONCLUDED_DELIVERY_FAILED": "non contare come successo una task conclusa la cui consegna e' fallita",
}


def unavailable_projection():
    return {
        "schema_version": SCHEMA,
        "criteria": {"state": "UNAVAILABLE", "current_points": None, "current_percent": None,
                     "register_points": None, "register_percent": None,
                     "historical_label": "valori storici memorizzati nel registro",
                     "denominator": FROZEN_DENOMINATOR, "points_per_pass": FROZEN_POINTS_PER_PASS,
                     "items": [], "reads_as_completion": False, "source": "PROGRESS_V1.json"},
        "service_availability": {"state": "UNAVAILABLE", "any_online": None, "services": []},
        "verified_inference": {"state": "UNAVAILABLE", "historical_success": None,
                               "currently_available": None, "evidence_refs": []},
        "blocks": [],
        "proposals": [],
        "sources": [],
    }


def _parse_time(value):
    if not value or not isinstance(value, str):
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _age_seconds(observed_at, now):
    stamp = _parse_time(observed_at)
    if stamp is None:
        return None
    return (now - stamp).total_seconds()


def _fresh(observed_at, now):
    age = _age_seconds(observed_at, now)
    return age is not None and 0 <= age <= TELEMETRY_MAX_AGE_SECONDS


def _current_percent(points):
    if points is None:
        return None
    return (points * 100) // FROZEN_MAX_POINTS


def _historical(score):
    if not isinstance(score, dict):
        return {"register_points": None, "register_percent": None}
    points = score.get("points")
    percent = score.get("percent")
    return {
        "register_points": points if isinstance(points, int) else None,
        "register_percent": percent if isinstance(percent, int) else None,
    }


def _no_current(score):
    return {
        "state": "UNAVAILABLE", "current_points": None, "current_percent": None,
        "denominator": FROZEN_DENOMINATOR, "points_per_pass": FROZEN_POINTS_PER_PASS,
        "historical_label": "valori storici memorizzati nel registro",
        "items": [], "reads_as_completion": False, "source": "PROGRESS_V1.json",
        **_historical(score),
    }


def _automated_blobs_match(item, current_blobs):
    cited = item.get("blob_shas") or {}
    if not cited or not isinstance(current_blobs, dict):
        return False
    return all(current_blobs.get(path) == digest for path, digest in cited.items())


def _validity(item, effective):
    if item.get("proof_class") == "AUTOMATED_TEST":
        if effective == "STALE":
            return "condizionata ai blob citati, non piu' coincidente"
        return "condizionata ai blob citati"
    if item.get("valid_until"):
        return f"fino a {item['valid_until']}"
    return "validita' runtime non determinata"


def _criteria(register, now, current_blobs):
    if not isinstance(register, dict) or not isinstance(register.get("score"), dict):
        return _no_current({})
    score = register["score"]
    if register.get("frozen") is False or register.get("baseline_status") == "BASELINE_PENDING":
        return _no_current(score)
    if not isinstance(score.get("points"), int):
        return _no_current(score)
    items = []
    counted = 0
    for cid, item in (register.get("criteria") or {}).items():
        stored = item.get("status")
        valid_until = item.get("valid_until")
        expires = _parse_time(valid_until)
        stale = expires is not None and expires < now
        if item.get("proof_class") == "AUTOMATED_TEST" and not _automated_blobs_match(item, current_blobs):
            stale = True
        effective = "STALE" if stale else stored
        points = item.get("points") if isinstance(item.get("points"), int) else 0
        counted_points = points if effective == "PASS" else 0
        counted += counted_points
        items.append({
            "id": cid, "stored_status": stored, "effective_status": effective,
            "points_stored": points, "points_counted": counted_points,
            "valid_until": valid_until, "proof_class": item.get("proof_class"),
            "validity": _validity(item, effective),
        })
    previous = score.get("previous_points")
    delta = score.get("delta_points")
    regression = (isinstance(delta, int) and delta < 0) or (
        isinstance(previous, int) and score["points"] < previous)
    all_stale = bool(items) and all(item["effective_status"] == "STALE" for item in items)
    if all_stale:
        state = "STALE"
        counted = None
    elif regression:
        state = "REGRESSION"
    else:
        state = "CURRENT"
    return {
        "state": state,
        "current_points": counted,
        "current_percent": _current_percent(counted),
        "denominator": FROZEN_DENOMINATOR,
        "points_per_pass": FROZEN_POINTS_PER_PASS,
        "historical_label": "valori storici memorizzati nel registro",
        "previous_points": previous,
        "delta_points": delta,
        "items": items,
        "reads_as_completion": False,
        "source": "PROGRESS_V1.json",
        **_historical(score),
    }


def _services(observations, now):
    if not observations:
        return {"state": "UNAVAILABLE", "any_online": None, "services": []}
    services = []
    fresh_flags = []
    for item in observations:
        fresh = _fresh(item.get("observed_at"), now)
        fresh_flags.append(fresh)
        listening = item.get("listening")
        if not fresh:
            availability = "STALE"
            published_listening = None
        elif listening is True:
            availability = "ONLINE"
            published_listening = True
        elif listening is False:
            availability = "OFFLINE"
            published_listening = False
        else:
            availability = "UNAVAILABLE"
            published_listening = None
        services.append({
            "name": item.get("name"), "port": item.get("port"),
            "listening": published_listening, "availability": availability,
            "observed_at": item.get("observed_at"),
        })
    if not any(fresh_flags):
        return {"state": "STALE", "any_online": None, "services": services}
    return {
        "state": "CURRENT",
        "any_online": any(item["availability"] == "ONLINE" for item in services),
        "services": services,
    }


def _block(code, evidence_refs):
    return {"code": code, "resolved": False, "evidence_refs": list(evidence_refs or []),
            "next_action": BLOCK_ACTIONS[code]}


def _operations_blocks(operations):
    if not isinstance(operations, dict):
        return []
    evidence = operations.get("evidence_refs") or []
    blocks = []
    if operations.get("health_reachable") and not operations.get("inference_http_succeeded"):
        blocks.append(_block("HEALTH_NOT_INFERENCE", evidence))
    if operations.get("http_default_model_ok") is False:
        blocks.append(_block("HTTP_DEFAULT_MODEL_FAILED", evidence))
    if operations.get("warmup_declared_ok") and not operations.get("warmup_generation_ok"):
        blocks.append(_block("WARMUP_OK_WITHOUT_GENERATION", evidence))
    router = operations.get("router_timeout_seconds")
    cold = operations.get("cold_start_seconds")
    if isinstance(router, (int, float)) and isinstance(cold, (int, float)) and router < cold:
        blocks.append(_block("ROUTER_TIMEOUT_SHORTER_THAN_COLD_START", evidence))
    if operations.get("gateway_start_idempotent") is False:
        blocks.append(_block("GATEWAY_START_NOT_IDEMPOTENT", evidence))
    if operations.get("stable_endpoint") == "PREPARED_NOT_APPLIED" or \
            operations.get("persistent_startup") == "PREPARED_NOT_APPLIED":
        blocks.append(_block("STABLE_ENDPOINT_PREPARED_NOT_APPLIED", evidence))
    if operations.get("remote_connection") == "REMOTE_UNCERTIFIED":
        blocks.append(_block("REMOTE_CONNECTION_UNCERTIFIED", evidence))
    return blocks


def _proposals(operations):
    if not isinstance(operations, dict):
        return []
    proposals = []
    for name in ("stable_endpoint", "persistent_startup", "remote_connection"):
        status = operations.get(name)
        if status is None:
            continue
        executed = False if status in {"PREPARED_NOT_APPLIED", "REMOTE_UNCERTIFIED"} else bool(status)
        proposals.append({"name": name, "status": status, "executed": executed,
                          "reads_as_execution": False})
    return proposals


def _inference(inference, services, operations):
    if inference is None and not isinstance(operations, dict):
        return {"state": "UNAVAILABLE", "historical_success": None,
                "currently_available": None, "evidence_refs": []}
    historical = bool((inference or {}).get("historical_success"))
    evidence = list((inference or {}).get("evidence_refs") or [])
    live_generation = bool((inference or {}).get("live_generation_ok"))
    fresh_offline = services["state"] == "CURRENT" and services["any_online"] is False
    fresh_online = services["state"] == "CURRENT" and services["any_online"] is True
    http_failed = isinstance(operations, dict) and operations.get("http_default_model_ok") is False
    warmup_empty = isinstance(operations, dict) and operations.get("warmup_declared_ok") and \
        not operations.get("warmup_generation_ok")
    if services["state"] in {"UNAVAILABLE", "STALE"}:
        current = None
    elif fresh_offline or not live_generation or http_failed or warmup_empty:
        current = False
    elif fresh_online and live_generation and not http_failed and not warmup_empty:
        current = True
    else:
        current = False
    if historical and not live_generation:
        current = False if services["state"] == "CURRENT" else current
    return {
        "state": "VERIFIED_PAST" if historical else "UNVERIFIED",
        "historical_success": historical,
        "currently_available": current,
        "model": (inference or {}).get("model"),
        "evidence_refs": evidence,
    }


def project(*, register=None, service_observations=None, inference=None,
            local_operations=None, delivery=None, now=None, current_blobs=None):
    now = now or datetime.now(timezone.utc)
    criteria = _criteria(register, now, current_blobs)
    criteria["generated_at"] = now.isoformat()
    services = _services(service_observations, now)
    inferred = _inference(inference, services, local_operations)
    blocks = _operations_blocks(local_operations)
    if isinstance(delivery, dict) and delivery.get("concluded") and delivery.get("delivered") is False:
        blocks.append(_block("TASK_CONCLUDED_DELIVERY_FAILED", delivery.get("evidence_refs") or []))
        criteria["reads_as_completion"] = False
    for item in services["services"]:
        if item["listening"] is False and item["availability"] == "ONLINE":
            item["availability"] = "OFFLINE"
    if inferred["currently_available"] is True and services.get("any_online") is not True:
        inferred["currently_available"] = False
    return {
        "schema_version": SCHEMA,
        "criteria": criteria,
        "service_availability": services,
        "verified_inference": inferred,
        "blocks": blocks,
        "proposals": _proposals(local_operations),
        "sources": ["PROGRESS_V1.json", "service port probe", "T04 local operations evidence"],
    }


def states_are_distinct(document):
    criteria = document["criteria"]
    services = document["service_availability"]
    inferred = document["verified_inference"]
    points = criteria.get("current_points")
    percent = criteria.get("current_percent")
    if (points is None) != (percent is None):
        return False
    if isinstance(points, int) and percent != (points * 100) // FROZEN_MAX_POINTS:
        return False
    if criteria["state"] == "UNAVAILABLE" and isinstance(points, (int, float)):
        return False
    for item in services["services"]:
        if item["listening"] is False and item["availability"] == "ONLINE":
            return False
        if item["availability"] == "STALE" and item["listening"] is True:
            return False
    if services["state"] == "STALE" and isinstance(services["any_online"], bool):
        return False
    if inferred["currently_available"] is True and services.get("any_online") is not True:
        return False
    codes = {block["code"] for block in document["blocks"]}
    if "HEALTH_NOT_INFERENCE" in codes and inferred["currently_available"] is True:
        return False
    if "WARMUP_OK_WITHOUT_GENERATION" in codes and inferred["currently_available"] is True:
        return False
    if "HTTP_DEFAULT_MODEL_FAILED" in codes and inferred["currently_available"] is True:
        return False
    for proposal in document["proposals"]:
        if proposal["status"] in {"PREPARED_NOT_APPLIED", "REMOTE_UNCERTIFIED"} and proposal["executed"]:
            return False
    if any(block["code"] == "TASK_CONCLUDED_DELIVERY_FAILED" for block in document["blocks"]) and \
            criteria.get("reads_as_completion"):
        return False
    return True


def render_consultation(document):
    criteria = document["criteria"]
    services = document["service_availability"]
    inferred = document["verified_inference"]
    lines = ["Punteggio criteri"]
    if criteria["current_points"] is None:
        lines.append(f"stato: {criteria['state']}")
        lines.append("punti correnti: non disponibili")
        lines.append("percentuale corrente: non disponibile")
    else:
        lines.append(f"stato: {criteria['state']}")
        lines.append(f"punti correnti: {criteria['current_points']}")
        lines.append(f"percentuale corrente: {criteria['current_percent']}")
        lines.append("completamento: no")
    if criteria.get("register_points") is not None:
        lines.append(f"punti storici di registro: {criteria['register_points']}")
        lines.append(f"percentuale storica di registro: {criteria.get('register_percent')}")
        lines.append(criteria.get("historical_label") or "valori storici memorizzati nel registro")
    for item in criteria["items"]:
        lines.append(f"{item['id']}: {item['effective_status']}, {item['validity']}")
    lines.extend(["", "Disponibilita servizi"])
    if services["state"] == "UNAVAILABLE":
        lines.append("stato: UNAVAILABLE")
    elif services["state"] == "STALE":
        lines.append("stato: STALE")
        lines.append("servizi online: dato scaduto, nessun numero")
    else:
        lines.append(f"qualche servizio online: {'si' if services['any_online'] else 'no'}")
        for item in services["services"]:
            lines.append(f"{item['name']} porta {item['port']}: {item['availability']}")
    lines.extend(["", "Inferenza verificata"])
    if inferred["state"] == "UNAVAILABLE":
        lines.append("stato: UNAVAILABLE")
    else:
        lines.append(f"verifica passata: {'si' if inferred['historical_success'] else 'no'}")
        current = inferred["currently_available"]
        lines.append("disponibile ora: " + ("si" if current is True else "no" if current is False else "non nota"))
        if inferred.get("model"):
            lines.append(f"modello della verifica passata: {inferred['model']}")
    if document["blocks"]:
        lines.extend(["", "Blocchi aperti"])
        for block in document["blocks"]:
            lines.append(f"{block['code']}: {block['next_action']}")
    for proposal in document["proposals"]:
        lines.append(f"{proposal['name']}: {proposal['status']}")
    return "\n".join(lines) + "\n"


class IsolatedConsultationSink:
    """Persists a consultation on disk. It has no network and no bot token."""

    isolated = True
    network = False

    def __init__(self, path):
        self.path = path
        self.records = []

    def deliver(self, document):
        if not states_are_distinct(document):
            raise RuntimeError("consultation refused: executive surfaces are not distinct")
        record = {
            "timestamp": document["criteria"].get("generated_at"),
            "source": document["criteria"].get("source"),
            "text": render_consultation(document),
            "projection": document,
        }
        self.records.append(record)
        self.path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return record


def deliver_consultation(document, sink):
    if getattr(sink, "network", True) or not getattr(sink, "isolated", False):
        raise RuntimeError("telegram delivery is refused; the sink is not isolated")
    return sink.deliver(document)
