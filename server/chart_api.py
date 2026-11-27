"""CHART-REAL-DATA-V1 - logica delle API del Chart (reale o esplicitamente indisponibile; il sintetico vive solo in `demo_ohlc`, separato e disattivato di default).

Contratto di risposta di /api/chart/ohlc (campi obbligatori): dataset_id, source (classificazione), feed_kind, broker_server, symbol_requested, symbol_actual, timeframe, available_range,
last_update_at, status (AVAILABLE_OFFLINE | UNAVAILABLE), quality, limitations[], dataset_version, mode (HISTORICAL), has_more/next_before, bars[]. Ogni barra porta `completeness`
(COMPLETE|PARTIAL|GAP|OPEN) e `minutes_present/minutes_missing`: una barra parziale NON e' presentata come completa.
Errori: richiesta invalida 422; partizione non autorizzata 403 (mai dati); store/dataset assente = 200 + status UNAVAILABLE con motivo (es. PC scollegato);
integrita' compromessa (hash segmento) = 503.
"""
from __future__ import annotations

import hashlib
import math
import os
import time as _time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException

import chart_guard
import chart_store

PIP = {"GOLD": {"pip_price_usd_per_oz": 0.10, "source": "OWNER_RESEARCH_CONVENTION (D8, 2026-11-27)", "applies_to": ["GOLD", "XAUUSD"]}}
GOLD_ALIASES = {"GOLD", "XAUUSD"}
_guard_cache: dict = {}


def store_root() -> str:
    return os.environ.get("NEXUS_CHART_STORE_ROOT", "").strip()


def get_guard() -> chart_guard.Guard:
    key = (os.environ.get("NEXUS_CHART_AUTH_FILE", ""), os.environ.get("NEXUS_CHART_PARTITION_DIR", ""))
    g = _guard_cache.get(key)
    if g is None:
        g = _guard_cache[key] = chart_guard.Guard()
    return g


def reset_caches() -> None:
    _guard_cache.clear()


def _iso(t: int | None) -> str | None:
    return None if t is None else datetime.fromtimestamp(t, timezone.utc).isoformat(timespec="seconds")


def _unavailable(reason: str, symbol: str = "", tf: str = "", source: str | None = None, detail: str = "") -> dict:
    return {"status": "UNAVAILABLE", "reason": reason, "detail": detail, "dataset_id": source, "source": "UNAVAILABLE", "provenance": "UNAVAILABLE", "symbol_requested": symbol, "timeframe": tf,
            "demo": False, "mode": "HISTORICAL", "bars": [], "candles": [], "has_more": False, "next_before": None, "limitations": ["NO_REAL_DATA_SERVED"]}


def _manifest_version(root: Path, dsid: str) -> str:
    try:
        return hashlib.sha256((root / dsid / "manifest.json").read_bytes()).hexdigest()
    except OSError:
        return ""


def _summary(store: chart_store.ChartStore, dsid: str, guard: chart_guard.Guard) -> dict:
    m = store.manifest(dsid)
    wins = guard.windows(dsid)
    cov = m["coverage"]
    return {"dataset_id": dsid, "feed_kind": m.get("feed_kind"), "broker_server": m.get("broker_server"), "label": m.get("label") or dsid, "symbol_actual": m.get("symbol_actual"),
            "symbol_aliases": m.get("symbol_aliases", []), "timeframes": m["tf_available"], "available_range": {"first": cov["first_t"], "last": cov["last_end_t"] - 60, "first_iso": _iso(cov["first_t"]), "last_iso": _iso(cov["last_end_t"] - 60)},
            "authorized": bool(wins) and guard.error is None, "authorized_windows": [[a, b] for a, b in wins], "guard_error": guard.error, "live": bool(m.get("live")), "clock_basis": m.get("clock_basis"),
            "calendar_status": (m.get("calendar") or {}).get("status"), "completeness_counts": m.get("completeness_counts"), "instrument_spec": instrument_spec(m), "provenance": m.get("provenance"),
            "dataset_version": _manifest_version(store.root, dsid), "last_update_at": m.get("built_at"), "purpose": m.get("purpose")}


def instrument_spec(m: dict) -> dict:
    """Grandezze mantenute SEPARATE (D8). Valore assente = NOT_RECORDED, mai stimato."""
    s = dict(m.get("instrument_spec") or {})
    names = ("point", "tick_size", "tick_value", "contract_size", "account_currency", "digits", "price_unit")
    out = {k: s.get(k, "NOT_RECORDED") for k in names}
    out["pip_convention"] = PIP["GOLD"] if (m.get("symbol_actual") or "").upper() in GOLD_ALIASES else "NOT_DEFINED_FOR_SYMBOL"
    out["price_change"] = "absolute price difference (not scaled)"
    return out


def _is_broker(store: chart_store.ChartStore, dsid: str) -> bool:
    try:
        return str(store.manifest(dsid).get("feed_kind", "")).startswith("MT5")
    except chart_store.StoreError:
        return False


def sources() -> dict:
    root = store_root()
    if not root:
        return {"status": "UNAVAILABLE", "reason": "CHART_STORE_NOT_CONFIGURED", "sources": [], "demo_enabled": demo_enabled()}
    store = chart_store.ChartStore(root)
    guard = get_guard()
    out = []
    # il feed del broker (export MT5) precede qualunque fonte alternativa nella scelta predefinita; le fonti non vengono mai mescolate
    order = sorted(store.datasets(), key=lambda d: (not _is_broker(store, d), d))
    for dsid in order:
        try:
            out.append(_summary(store, dsid, guard))
        except chart_store.StoreError as ex:
            out.append({"dataset_id": dsid, "status": "UNAVAILABLE", "reason": ex.code})
    return {"status": "AVAILABLE" if out else "UNAVAILABLE", "reason": None if out else "NO_DATASETS", "sources": out, "default_source": os.environ.get("NEXUS_CHART_DEFAULT_SOURCE") or (out[0]["dataset_id"] if out else None),
            "demo_enabled": demo_enabled(), "guard_error": guard.error}


def demo_enabled() -> bool:
    return os.environ.get("NEXUS_CHART_DEMO", "") == "1"


def ohlc(source: str, symbol: str, tf: str, limit: int, before: int | None) -> dict:
    sym = (symbol or "").strip().upper()
    if tf not in chart_store.ALL_TFS:
        raise HTTPException(422, detail={"code": "TIMEFRAME_UNSUPPORTED", "supported": list(chart_store.ALL_TFS)})
    if not isinstance(limit, int) or not 1 <= limit <= chart_store.MAX_LIMIT:
        raise HTTPException(422, detail={"code": "LIMIT_INVALID", "max": chart_store.MAX_LIMIT})
    if before is not None and (not isinstance(before, int) or before < 0 or before > 4102444800):
        raise HTTPException(422, detail={"code": "BEFORE_INVALID"})
    root = store_root()
    if not root:
        return _unavailable("CHART_STORE_NOT_CONFIGURED", sym, tf, source or None)
    store = chart_store.ChartStore(root)
    guard = get_guard()
    dsid = (source or os.environ.get("NEXUS_CHART_DEFAULT_SOURCE") or "").strip()
    try:
        if not dsid:
            for cand in sorted(store.datasets(), key=lambda d: (not _is_broker(store, d), d)):
                if sym in [a.upper() for a in store.manifest(cand).get("symbol_aliases", [])]:
                    dsid = cand
                    break
        if not dsid:
            return _unavailable("NO_DATASET_FOR_SYMBOL", sym, tf)
        m = store.manifest(dsid)
        if sym and sym not in [a.upper() for a in m.get("symbol_aliases", [])]:
            raise HTTPException(422, detail={"code": "SYMBOL_NOT_IN_DATASET", "dataset_id": dsid, "aliases": m.get("symbol_aliases", [])})
        if tf not in m["tf_available"]:
            raise HTTPException(422, detail={"code": "TIMEFRAME_NOT_AVAILABLE", "dataset_id": dsid, "available": m["tf_available"]})
        r = store.read(dsid, tf, limit, before, guard=guard, now=int(_time.time()))
    except chart_guard.PartitionDenied as ex:
        raise HTTPException(403, detail={"code": ex.code, "message": "Dati non autorizzati per il Chart"})
    except chart_store.StoreError as ex:
        if ex.code in ("STORE_UNREACHABLE",):
            return _unavailable("SOURCE_UNREACHABLE", sym, tf, dsid or None, ex.code)
        if ex.code in ("SEGMENT_HASH_MISMATCH", "MANIFEST_INVALID"):
            raise HTTPException(503, detail={"code": ex.code})
        raise HTTPException(422 if ex.code in ("TIMEFRAME_UNSUPPORTED", "LIMIT_INVALID", "DATASET_ID_INVALID", "TIMEFRAME_NOT_AVAILABLE") else 503, detail={"code": ex.code})
    bars = r["bars"]
    cov = m["coverage"]
    counts = {}
    for b in bars:
        counts[b["completeness"]] = counts.get(b["completeness"], 0) + 1
    limits = ["CLOCK_OFFSET_UNVERIFIED (orologio del terminale: non UTC certificato)"] if (m.get("clock_basis") or "").upper().startswith("TERMINAL") else []
    if (m.get("calendar") or {}).get("status") != "VERIFIED":
        limits.append("BROKER_CALENDAR_UNVERIFIED (le barre con minuti mancanti spiegati solo dal calendario candidato sono PARTIAL)")
    if m.get("purpose"):
        limits.append("PURPOSE:" + str(m["purpose"]))
    if m.get("feed_kind") == "DUKASCOPY":
        limits.append("FEED_IS_DUKASCOPY_NOT_BROKER_MT5")
    return {"status": "AVAILABLE_OFFLINE", "reason": None, "dataset_id": dsid, "source": "REAL_HISTORICAL", "provenance": "REAL_HISTORICAL", "feed_kind": m.get("feed_kind"), "broker_server": m.get("broker_server"),
            "symbol_requested": sym, "symbol_actual": m.get("symbol_actual"), "timeframe": tf, "mode": "LIVE" if m.get("live") else "HISTORICAL", "demo": False,
            "available_range": {"first": cov["first_t"], "last": cov["last_end_t"] - 60, "first_iso": _iso(cov["first_t"]), "last_iso": _iso(cov["last_end_t"] - 60)},
            "last_update_at": m.get("built_at"), "dataset_version": _manifest_version(Path(root), dsid), "calendar_status": (m.get("calendar") or {}).get("status"), "clock_basis": m.get("clock_basis"),
            "quality": {"verdict": m.get("quality_verdict"), "completeness_in_response": counts, "completeness_in_dataset": (m.get("completeness_counts") or {}).get(tf)}, "instrument_spec": instrument_spec(m),
            "limitations": limits, "has_more": r["has_more"], "next_before": r["next_before"], "bars": bars, "candles": bars}


def demo_ohlc(symbol: str, tf: str, limit: int) -> dict:
    """Serie SINTETICA di dimostrazione: solo con NEXUS_CHART_DEMO=1 e source=SYNTHETIC_DEMO. Rispetta il timeframe (correzione del difetto storico dei 900 s)."""
    if tf not in chart_store.TF_SECONDS:
        raise HTTPException(422, detail={"code": "TIMEFRAME_UNSUPPORTED_IN_DEMO"})
    step = chart_store.TF_SECONDS[tf]
    base = 2350.0 if symbol.upper().startswith(("XAU", "GOLD")) else 1.10
    unit = base * 0.001
    now = int(_time.time()) // step * step
    t0 = now - limit * step
    price, bars = base, []
    for i in range(limit):
        drift = math.sin(i / 9.0) * unit * 3 + ((i * 53) % 7 - 3) * unit
        o, c = price, price + drift
        bars.append({"time": t0 + i * step, "open": round(o, 3), "high": round(max(o, c) + abs(drift) * 0.5, 3), "low": round(min(o, c) - abs(drift) * 0.5, 3), "close": round(c, 3), "completeness": "COMPLETE"})
        price = c
    return {"status": "AVAILABLE_DEMO", "symbol_requested": symbol, "timeframe": tf, "bars": bars, "candles": bars, "source": "SYNTHETIC_DATA", "provenance": "SYNTHETIC_DATA", "dataset_id": "SYNTHETIC_DEMO",
            "demo": True, "mode": "DEMO", "has_more": False, "next_before": None, "limitations": ["SYNTHETIC_DATA_NOT_MARKET"]}
