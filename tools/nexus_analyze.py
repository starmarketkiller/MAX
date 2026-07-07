#!/usr/bin/env python3
"""
nexus_analyze.py - Analizzatore dei risultati backtest NEXUS.

Digerisce i CSV per-strategia emessi dall'EA (OnTester logger, formato ';':
name;enabled;called;setup;...;winrate_pct;expectancy_R;profit_factor;...;
dominant_blocker;reachability_pct;exec_rate_pct;health) e produce una tabella
ordinata con VERDETTO e raccomandazioni concrete (cosa spegnere, cosa rivedere,
perche' una strategia non apre).

Uso:
    python3 tools/nexus_analyze.py results/reports/ALL_ON_..._stats.csv
    python3 tools/nexus_analyze.py results/reports/            # tutti gli *_stats.csv
    python3 tools/nexus_analyze.py <file> --min-trades 15

Nessuna dipendenza esterna: solo stdlib.
"""
import csv
import sys
import os
import glob
from datetime import datetime, timezone

MIN_TRADES_DEFAULT = 10   # sotto questo campione = dati insufficienti

# Mappa il codice numerico del dominant_blocker (enum ENUM_NXS_BLOCK) al nome.
BLOCKERS = ["NONE", "NO_SIGNAL", "COOLDOWN", "MTF", "HTF", "VELOCITY", "NEWS",
            "SPREAD", "PROTECTIONS", "SCORE_BELOW", "PREFLIGHT", "LICENSE",
            "PAUSED", "SEND_FAILED"]


def blocker_name(v):
    s = str(v).strip()
    if s.isdigit() and int(s) < len(BLOCKERS):
        return BLOCKERS[int(s)]
    return s or "?"


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


def verdict(row, min_trades):
    """Assegna un verdetto onesto in base a numeri REALI, non a intuito."""
    executed = _i(row, "executed")
    setup = _i(row, "setup")
    pf = _f(row, "profit_factor")
    exp = _f(row, "expectancy_R")
    wr = _f(row, "winrate_pct")

    # Non ha mai aperto: distingui "non forma il setup" da "bloccato da un gate".
    if executed < min_trades:
        if setup == 0:
            return ("NO_SETUP", "il pattern non si forma (raro/assente su questo simbolo)")
        if setup > 0 and executed <= 1:
            blk = blocker_name(row.get("dominant_blocker", "?"))
            return ("BLOCCATA", f"forma il setup ma non apre (blocco: {blk})")
        return ("POCHI_DATI", f"solo {executed} trade: campione troppo piccolo per giudicare")

    # Campione sufficiente: giudica sull'edge.
    if pf >= 1.5 and exp > 0:
        return ("FORTE", f"PF {pf:.2f}, expectancy {exp:+.2f}R, WR {wr:.0f}%")
    if pf >= 1.15 and exp > 0:
        return ("OK", f"PF {pf:.2f}, expectancy {exp:+.2f}R")
    if pf >= 0.95:
        return ("DEBOLE", f"PF {pf:.2f}: intorno al break-even, nessun edge chiaro")
    return ("CRITICA", f"PF {pf:.2f}, expectancy {exp:+.2f}R: perde soldi, spegnere live")


VERDICT_RANK = {"FORTE": 0, "OK": 1, "DEBOLE": 2, "CRITICA": 3,
                "BLOCCATA": 4, "POCHI_DATI": 5, "NO_SETUP": 6}


def load(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        # sniff separatore (l'EA usa ';', alcuni export ',')
        sample = fh.read(2048)
        fh.seek(0)
        delim = ";" if sample.count(";") >= sample.count(",") else ","
        return list(csv.DictReader(fh, delimiter=delim))


def analyze_file(path, min_trades):
    rows = load(path)
    if not rows:
        print(f"  (vuoto: {path})")
        return

    results = []
    for r in rows:
        name = r.get("name") or r.get("strategy") or "?"
        v, why = verdict(r, min_trades)
        results.append({
            "name": name,
            "verdict": v, "why": why,
            "executed": _i(r, "executed") or _i(r, "trades"),
            "pf": _f(r, "profit_factor"),
            "exp": _f(r, "expectancy_R"),
            "wr": _f(r, "winrate_pct") or _f(r, "win_rate"),
            "hold_s": _f(r, "avg_holding_sec"),
            "blocker": blocker_name(r.get("dominant_blocker", "")),
        })

    results.sort(key=lambda x: (VERDICT_RANK.get(x["verdict"], 9), -x["pf"]))

    print(f"\n=== {os.path.basename(path)} ===")
    print(f"{'STRATEGIA':<22}{'VERDETTO':<12}{'N':>5}{'PF':>7}{'EXP.R':>8}{'WR%':>6}  note")
    print("-" * 100)
    for x in results:
        hold = f"  hold={x['hold_s']/60:.0f}m" if x["hold_s"] > 0 else ""
        print(f"{x['name']:<22}{x['verdict']:<12}{x['executed']:>5}"
              f"{x['pf']:>7.2f}{x['exp']:>8.2f}{x['wr']:>6.0f}  {x['why']}{hold}")

    # Raccomandazioni concrete
    crit = [x["name"] for x in results if x["verdict"] == "CRITICA"]
    forte = [x["name"] for x in results if x["verdict"] == "FORTE"]
    blocked = [(x["name"], x["blocker"]) for x in results if x["verdict"] == "BLOCCATA"]
    fast = [x["name"] for x in results
            if x["executed"] >= min_trades and 0 < x["hold_s"] < 300]

    print("\n  RACCOMANDAZIONI:")
    if crit:
        print(f"   • SPEGNI live (perdono): {', '.join(crit)}")
    if forte:
        print(f"   • TIENI/rafforza (edge reale): {', '.join(forte)}")
    if fast:
        print(f"   • CHIUSURE TROPPO VELOCI (<5min) - alza MinHold/runner: {', '.join(fast)}")
    if blocked:
        print("   • FORMANO setup ma NON aprono (sblocca il gate):")
        for nm, blk in blocked[:10]:
            print(f"       - {nm}: {blk}")
    if not (crit or forte or blocked or fast):
        print("   • nessun segnale forte in un senso o nell'altro: campione ancora piccolo.")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    min_trades = MIN_TRADES_DEFAULT
    if "--min-trades" in sys.argv:
        min_trades = int(sys.argv[sys.argv.index("--min-trades") + 1])

    if not args:
        print(__doc__)
        return
    target = args[0]

    paths = []
    if os.path.isdir(target):
        paths = sorted(glob.glob(os.path.join(target, "*_stats.csv")))
    else:
        paths = [target]

    if not paths:
        print(f"Nessun CSV trovato in {target}")
        return

    print(f"NEXUS analyze - {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC} "
          f"- min_trades={min_trades} - {len(paths)} file")
    for p in paths:
        analyze_file(p, min_trades)


if __name__ == "__main__":
    main()
