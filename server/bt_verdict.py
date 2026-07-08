"""
bt_verdict.py - Verdetti per-strategia dai CSV reali dei test MT5.

Condivide la logica di tools/nexus_analyze.py ma espone una funzione pura che
prende il testo del CSV (formato ';' emesso dall'OnTester logger dell'EA, o ','
di export generici) e restituisce un dict pronto per il frontend del Backtest Lab.
"""
from __future__ import annotations

import csv
import io

MIN_TRADES_DEFAULT = 10

BLOCKERS = ["NONE", "NO_SIGNAL", "COOLDOWN", "MTF", "HTF", "VELOCITY", "NEWS",
            "SPREAD", "PROTECTIONS", "SCORE_BELOW", "PREFLIGHT", "LICENSE",
            "PAUSED", "SEND_FAILED"]

VERDICT_RANK = {"FORTE": 0, "OK": 1, "DEBOLE": 2, "CRITICA": 3,
                "BLOCCATA": 4, "POCHI_DATI": 5, "NO_SETUP": 6}


def _f(row, key, default=0.0):
    try:
        return float(row.get(key, default) or default)
    except (ValueError, TypeError):
        return default


def _i(row, key, default=0):
    try:
        return int(float(row.get(key, default) or default))
    except (ValueError, TypeError):
        return default


def _blocker_name(v):
    s = str(v).strip()
    if s.isdigit() and int(s) < len(BLOCKERS):
        return BLOCKERS[int(s)]
    return s or "?"


def _verdict(row, min_trades):
    executed = _i(row, "executed") or _i(row, "trades")
    setup = _i(row, "setup")
    pf = _f(row, "profit_factor")
    exp = _f(row, "expectancy_R")
    wr = _f(row, "winrate_pct") or _f(row, "win_rate")

    if executed < min_trades:
        if setup == 0 and executed == 0:
            return "NO_SETUP", "il pattern non si forma (raro/assente su questo simbolo)"
        if setup > 0 and executed <= 1:
            return "BLOCCATA", f"forma il setup ma non apre (blocco: {_blocker_name(row.get('dominant_blocker', '?'))})"
        return "POCHI_DATI", f"solo {executed} trade: campione troppo piccolo per giudicare"

    if pf >= 1.5 and exp > 0:
        return "FORTE", f"PF {pf:.2f}, expectancy {exp:+.2f}R, WR {wr:.0f}%"
    if pf >= 1.15 and exp > 0:
        return "OK", f"PF {pf:.2f}, expectancy {exp:+.2f}R"
    if pf >= 0.95:
        return "DEBOLE", f"PF {pf:.2f}: intorno al break-even, nessun edge chiaro"
    return "CRITICA", f"PF {pf:.2f}, expectancy {exp:+.2f}R: perde soldi, spegnere live"


def _hold_min(open_iso, close_iso):
    """Minuti di durata da due timestamp ISO; None se non calcolabile."""
    from datetime import datetime
    try:
        a = datetime.fromisoformat(str(open_iso).replace("Z", ""))
        b = datetime.fromisoformat(str(close_iso).replace("Z", ""))
        d = (b - a).total_seconds() / 60.0
        return d if d >= 0 else None
    except (ValueError, TypeError):
        return None


def _verdict_live(n, pf, net, wr, min_trades):
    if n < min_trades:
        return "POCHI_DATI", f"solo {n} trade: campione troppo piccolo per giudicare"
    if pf >= 1.5 and net > 0:
        return "FORTE", f"PF {pf:.2f}, net {net:+.2f}, WR {wr:.0f}%"
    if pf >= 1.15 and net > 0:
        return "OK", f"PF {pf:.2f}, net {net:+.2f}"
    if pf >= 0.95:
        return "DEBOLE", f"PF {pf:.2f}: intorno al break-even"
    return "CRITICA", f"PF {pf:.2f}, net {net:+.2f}: perde soldi, spegnere live"


def analyze_live_trades(trades: list, min_trades: int = MIN_TRADES_DEFAULT) -> dict:
    """Verdetti per-strategia dai trade REALI sincronizzati (tabella trades):
    stessa forma di analyze_stats_csv, cosi' il frontend riusa la stessa tabella.
    Raggruppa per strategia, calcola PF/win-rate/net/hold e assegna il verdetto."""
    from collections import defaultdict
    g = defaultdict(lambda: {"n": 0, "wins": 0, "losses": 0,
                             "gw": 0.0, "gl": 0.0, "net": 0.0, "hold": []})
    for t in trades or []:
        strat = (t.get("strategy") or "").strip() or "?"
        pnl = t.get("pnl")
        if pnl is None:
            continue
        try:
            pnl = float(pnl)
        except (ValueError, TypeError):
            continue
        d = g[strat]
        d["n"] += 1
        d["net"] += pnl
        if pnl > 0:
            d["wins"] += 1
            d["gw"] += pnl
        elif pnl < 0:
            d["losses"] += 1
            d["gl"] += abs(pnl)
        h = _hold_min(t.get("openTime"), t.get("closeTime"))
        if h is not None:
            d["hold"].append(h)

    rows = []
    for strat, d in g.items():
        n = d["n"]
        pf = (d["gw"] / d["gl"]) if d["gl"] > 0 else (99.0 if d["gw"] > 0 else 0.0)
        wr = (100.0 * d["wins"] / n) if n else 0.0
        avg = (d["net"] / n) if n else 0.0
        hold = (sum(d["hold"]) / len(d["hold"])) if d["hold"] else 0.0
        v, why = _verdict_live(n, pf, d["net"], wr, min_trades)
        rows.append({
            "name": strat, "verdict": v, "why": why,
            "executed": n, "pf": round(pf, 2), "exp": round(avg, 2),
            "wr": round(wr, 1), "net": round(d["net"], 2),
            "hold_min": round(hold, 1), "blocker": "",
        })

    if not rows:
        return {"error": "nessun trade sincronizzato da analizzare"}

    rows.sort(key=lambda x: (VERDICT_RANK.get(x["verdict"], 9), -x["pf"]))
    counts = {}
    for x in rows:
        counts[x["verdict"]] = counts.get(x["verdict"], 0) + 1
    return {
        "rows": rows,
        "summary": {"total": len(rows), "counts": counts, "min_trades": min_trades,
                    "trades": sum(x["executed"] for x in rows)},
        "recommendations": {
            "keep": [x["name"] for x in rows if x["verdict"] in ("FORTE", "OK")],
            "disable": [x["name"] for x in rows if x["verdict"] == "CRITICA"],
            "too_fast": [x["name"] for x in rows
                         if x["executed"] >= min_trades and 0 < x["hold_min"] < 5],
            "blocked": [],
        },
    }


def analyze_stats_csv(text: str, min_trades: int = MIN_TRADES_DEFAULT) -> dict:
    """Ritorna {rows:[...], summary:{...}, recommendations:{...}} dal CSV."""
    if not text or not text.strip():
        return {"error": "CSV vuoto"}

    sample = text[:2048]
    delim = ";" if sample.count(";") >= sample.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)

    rows = []
    for r in reader:
        name = (r.get("name") or r.get("strategy") or "").strip()
        if not name:
            continue
        v, why = _verdict(r, min_trades)
        rows.append({
            "name": name,
            "verdict": v,
            "why": why,
            "executed": _i(r, "executed") or _i(r, "trades"),
            "pf": round(_f(r, "profit_factor"), 2),
            "exp": round(_f(r, "expectancy_R"), 2),
            "wr": round(_f(r, "winrate_pct") or _f(r, "win_rate"), 1),
            "net": round(_f(r, "net_profit"), 2),
            "hold_min": round((_f(r, "avg_holding_sec") or 0) / 60.0, 1),
            "blocker": _blocker_name(r.get("dominant_blocker", "")),
        })

    if not rows:
        return {"error": "nessuna riga strategia riconosciuta nel CSV"}

    rows.sort(key=lambda x: (VERDICT_RANK.get(x["verdict"], 9), -x["pf"]))

    counts = {}
    for x in rows:
        counts[x["verdict"]] = counts.get(x["verdict"], 0) + 1

    forte = [x["name"] for x in rows if x["verdict"] == "FORTE"]
    ok = [x["name"] for x in rows if x["verdict"] == "OK"]
    critica = [x["name"] for x in rows if x["verdict"] == "CRITICA"]
    fast = [x["name"] for x in rows
            if x["executed"] >= min_trades and 0 < x["hold_min"] < 5]
    blocked = [{"name": x["name"], "blocker": x["blocker"]}
               for x in rows if x["verdict"] == "BLOCCATA"]

    return {
        "rows": rows,
        "summary": {"total": len(rows), "counts": counts, "min_trades": min_trades},
        "recommendations": {
            "keep": forte + ok,
            "disable": critica,
            "too_fast": fast,
            "blocked": blocked[:15],
        },
    }
