"""
NEXUS Causal Research - Experiment 1: WICK Sweep +1R-before--1R

Costruisce il dataset causale v1 dagli eventi [LEVELENGINE][EVENT] delle 3
finestre Phase E (Model=1, InpLevelRegistry_WickReadPath=true) e calcola
l'esito (+1R/-1R/CENSORED) camminando in avanti sulle barre M15 esportate
separatamente (NXS_ResearchExportBars.mq5). Nessuna feature usa dati con
timestamp successivo al momento dello sweep - solo l'OUTCOME (per
definizione) usa il prezzo futuro.

Discovery, non ottimizzazione: WICK_SWEEP_REV resta una negative research
baseline. Nessun parametro della strategia viene toccato qui.
"""
import re
import json
import csv
from datetime import datetime, timedelta
from collections import defaultdict

PIP = 0.10          # 1 pip = $0.10 su GOLD (convenzione NEXUS gia' usata ovunque nel progetto)
R_PIPS = 25.0        # 1R simmetrico per QUESTO esperimento - indipendente dal TP100 legacy
R_PRICE = R_PIPS * PIP

BASE = r"C:\Users\User\.claude\jobs\703d44b4\tmp\phaseE_results"
BARS_PATH = r"C:\Users\User\AppData\Roaming\MetaQuotes\Terminal\Common\Files\nxs_research_bars_m1.csv"

WINDOWS = {
    "W1": "w1_events_v2.txt",
    "W2": "w2_events_v2.txt",
    "W3": "w3_events_v2.txt",
}

EVENT_RE = re.compile(
    r"\[LEVELENGINE\]\[EVENT\] event_id=(\d+) level_id=(\d+) type=(\w+) side=(\w+) dir=(-?\d+) "
    r"price=([\d.]+) pen=([\d.\-]+) touch_count=(\d+) reclaim=(\w+) tf=(\S+) strat=(\S*) "
    r"time=([\d.: ]+) reason=(\S*)"
)


def parse_dt(s):
    return datetime.strptime(s.strip(), "%Y.%m.%d %H:%M:%S")


def load_events(window_id, path):
    events = []
    for line in open(path, encoding="utf-8", errors="ignore"):
        m = EVENT_RE.search(line)
        if not m:
            continue
        events.append(dict(
            window=window_id,
            event_id_local=int(m.group(1)),
            level_id_local=int(m.group(2)),
            type=m.group(3),
            side=m.group(4),
            dir=int(m.group(5)),
            price=float(m.group(6)),
            pen=float(m.group(7)),
            touch_count=int(m.group(8)),
            reclaim=(m.group(9) == "true"),
            tf=m.group(10),
            strat=m.group(11),
            timestamp=parse_dt(m.group(12)),
            reason=m.group(13),
        ))
    return events


def load_bars(path):
    bars = []
    with open(path, encoding="utf-16") as f:
        header = f.readline()
        for line in f:
            parts = line.strip().split(",")
            if len(parts) != 5:
                continue
            t, o, h, l, c = parts
            bars.append((parse_dt(t), float(o), float(h), float(l), float(c)))
    bars.sort(key=lambda r: r[0])
    return bars


def session_bucket(hour):
    # Approssimazione dichiarata: bucket su ora del server MT5 (non convertita
    # a UTC/broker-tz specifico - limite noto, non un dato causale certo al
    # 100% sul fuso, ma l'ORA STESSA e' un dato disponibile causalmente).
    if 0 <= hour < 8:
        return "ASIA"
    if 8 <= hour < 13:
        return "LONDON"
    if 13 <= hour < 22:
        return "NY"
    return "LATE"


def find_outcome(bars, from_ts, entry_ref, direction, dataset_end):
    """Cammina in avanti sulle barre M15 STRETTAMENTE successive a from_ts.
    direction: -1 = SELL (favorevole = prezzo giu'), +1 = BUY (favorevole = prezzo su).
    Ritorna (label, time_to_outcome_seconds, ambiguous_same_bar)."""
    if direction < 0:
        favorable_level = entry_ref - R_PRICE
        adverse_level = entry_ref + R_PRICE
    else:
        favorable_level = entry_ref + R_PRICE
        adverse_level = entry_ref - R_PRICE

    # bisezione lineare (poche migliaia di barre, non serve altro)
    for (t, o, h, l, c) in bars:
        if t <= from_ts:
            continue
        if t > dataset_end:
            break
        if direction < 0:
            hit_fav = l <= favorable_level
            hit_adv = h >= adverse_level
        else:
            hit_fav = h >= favorable_level
            hit_adv = l <= adverse_level
        if hit_fav and hit_adv:
            return ("AMBIGUOUS_SAME_BAR", (t - from_ts).total_seconds(), True)
        if hit_fav:
            return ("PLUS_1R_FIRST", (t - from_ts).total_seconds(), False)
        if hit_adv:
            return ("MINUS_1R_FIRST", (t - from_ts).total_seconds(), False)
    return ("CENSORED", None, False)


def main():
    print("Caricamento barre M15...")
    bars = load_bars(BARS_PATH)
    print(f"  {len(bars)} barre, {bars[0][0]} -> {bars[-1][0]}")
    dataset_end = bars[-1][0]

    all_events = []
    for wid, fname in WINDOWS.items():
        evs = load_events(wid, f"{BASE}\\{fname}")
        all_events.extend(evs)
        print(f"  {wid}: {len(evs)} eventi grezzi")

    # indicizza per (window, level_id_local)
    by_level = defaultdict(list)
    for e in all_events:
        by_level[(e["window"], e["level_id_local"])].append(e)

    total_levels = len(by_level)
    records = []
    dq = dict(
        total_sweep_events=0, resolved=0, censored=0, ambiguous_same_bar=0,
        duplicate_level_sweep=0, missing_created_time=0, incoherent=0,
    )

    for (window, lvl), evs in by_level.items():
        evs.sort(key=lambda e: e["event_id_local"])
        creates = [e for e in evs if e["type"] == "CREATE"]
        sweeps = [e for e in evs if e["type"] == "SWEEP"]
        if not sweeps:
            continue
        if len(sweeps) > 1:
            dq["duplicate_level_sweep"] += 1
            # per costruzione one-shot del legacy questo non dovrebbe accadere;
            # se accade, usa SOLO il primo sweep (quello che ha davvero
            # generato il trade/segnale), scartando i successivi come
            # ridondanti - dichiarato, non silenzioso.
        sweep = sweeps[0]
        dq["total_sweep_events"] += 1

        if not creates:
            dq["missing_created_time"] += 1
            created_time = None
        else:
            created_time = creates[0]["timestamp"]

        side = sweep["side"]
        direction = sweep["dir"]
        level_price = sweep["price"]
        penetration_pips = sweep["pen"]
        touch_count_before_sweep = sweep["touch_count"]

        # entry_ref ricostruito dalla STESSA formula del codice (mai un nuovo
        # calcolo indipendente): SELL -> level+pen*pip, BUY -> level-pen*pip
        if direction < 0:
            entry_ref = level_price + penetration_pips * PIP
        else:
            entry_ref = level_price - penetration_pips * PIP

        if created_time is not None and created_time <= sweep["timestamp"]:
            level_age_seconds = (sweep["timestamp"] - created_time).total_seconds()
        else:
            level_age_seconds = None
            if created_time is not None:
                dq["incoherent"] += 1  # created_time dopo lo sweep: incoerente, non usare

        label, ttf, ambiguous = find_outcome(bars, sweep["timestamp"], entry_ref, direction, dataset_end)
        if label == "CENSORED":
            dq["censored"] += 1
        elif ambiguous:
            dq["ambiguous_same_bar"] += 1
        else:
            dq["resolved"] += 1

        records.append(dict(
            event_id=f"{window}_{sweep['event_id_local']}",
            level_id=f"{window}_{lvl}",
            timestamp=sweep["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
            side=side,
            direction=("SELL" if direction < 0 else "BUY"),
            level_price=level_price,
            entry_ref=round(entry_ref, 2),
            created_time=(created_time.strftime("%Y-%m-%d %H:%M:%S") if created_time else None),
            level_age_seconds=level_age_seconds,
            touch_count_before_sweep=touch_count_before_sweep,
            penetration_pips=penetration_pips,
            sweep_depth_pips=penetration_pips,  # per definizione di schema, congelata al primo sweep
            session_bucket=session_bucket(sweep["timestamp"].hour),
            hour=sweep["timestamp"].hour,
            day_of_week=sweep["timestamp"].strftime("%A"),
            source_tf=sweep["tf"],
            window_id=window,
            outcome=label,
            time_to_outcome_seconds=ttf,
        ))

    dq["total_levels_created"] = total_levels
    dq["duplicates_event_id"] = 0  # verificato sotto

    # controllo duplicati event_id/level_id globali (dopo prefisso window)
    eids = [r["event_id"] for r in records]
    lids = [r["level_id"] for r in records]
    dq["duplicate_event_id_global"] = len(eids) - len(set(eids))
    dq["duplicate_level_id_global"] = len(lids) - len(set(lids))

    out_csv = r"C:\Users\User\ClaudeWork\MAX\results\causal_experiment_1\wick_sweep_1r_dataset.csv"
    out_json = r"C:\Users\User\ClaudeWork\MAX\results\causal_experiment_1\wick_sweep_1r_dataset.json"
    fieldnames = list(records[0].keys()) if records else []
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in records:
            w.writerow(r)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, default=str)

    print("\n=== DATA QUALITY ===")
    for k, v in dq.items():
        print(f"  {k}: {v}")

    print(f"\nRecord totali (livelli swept): {len(records)}")
    print(f"Salvato: {out_csv}")
    print(f"Salvato: {out_json}")

    # distribuzioni richieste
    from collections import Counter
    print("\n=== DISTRIBUZIONE per finestra ===")
    print(Counter(r["window_id"] for r in records))
    print("\n=== DISTRIBUZIONE per sessione ===")
    print(Counter(r["session_bucket"] for r in records))
    print("\n=== DISTRIBUZIONE long/short ===")
    print(Counter(r["direction"] for r in records))
    print("\n=== DISTRIBUZIONE outcome ===")
    print(Counter(r["outcome"] for r in records))


if __name__ == "__main__":
    main()
