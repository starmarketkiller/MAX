"""CHART-REAL-DATA-V1 - archivio di barre aggregate, a segmenti mensili binari, con completezza esplicita.

Perche' esiste: il Chart deve mostrare dati REALI e verificabili senza caricare interi dataset in RAM (Render: 512 MiB). Lo store e' prodotto lato PC (o da un'esportazione
autorizzata) e contiene solo barre aggregate; i tick non entrano mai nello store. Il lettore apre soltanto i segmenti che servono alla richiesta (limite di barre per risposta) e
verifica lo sha256 di ogni segmento prima di servirlo.

Completezza di una barra (calcolata alla costruzione, mai dedotta in lettura):
  COMPLETE  tutti i minuti attesi presenti (con un calendario VERIFICATO i minuti di chiusura non sono attesi)
  PARTIAL   mancano solo minuti spiegati da un calendario candidato NON verificato, oppure la barra esce dalla copertura del dataset (bordo)
  GAP       mancano minuti non spiegati da alcuna chiusura nota/ricorrente: buco reale del dato
  (OPEN e' deciso in lettura: barra non ancora chiusa di un dataset `live`; UNAVAILABLE e' lo stato della risposta quando non ci sono dati)
Il calendario del broker NON e' dedotto come verita': dai dati si ricava solo un calendario CANDIDATO (chiusure ricorrenti), dichiarato `UNVERIFIED`.
"""
from __future__ import annotations

import bisect
import datetime as _dt
import hashlib
import json
import os
import struct
from pathlib import Path

SCHEMA = "NEXUS_CHART_STORE_V1"
BUILDER_VERSION = "chart_store.v1"
TF_SECONDS = {"M1": 60, "M5": 300, "M15": 900, "M30": 1800, "H1": 3600, "H4": 14400, "D1": 86400}
CALENDAR_TFS = ("W1", "MN1")
ALL_TFS = ("M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1")
REC = struct.Struct("<qiiiiHHBB")          # t, o, h, l, c (int32 scalati), minuti presenti, minuti mancanti, completezza, motivi
COMPLETE, PARTIAL, GAP, OPEN = 0, 1, 2, 3
COMP_NAME = {COMPLETE: "COMPLETE", PARTIAL: "PARTIAL", GAP: "GAP", OPEN: "OPEN"}
R_EDGE, R_CAL_VERIFIED, R_CAL_CANDIDATE, R_UNEXPLAINED = 1, 2, 4, 8
MAX_LIMIT = 5000


class StoreError(Exception):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(code + (": " + detail if detail else ""))
        self.code, self.detail = code, detail


def bucket(t: int, tf: str) -> tuple[int, int]:
    if tf in TF_SECONDS:
        s = t // TF_SECONDS[tf] * TF_SECONDS[tf]
        return s, s + TF_SECONDS[tf]
    d = _dt.datetime.fromtimestamp(t, _dt.timezone.utc)
    if tf == "W1":
        s = d.replace(hour=0, minute=0, second=0, microsecond=0) - _dt.timedelta(days=d.weekday())
        return int(s.timestamp()), int((s + _dt.timedelta(days=7)).timestamp())
    if tf == "MN1":
        s = d.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        e = s.replace(year=s.year + (s.month == 12), month=s.month % 12 + 1)
        return int(s.timestamp()), int(e.timestamp())
    raise StoreError("TIMEFRAME_UNSUPPORTED", tf)


def month_key(t: int) -> str:
    return _dt.datetime.fromtimestamp(t, _dt.timezone.utc).strftime("%Y-%m")


def validate_m1(rows: list[dict]) -> None:
    prev = None
    for r in rows:
        t = r["time"]
        if t % 60:
            raise StoreError("M1_NOT_ALIGNED", str(t))
        if prev is not None and t <= prev:
            raise StoreError("M1_DUPLICATE_OR_UNORDERED", str(t))
        o, h, l, c = r["open"], r["high"], r["low"], r["close"]
        if not (0 < l <= min(o, c) <= max(o, c) <= h):
            raise StoreError("M1_OHLC_INCOHERENT", str(t))
        prev = t


# ---------------------------------------------------------------- calendario
def _rule_hit(rule: dict, m: int) -> bool:
    """Il minuto `m` (epoca s) cade in una chiusura della regola {dow|None, start_min, duration_min}? Le chiusure possono scavalcare la mezzanotte."""
    dur = rule["duration_min"] * 60
    day0 = m // 86400 * 86400
    for k in range(0, dur // 86400 + 2):
        day = day0 - k * 86400
        if rule.get("dow") is not None and _dt.datetime.fromtimestamp(day, _dt.timezone.utc).weekday() != rule["dow"]:
            continue
        start = day + rule["start_min"] * 60
        if start <= m < start + dur:
            return True
    return False


def infer_candidate_calendar(rows: list[dict], min_len: int = 10, min_repeat: int = 2) -> dict:
    """Calendario CANDIDATO dalle interruzioni ricorrenti dello stesso minuto-del-giorno (e giorno della settimana se settimanali). NON e' verita': status=UNVERIFIED."""
    import collections
    occ = collections.defaultdict(list)          # (minuto del giorno, durata) -> giorni della settimana in cui si presenta
    for a, b in zip(rows, rows[1:]):
        miss = (b["time"] - a["time"]) // 60 - 1
        if miss >= min_len:
            st = a["time"] + 60
            occ[(st % 86400 // 60, miss)].append(_dt.datetime.fromtimestamp(st, _dt.timezone.utc).weekday())
    rules = []
    for (sm, du), dows in sorted(occ.items()):
        if len(dows) < min_repeat:
            continue                              # chiusura isolata: NON e' un calendario, resta un buco (GAP)
        if len(set(dows)) >= 3:
            rules.append({"dow": None, "start_min": sm, "duration_min": du})
        else:
            rules += [{"dow": d, "start_min": sm, "duration_min": du} for d in sorted(set(dows))]
    return {"status": "UNVERIFIED", "basis": "INFERRED_FROM_DATA_RECURRENCE", "rules": rules}


# ---------------------------------------------------------------- costruzione
def _classify(present: int, total: int, edge: int, expl_n: int, unexpl_n: int, verified: bool) -> tuple[int, int]:
    reason = R_EDGE if edge else 0
    if unexpl_n:
        return GAP, reason | R_UNEXPLAINED
    if edge:
        return PARTIAL, reason | (R_CAL_VERIFIED if (verified and expl_n) else (R_CAL_CANDIDATE if expl_n else 0))
    if expl_n:
        return (COMPLETE, R_CAL_VERIFIED) if verified else (PARTIAL, R_CAL_CANDIDATE)
    return COMPLETE, 0


def aggregate_all(rows: list[dict], calendar: dict, scale: int) -> dict[str, list[tuple]]:
    """M1 -> tutti i timeframe. Ritorna {tf: [(t,o,h,l,c,present,missing,comp,reason)]} con prezzi scalati a int."""
    validate_m1(rows)
    if not rows:
        return {tf: [] for tf in ALL_TFS}
    cov0, cov1 = rows[0]["time"], rows[-1]["time"] + 60
    verified = calendar.get("status") == "VERIFIED"
    rules = calendar.get("rules", [])
    miss_expl, miss_unexpl = [], []
    for a, b in zip(rows, rows[1:]):
        gap = (b["time"] - a["time"]) // 60 - 1
        for k in range(1, gap + 1):
            m = a["time"] + 60 * k
            (miss_expl if any(_rule_hit(r, m) for r in rules) else miss_unexpl).append(m)
    out = {}
    sc = lambda x: int(round(x * scale))
    for tf in ALL_TFS:
        groups: dict[int, list] = {}
        ends = {}
        for r in rows:
            s, e = bucket(r["time"], tf)
            groups.setdefault(s, []).append(r)
            ends[s] = e
        bars = []
        for s in sorted(groups):
            rs, e = groups[s], ends[s]
            total = (e - s) // 60
            lo, hi = max(s, cov0), min(e, cov1)
            edge = total - (hi - lo) // 60 if hi > lo else total
            n_expl = bisect.bisect_left(miss_expl, e) - bisect.bisect_left(miss_expl, s)
            n_unexpl = bisect.bisect_left(miss_unexpl, e) - bisect.bisect_left(miss_unexpl, s)
            comp, reason = _classify(len(rs), total, edge, n_expl, n_unexpl, verified)
            bars.append((s, sc(rs[0]["open"]), sc(max(r["high"] for r in rs)), sc(min(r["low"] for r in rs)), sc(rs[-1]["close"]), len(rs), n_expl + n_unexpl, comp, reason))
        out[tf] = bars
    return out


def build_store(rows: list[dict], out_dir: str | Path, meta: dict, calendar: dict | None = None, scale: int = 1000) -> dict:
    """Costruisce lo store in `out_dir/<dataset_id>/`. `meta` fornisce dataset_id, feed_kind, symbol_actual, aliases, provenance, source_sha256, instrument_spec, authorization, clock_basis."""
    cal = calendar if calendar is not None else infer_candidate_calendar(rows)
    series = aggregate_all(rows, cal, scale)
    root = Path(out_dir) / meta["dataset_id"]
    root.mkdir(parents=True, exist_ok=True)
    segments = {}
    for tf, bars in series.items():
        by_month: dict[str, list] = {}
        for b in bars:
            by_month.setdefault(month_key(b[0]), []).append(b)
        segments[tf] = []
        for mk, bs in sorted(by_month.items()):
            d = root / tf
            d.mkdir(exist_ok=True)
            blob = b"".join(REC.pack(*x) for x in bs)
            (d / (mk + ".bin")).write_bytes(blob)
            segments[tf].append({"month": mk, "first_t": bs[0][0], "last_t": bs[-1][0], "n": len(bs), "bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest()})
    counts = {tf: {COMP_NAME[c]: sum(1 for b in bars if b[7] == c) for c in (COMPLETE, PARTIAL, GAP)} for tf, bars in series.items()}
    manifest = {"schema": SCHEMA, "builder": BUILDER_VERSION, "price_scale": scale, "record": "<qiiiiHHBB", "tf_available": [tf for tf in ALL_TFS if series[tf]], "segments": segments,
                "coverage": {"first_t": rows[0]["time"], "last_end_t": rows[-1]["time"] + 60}, "n_m1": len(rows), "calendar": cal, "completeness_counts": counts, "live": False,
                "built_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"), **meta}
    (root / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True), encoding="utf-8")
    return manifest


# ---------------------------------------------------------------- lettura
class ChartStore:
    """Lettore a finestra. Non carica mai piu' di un segmento alla volta; verifica sha256 per segmento."""

    def __init__(self, root: str | Path):
        self.root = Path(root)

    def datasets(self) -> list[str]:
        try:
            return sorted(p.name for p in self.root.iterdir() if (p / "manifest.json").is_file())
        except OSError:
            return []

    def manifest(self, dataset_id: str) -> dict:
        if not dataset_id or "/" in dataset_id or "\\" in dataset_id or ".." in dataset_id:
            raise StoreError("DATASET_ID_INVALID")
        p = self.root / dataset_id / "manifest.json"
        try:
            m = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise StoreError("STORE_UNREACHABLE", dataset_id)
        if m.get("schema") != SCHEMA or m.get("dataset_id") != dataset_id:
            raise StoreError("MANIFEST_INVALID", dataset_id)
        return m

    def _segment(self, m: dict, tf: str, seg: dict) -> bytes:
        p = self.root / m["dataset_id"] / tf / (seg["month"] + ".bin")
        try:
            blob = p.read_bytes()
        except OSError:
            raise StoreError("STORE_UNREACHABLE", "%s/%s" % (tf, seg["month"]))
        if len(blob) != seg["bytes"] or hashlib.sha256(blob).hexdigest() != seg["sha256"]:
            raise StoreError("SEGMENT_HASH_MISMATCH", "%s/%s" % (tf, seg["month"]))
        return blob

    def read(self, dataset_id: str, tf: str, limit: int, before: int | None = None, guard=None, now: int | None = None) -> dict:
        """Ultime `limit` barre con t < before (o le piu' recenti). `guard.check(dataset_id, t0, t1)` e' invocato PRIMA di aprire ogni segmento."""
        if tf not in ALL_TFS:
            raise StoreError("TIMEFRAME_UNSUPPORTED", tf)
        if not isinstance(limit, int) or not 1 <= limit <= MAX_LIMIT:
            raise StoreError("LIMIT_INVALID", "1..%d" % MAX_LIMIT)
        m = self.manifest(dataset_id)
        segs = m["segments"].get(tf) or []
        if not segs:
            raise StoreError("TIMEFRAME_NOT_AVAILABLE", tf)
        scale = m["price_scale"]
        cov0, cov1 = m["coverage"]["first_t"], m["coverage"]["last_end_t"]
        got: list[tuple] = []
        checked: list[tuple[int, int]] = []
        more = False
        for seg in reversed(segs):
            if before is not None and seg["first_t"] >= before:
                continue
            if guard is not None:
                # intervallo di DATI coperto dal segmento: le barre ai bordi (es. W1/MN1 parziali) iniziano prima della copertura ma non contengono dati fuori da essa
                lo = max(seg["first_t"], cov0)
                hi = min(bucket(seg["last_t"], tf)[1], cov1)
                guard.check(dataset_id, lo, max(hi, lo + 1))
                checked.append((lo, max(hi, lo + 1)))
            blob = self._segment(m, tf, seg)
            recs = [REC.unpack_from(blob, i * REC.size) for i in range(len(blob) // REC.size)]
            if before is not None:
                recs = [r for r in recs if r[0] < before]
            need = limit - len(got)
            if len(recs) > need:
                got = recs[-need:] + got
                more = True
                break
            got = recs + got
        else:
            more = False
        if guard is not None and checked:
            guard.recheck(dataset_id, checked)               # revoca/modifica avvenuta DURANTE la lettura: nessun dato restituito (FIX-01)
        if not more and got:
            earlier = [s for s in segs if s["first_t"] < got[0][0]]
            more = bool(earlier)
        live = bool(m.get("live"))
        bars = []
        for t, o, h, l, c, present, missing, comp, reason in got:
            end = bucket(t, tf)[1]
            is_open = live and now is not None and end > now
            bars.append({"time": t, "open": o / scale, "high": h / scale, "low": l / scale, "close": c / scale, "completeness": "OPEN" if is_open else COMP_NAME[comp],
                         "minutes_present": present, "minutes_missing": missing, "reason": [n for b, n in ((R_EDGE, "COVERAGE_EDGE"), (R_CAL_VERIFIED, "CALENDAR_VERIFIED_CLOSURE"), (R_CAL_CANDIDATE, "CANDIDATE_CALENDAR_UNVERIFIED"), (R_UNEXPLAINED, "UNEXPLAINED_MISSING_MINUTES")) if reason & b]})
        return {"manifest": m, "bars": bars, "has_more": more, "next_before": bars[0]["time"] if bars and more else None}
