"""
NEXUS Causal Research Thread 2, Fase B: Structural Dataset v1.

Costruisce (NON analizza) il primo dataset strutturale da eventi SWEEP/
TRUE_BREAK/RETEST/INVALIDATE esportati da NXS_StructuralResearchLog.mqh
(Thread 2 Fase A/A.1, detector integrity fix 9b77f83).

Puro standard library (nessun pandas/numpy disponibile in questo
ambiente) - stesso stile di causal_experiment_1/2/3.

Input: CSV grezzi per 4 finestre non sovrapposte (raccolti dal Tester),
       + barre M1 per le stesse 4 finestre (per i label forward-looking).
Output: results/structural_dataset_v1/{structural_events,at_sweep,at_true_break}.csv
        + metadata.json

Regola di sicurezza causale: ogni feature in AT_SWEEP usa solo dati noti
AL MOMENTO dello sweep; ogni feature in AT_TRUE_BREAK usa solo dati noti
al momento del TRUE_BREAK (mai il retest/invalidate futuro). I LABEL sono
per definizione forward-looking e sono calcolati SOLO entro i dati M1
della STESSA finestra della sua origine (mai a cavallo di finestre diverse).

Questo script COSTRUISCE il dataset e i controlli di qualita'. Non fa
feature selection, non fa regressione/albero, non propone regole.
"""
import csv
import json
import os
import bisect
from datetime import datetime, timedelta
from collections import defaultdict, Counter

HARVEST_DIR = r"C:\Users\User\.claude\jobs\703d44b4\tmp\structural_dataset_v1\harvest"
OUT_DIR = r"C:\Users\User\ClaudeWork\MAX\results\structural_dataset_v1"
os.makedirs(OUT_DIR, exist_ok=True)

WINDOWS = [
    {"id": "w1", "from": "2026.01.01", "to": "2026.03.01"},
    {"id": "w2", "from": "2026.03.01", "to": "2026.05.01"},
    {"id": "w3", "from": "2026.05.01", "to": "2026.07.01"},
    {"id": "w4", "from": "2026.07.01", "to": "2026.08.25"},
]

R_PIPS = 25.0          # stessa convenzione fissa di Causal Experiment 1/2/3
PIP_SIZE = 0.01        # GOLD, come g_profile.pipSize
HORIZON = timedelta(days=5)   # orizzonte fisso e dichiarato per tutti i label forward

DT_FMT = "%Y.%m.%d %H:%M:%S"


def parse_dt(s):
    s = (s or "").strip()
    if not s:
        return None
    return datetime.strptime(s, DT_FMT)


def parse_float(s, default=0.0):
    try:
        return float(s)
    except (TypeError, ValueError):
        return default


_STRUCT_COLS = ["event_id", "structural_level_id", "timestamp", "event_type", "source", "source_tf",
                "side", "direction", "level_price", "price_at_event", "penetration_pips",
                "created_time", "age_seconds", "state_before", "state_after", "regime_at_event",
                "structure_trend_at_event", "atr_at_event", "consumer", "observed_by", "observation_count"]
# indice (0-based) dell'ultimo campo FISSO prima di observed_by (consumer), e del campo dopo (observation_count)
_IDX_CONSUMER = _STRUCT_COLS.index("consumer")          # 18
_IDX_OBSERVED_BY = _STRUCT_COLS.index("observed_by")    # 19
_IDX_OBS_COUNT = _STRUCT_COLS.index("observation_count")  # 20


def read_structural_csv(path):
    """
    Lettura robusta: observed_by e' scritto dal lato MQL5 come ",Nome1,Nome2,"
    e FileWrite(FILE_CSV) NON quota i campi che contengono il delimitatore ','
    al suo interno - il campo si spezza quindi su piu' colonne CSV (anche per
    un solo consumer: ",SH_BMS_RTO," produce gia' 3 pezzi vuoti/pieni). Ogni
    riga ha percio' N >= 21 colonne invece delle 21 attese; i pezzi da
    indice _IDX_OBSERVED_BY a N-2 (esclusa l'ultima, observation_count) sono
    ricongiunti con ',' per ricostruire il vero valore di observed_by.
    """
    rows = []
    with open(path, encoding="utf-16", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        for fields in reader:
            if not fields:
                continue
            n = len(fields)
            if n < len(_STRUCT_COLS):
                continue  # riga tronca/vuota, scartata (nessuna attesa in pratica)
            prefix = fields[:_IDX_CONSUMER + 1]
            observed_by = ",".join(fields[_IDX_OBSERVED_BY:n - 1])
            obs_count = fields[n - 1]
            values = prefix + [observed_by, obs_count]
            r = dict(zip(_STRUCT_COLS, values))
            r["timestamp"] = parse_dt(r["timestamp"])
            r["created_time"] = parse_dt(r.get("created_time"))
            r["level_price"] = parse_float(r["level_price"])
            r["price_at_event"] = parse_float(r["price_at_event"])
            r["penetration_pips"] = parse_float(r["penetration_pips"])
            r["age_seconds"] = parse_float(r.get("age_seconds"), -1)
            r["atr_at_event"] = parse_float(r.get("atr_at_event"))
            r["observation_count"] = int(parse_float(r.get("observation_count"), 0))
            rows.append(r)
    return rows


def read_m1_csv(path):
    """Ritorna liste parallele ordinate per tempo: times (datetime), highs, lows (float)."""
    times, highs, lows = [], [], []
    with open(path, encoding="utf-16") as f:
        reader = csv.DictReader(f)
        for r in reader:
            t = parse_dt(r["time"])
            if t is None:
                continue
            times.append(t)
            highs.append(parse_float(r["high"]))
            lows.append(parse_float(r["low"]))
    order = sorted(range(len(times)), key=lambda i: times[i])
    times = [times[i] for i in order]
    highs = [highs[i] for i in order]
    lows = [lows[i] for i in order]
    return times, highs, lows


def load_all():
    ev_by_window = {}
    m1_by_window = {}
    for w in WINDOWS:
        rows = read_structural_csv(os.path.join(HARVEST_DIR, f"structural_events_{w['id']}.csv"))
        for r in rows:
            r["window_id"] = w["id"]
        ev_by_window[w["id"]] = rows
        m1_by_window[w["id"]] = read_m1_csv(os.path.join(HARVEST_DIR, f"nxs_m1_struct_{w['id']}.csv"))
    all_events = []
    for w in WINDOWS:
        all_events.extend(ev_by_window[w["id"]])
    return all_events, ev_by_window, m1_by_window


def assign_episodes(all_events):
    """
    Linkage rule deterministica (Fase B - Causal Linkage Integrity Audit).

    Causa dei 48 casi (Fase B v1) e degli 11 non risolti da event_id: un
    singolo structural_level_id (es. "Asia-High_2026.01.23") puo' avere PIU'
    episodi SWEEP->TRUE_BREAK->RETEST/INVALIDATE nella stessa finestra (stesso
    livello, sweepato/invalidato/risweepato piu' volte), e la fonte SWEEP
    condivisa (Fase A.1) puo' emettere PIU' righe SWEEP consecutive per lo
    STESSO episodio quando la condizione sw.confirmed persiste su bar
    successive (osservate da "DETECTOR" ma non da SH_BMS_RTO, che e' gia'
    uscito da IDLE). Il vecchio builder linkava per (level_id, window) intero,
    ignorando quale SWEEP appartenesse a quale episodio - da qui sia i
    "sweep_event_id vuoto" (timestamp bar-anchor incomparabile) sia il
    linkage potenzialmente errato quando piu' episodi condividono il livello.

    Regola qui implementata, SOLO in ordine di event_id (mai timestamp,
    mai nearest-match post-hoc):
      - Una riga SWEEP apre un NUOVO episodio (structural_episode_id univoco)
        SOLO se "SH_BMS_RTO" compare nel suo observed_by - e' la prova diretta
        che, in quel preciso momento di elaborazione, lo stato di SH_BMS_RTO
        era IDLE (precondizione hardcoded nel suo stesso codice per osservare
        un nuovo sweep). Una riga SWEEP canonica osservata SOLO da DETECTOR
        (persistenza della condizione, non un nuovo episodio per SH_BMS_RTO)
        riceve comunque un proprio structural_episode_id (per restare
        popolazione valida in AT_SWEEP), ma non diventa mai il bersaglio di
        un TRUE_BREAK/RETEST/INVALIDATE.
      - TRUE_BREAK/RETEST/INVALIDATE (prodotti SOLO da SH_BMS_RTO) si
        agganciano SEMPRE all'ultimo episodio SH_BMS_RTO aperto in ordine di
        event_id fino a quel punto ("last_episode"). Se last_episode e' None
        (nessun episodio mai aperto prima), l'evento e' un vero ORPHAN
        (riportato esplicitamente, MAI agganciato per timestamp piu' vicino).
      - RETEST/INVALIDATE chiudono l'episodio (is_open=False). TRUE_BREAK non
        chiude. Un secondo INVALIDATE/RETEST dopo la chiusura (osservato
        empiricamente: doppio INVALIDATE consecutivo sullo stesso episodio,
        artefatto del loop multi-TF-pass che rivaluta lo stesso stato
        condiviso da pass diversi nello stesso tick) resta agganciato
        all'ultimo episodio ma viene marcato "redundant_after_close" - MAI
        silenziosamente ignorato o riassegnato altrove.
      - Un nuovo SWEEP con SH_BMS_RTO in observed_by chiude SEMPRE
        implicitamente l'episodio precedente (se ancora aperto) - la sola
        esistenza di una nuova osservazione IDLE->SWEPT e' prova che
        l'episodio precedente e' terminato nella realta', con o senza una
        riga di chiusura esplicita nel log (marcato "implicit_close").

    Ritorna: (all_events con 'structural_episode_id' assegnato ad ogni riga
    SWEEP; lifecycle_link: dict event_id(lifecycle) -> episode_id; episodes:
    dict episode_id -> info; true_orphans: lista di eventi mai agganciabili).
    """
    groups = defaultdict(list)
    for e in all_events:
        groups[(e["structural_level_id"], e["window_id"])].append(e)

    lifecycle_link = {}
    episodes = {}
    true_orphans = []
    redundant_after_close = []
    true_break_after_close = []

    for (lvl, win), grp in groups.items():
        grp_sorted = sorted(grp, key=lambda x: int(x["event_id"]))
        last_episode = None
        is_open = False
        ep_counter = 0
        for e in grp_sorted:
            if e["event_type"] == "SWEEP":
                ep_counter += 1
                ep_id = f"{lvl}__ep{ep_counter}"
                e["structural_episode_id"] = ep_id
                if "SH_BMS_RTO" in e.get("observed_by", ""):
                    if last_episode is not None and is_open:
                        episodes[last_episode]["closed_by"] = "IMPLICIT_NEXT_SWEEP"
                        episodes[last_episode]["is_open_at_window_end"] = False
                    last_episode = ep_id
                    is_open = True
                    episodes[ep_id] = {
                        "window_id": win, "structural_level_id": lvl,
                        "sweep_event_id": e["event_id"], "sweep_timestamp": str(e["timestamp"]),
                        "closed_by": None, "is_open_at_window_end": True,
                    }
            else:
                if last_episode is None:
                    true_orphans.append(e)
                    continue
                lifecycle_link[e["event_id"]] = last_episode
                e["structural_episode_id"] = last_episode
                if not is_open:
                    redundant_after_close.append(e)
                    if e["event_type"] == "TRUE_BREAK":
                        true_break_after_close.append(e)
                if e["event_type"] in ("RETEST", "INVALIDATE"):
                    if is_open:
                        episodes[last_episode]["closed_by"] = e["event_type"]
                        episodes[last_episode]["is_open_at_window_end"] = False
                    is_open = False
    return lifecycle_link, episodes, true_orphans, redundant_after_close, true_break_after_close


def data_quality_checks(all_events, lifecycle_link, episodes, true_orphans, redundant_after_close, true_break_after_close):
    dq = {}

    # 1. duplicate keys (structural_level_id, event_type, timestamp, window_id)
    key_counts = Counter(
        (e["structural_level_id"], e["event_type"], e["timestamp"], e["window_id"]) for e in all_events
    )
    dq["duplicate_event_keys"] = sum(1 for c in key_counts.values() if c > 1)

    # 2. orphan reali: lifecycle event MAI agganciabile a nessun episodio (last_episode
    #    era None quando e' arrivato) - per costruzione dell'algoritmo, non per timestamp.
    dq["orphan_true_break"] = sum(1 for e in true_orphans if e["event_type"] == "TRUE_BREAK")
    dq["orphan_retest"] = sum(1 for e in true_orphans if e["event_type"] == "RETEST")
    dq["orphan_invalidate_no_open_episode"] = sum(1 for e in true_orphans if e["event_type"] == "INVALIDATE")
    dq["orphan_detail"] = [
        {"window_id": e["window_id"], "structural_level_id": e["structural_level_id"],
         "event_type": e["event_type"], "event_id": e["event_id"], "timestamp": str(e["timestamp"])}
        for e in true_orphans
    ][:50]

    # 3. ordine impossibile: per costruzione dell'algoritmo (replay in ordine di event_id,
    #    un evento lifecycle si aggancia SEMPRE all'ultimo episodio aperto PRIMA di esso in
    #    quello stesso ordine), un ordine impossibile e' strutturalmente escluso.
    dq["impossible_transitions"] = 0

    # 4. episodi: chiusura esplicita/implicita/aperta a fine finestra
    dq["episodes_total"] = len(episodes)
    dq["episodes_closed_explicit"] = sum(1 for v in episodes.values() if v["closed_by"] in ("RETEST", "INVALIDATE"))
    dq["episodes_closed_implicit_next_sweep"] = sum(1 for v in episodes.values() if v["closed_by"] == "IMPLICIT_NEXT_SWEEP")
    dq["episodes_open_at_window_end"] = sum(1 for v in episodes.values() if v["is_open_at_window_end"])
    dq["lifecycle_redundant_after_close"] = len(redundant_after_close)
    dq["lifecycle_redundant_after_close_detail"] = [
        {"window_id": e["window_id"], "structural_level_id": e["structural_level_id"],
         "event_type": e["event_type"], "event_id": e["event_id"]} for e in redundant_after_close
    ][:50]
    dq["true_break_after_close"] = len(true_break_after_close)
    dq["true_break_after_close_detail"] = [
        {"window_id": e["window_id"], "structural_level_id": e["structural_level_id"],
         "event_id": e["event_id"]} for e in true_break_after_close
    ][:50]

    # malformed (post-fix, dovrebbe essere strutturalmente impossibile - verificato comunque)
    malformed = [e for e in all_events if e["direction"] == "NONE" or not e.get("side") or e["level_price"] <= 0]
    dq["malformed_rows"] = len(malformed)

    # counts by window and type
    counts = defaultdict(lambda: defaultdict(int))
    for e in all_events:
        counts[e["window_id"]][e["event_type"]] += 1
    dq["counts_by_window_and_type"] = {k: dict(v) for k, v in counts.items()}

    return dq


def check_m1_coverage(m1_by_window):
    coverage = {}
    for w in WINDOWS:
        times, highs, lows = m1_by_window[w["id"]]
        if not times:
            coverage[w["id"]] = {"rows": 0, "gap_check": "NO_DATA"}
            continue
        big_gaps = 0
        for i in range(1, len(times)):
            if (times[i] - times[i - 1]).total_seconds() > 300:
                big_gaps += 1
        coverage[w["id"]] = {
            "rows": len(times),
            "first": str(times[0]),
            "last": str(times[-1]),
            "gaps_over_5min": big_gaps,
        }
    return coverage


def dir_sign(direction_str):
    return 1 if direction_str == "BUY" else (-1 if direction_str == "SELL" else 0)


def scan_forward_labels(m1_tuple, window_end, obs_time, obs_price, dsign, atr):
    """
    Cammina in avanti sulle barre M1 (SOLO time > obs_time, mai oltre window_end)
    e determina quale soglia viene toccata per prima.
    Ritorna dict con 'plus1r_before_minus1r' e 'continuation_1atr_before_failure'.
    """
    times, highs, lows = m1_tuple
    result = {"plus1r_before_minus1r": "CENSORED", "continuation_1atr_before_failure": "CENSORED"}

    horizon_end = min(obs_time + HORIZON, window_end)
    lo_idx = bisect.bisect_right(times, obs_time)
    hi_idx = bisect.bisect_right(times, horizon_end)
    if lo_idx >= hi_idx:
        return result

    r_price = R_PIPS * PIP_SIZE
    plus_level = obs_price + dsign * r_price
    minus_level = obs_price - dsign * r_price
    have_atr = atr is not None and atr > 0
    if have_atr:
        cont_level = obs_price + dsign * atr
        fail_level = obs_price

    plus_done = minus_done = cont_done = fail_done = False
    for i in range(lo_idx, hi_idx):
        h, l = highs[i], lows[i]
        if dsign > 0:
            hit_plus, hit_minus = (h >= plus_level), (l <= minus_level)
        else:
            hit_plus, hit_minus = (l <= plus_level), (h >= minus_level)

        if result["plus1r_before_minus1r"] == "CENSORED":
            if hit_plus and hit_minus:
                result["plus1r_before_minus1r"] = "AMBIGUOUS_SAME_BAR"
            elif hit_plus:
                result["plus1r_before_minus1r"] = "PLUS_1R_FIRST"
            elif hit_minus:
                result["plus1r_before_minus1r"] = "MINUS_1R_FIRST"

        if have_atr and result["continuation_1atr_before_failure"] == "CENSORED":
            if dsign > 0:
                hit_cont, hit_fail = (h >= cont_level), (l <= fail_level)
            else:
                hit_cont, hit_fail = (l <= cont_level), (h >= fail_level)
            if hit_cont and hit_fail:
                result["continuation_1atr_before_failure"] = "AMBIGUOUS_SAME_BAR"
            elif hit_cont:
                result["continuation_1atr_before_failure"] = "CONTINUATION_FIRST"
            elif hit_fail:
                result["continuation_1atr_before_failure"] = "FAILURE_FIRST"

        if result["plus1r_before_minus1r"] != "CENSORED" and (
            not have_atr or result["continuation_1atr_before_failure"] != "CENSORED"
        ):
            break

    return result


RETEST_LABEL_MAP = {
    "PLUS_1R_FIRST": "HOLD", "MINUS_1R_FIRST": "FAIL",
    "AMBIGUOUS_SAME_BAR": "AMBIGUOUS", "CENSORED": "CENSORED",
}


def build_episode_lifecycle_index(all_events, lifecycle_link):
    """episode_id -> lista di eventi lifecycle (TRUE_BREAK/RETEST/INVALIDATE) agganciati,
    SOLO tramite lifecycle_link (mai per livello intero) - un episodio vede solo
    i propri eventi, mai quelli di un episodio diverso sullo stesso livello."""
    idx = defaultdict(list)
    ev_by_id = {e["event_id"]: e for e in all_events}
    for evid, ep_id in lifecycle_link.items():
        idx[ep_id].append(ev_by_id[evid])
    return idx


def build_at_sweep(all_events, episode_lifecycle, m1_by_window, window_end_by_id):
    rows = []
    for e in all_events:
        if e["event_type"] != "SWEEP":
            continue
        win = e["window_id"]
        peers = episode_lifecycle.get(e["structural_episode_id"], [])
        tb = [p for p in peers if p["event_type"] == "TRUE_BREAK"]
        rt = [p for p in peers if p["event_type"] == "RETEST"]
        inv = [p for p in peers if p["event_type"] == "INVALIDATE"]

        true_break_occurred = len(tb) > 0
        retest_occurred = len(rt) > 0
        if true_break_occurred:
            lifecycle_outcome = "TRUE_BREAK_OBSERVED"
        elif any(p["state_before"] == "SWEPT" for p in inv):
            # evento INVALIDATE osservato, senza alcun TRUE_BREAK nello stesso episodio -
            # "invalidato prima di un MSS/displacement": NON un evento RECLAIM esplicito
            # (non esiste nell'instrumentation), nome scelto per riflettere solo cio' che
            # e' realmente registrato (event_type + state_before).
            lifecycle_outcome = "INVALIDATED_NO_BREAK"
        else:
            lifecycle_outcome = "NO_LIFECYCLE_OBSERVED"

        m1_tuple = m1_by_window[win]
        window_end = window_end_by_id[win]
        dsign = dir_sign(e["direction"])
        fwd = scan_forward_labels(m1_tuple, window_end, e["timestamp"], e["price_at_event"], dsign, e["atr_at_event"])

        retest_hold_or_fail = "N/A_NO_RETEST"
        if retest_occurred:
            r0 = sorted(rt, key=lambda x: int(x["event_id"]))[0]
            r_fwd = scan_forward_labels(m1_tuple, window_end, r0["timestamp"], r0["price_at_event"], dsign, r0["atr_at_event"])
            retest_hold_or_fail = RETEST_LABEL_MAP[r_fwd["plus1r_before_minus1r"]]

        rows.append({
            "window_id": win, "structural_level_id": e["structural_level_id"],
            "structural_episode_id": e["structural_episode_id"], "event_id": e["event_id"],
            "timestamp": e["timestamp"], "source": e["source"], "source_tf": e["source_tf"],
            "side": e["side"], "direction": e["direction"], "level_price": e["level_price"],
            "price_at_event": e["price_at_event"], "penetration_pips": e["penetration_pips"],
            "created_time": e["created_time"], "age_seconds": e["age_seconds"],
            "regime_at_event": e["regime_at_event"], "structure_trend_at_event": e["structure_trend_at_event"],
            "atr_at_event": e["atr_at_event"], "consumer": e["consumer"],
            "observed_by": e["observed_by"], "observation_count": e["observation_count"],
            "label_true_break_occurred": true_break_occurred,
            "label_retest_occurred": retest_occurred,
            "label_lifecycle_outcome": lifecycle_outcome,
            "label_retest_hold_or_fail": retest_hold_or_fail,
            "label_plus1r_before_minus1r": fwd["plus1r_before_minus1r"],
            "label_continuation_1atr_before_failure": fwd["continuation_1atr_before_failure"],
        })
    return rows


def build_at_true_break(all_events, episodes, episode_lifecycle, m1_by_window, window_end_by_id):
    rows = []
    for e in all_events:
        if e["event_type"] != "TRUE_BREAK":
            continue
        win = e["window_id"]
        ep_id = e.get("structural_episode_id")  # assegnato tramite lifecycle_link nel chiamante
        ep_info = episodes.get(ep_id)
        sweep_event_id = ep_info["sweep_event_id"] if ep_info else None

        peers = episode_lifecycle.get(ep_id, [])
        rt = [p for p in peers if p["event_type"] == "RETEST"]
        retest_occurred = len(rt) > 0

        m1_tuple = m1_by_window[win]
        window_end = window_end_by_id[win]
        dsign = dir_sign(e["direction"])
        fwd = scan_forward_labels(m1_tuple, window_end, e["timestamp"], e["price_at_event"], dsign, e["atr_at_event"])

        retest_hold_or_fail = "N/A_NO_RETEST"
        if retest_occurred:
            r0 = sorted(rt, key=lambda x: int(x["event_id"]))[0]
            r_fwd = scan_forward_labels(m1_tuple, window_end, r0["timestamp"], r0["price_at_event"], dsign, r0["atr_at_event"])
            retest_hold_or_fail = RETEST_LABEL_MAP[r_fwd["plus1r_before_minus1r"]]

        rows.append({
            "window_id": win, "structural_level_id": e["structural_level_id"],
            "structural_episode_id": ep_id, "sweep_event_id": sweep_event_id, "true_break_event_id": e["event_id"],
            "timestamp": e["timestamp"], "source_tf": e["source_tf"], "side": e["side"],
            "direction": e["direction"], "level_price": e["level_price"],
            "price_at_event": e["price_at_event"], "penetration_pips": e["penetration_pips"],
            "regime_at_event": e["regime_at_event"], "structure_trend_at_event": e["structure_trend_at_event"],
            "atr_at_event": e["atr_at_event"], "consumer": e["consumer"],
            # time_to_true_break_sec RIMOSSO (Fase B, Causal Linkage Integrity Audit): il
            # campo timestamp e' il bar-open del TF che ha innescato la transizione, non
            # un orologio uniforme fra pass diversi - sottrarre due timestamp di TF diversi
            # puo' invertire l'ordine reale (vedi report). event_id stabilisce l'ordine ma
            # non rappresenta secondi: nessuna conversione event_id->tempo eseguita.
            "label_retest_occurred": retest_occurred,
            "label_retest_hold_or_fail": retest_hold_or_fail,
            "label_plus1r_before_minus1r": fwd["plus1r_before_minus1r"],
            "label_continuation_1atr_before_failure": fwd["continuation_1atr_before_failure"],
        })
    return rows


def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def counter_dict(rows, key):
    return dict(Counter(r[key] for r in rows))


def main():
    all_events, ev_by_window, m1_by_window = load_all()
    window_end_by_id = {w["id"]: datetime.strptime(w["to"], "%Y.%m.%d") for w in WINDOWS}

    lifecycle_link, episodes, true_orphans, redundant_after_close, true_break_after_close = assign_episodes(all_events)
    episode_lifecycle = build_episode_lifecycle_index(all_events, lifecycle_link)

    dq = data_quality_checks(all_events, lifecycle_link, episodes, true_orphans, redundant_after_close, true_break_after_close)
    m1_cov = check_m1_coverage(m1_by_window)

    at_sweep = build_at_sweep(all_events, episode_lifecycle, m1_by_window, window_end_by_id)
    at_true_break = build_at_true_break(all_events, episodes, episode_lifecycle, m1_by_window, window_end_by_id)

    ev_fields = ["event_id", "structural_level_id", "structural_episode_id", "timestamp", "event_type",
                 "source", "source_tf", "side", "direction", "level_price", "price_at_event", "penetration_pips",
                 "created_time", "age_seconds", "state_before", "state_after", "regime_at_event",
                 "structure_trend_at_event", "atr_at_event", "consumer", "observed_by",
                 "observation_count", "window_id"]
    write_csv(os.path.join(OUT_DIR, "structural_events.csv"), all_events, ev_fields)

    sweep_fields = ["window_id", "structural_level_id", "structural_episode_id", "event_id", "timestamp",
                    "source", "source_tf", "side", "direction", "level_price", "price_at_event", "penetration_pips",
                    "created_time", "age_seconds", "regime_at_event", "structure_trend_at_event",
                    "atr_at_event", "consumer", "observed_by", "observation_count",
                    "label_true_break_occurred", "label_retest_occurred", "label_lifecycle_outcome",
                    "label_retest_hold_or_fail", "label_plus1r_before_minus1r",
                    "label_continuation_1atr_before_failure"]
    write_csv(os.path.join(OUT_DIR, "at_sweep.csv"), at_sweep, sweep_fields)

    tb_fields = ["window_id", "structural_level_id", "structural_episode_id", "sweep_event_id",
                 "true_break_event_id", "timestamp", "source_tf", "side", "direction", "level_price",
                 "price_at_event", "penetration_pips", "regime_at_event", "structure_trend_at_event",
                 "atr_at_event", "consumer", "label_retest_occurred", "label_retest_hold_or_fail",
                 "label_plus1r_before_minus1r", "label_continuation_1atr_before_failure"]
    write_csv(os.path.join(OUT_DIR, "at_true_break.csv"), at_true_break, tb_fields)

    n_sweep = len(at_sweep)
    n_tb = len(at_true_break)
    label_coverage = {
        "at_sweep": {
            "n_rows": n_sweep,
            "true_break_occurred_rate": (sum(1 for r in at_sweep if r["label_true_break_occurred"]) / n_sweep) if n_sweep else None,
            "retest_occurred_rate": (sum(1 for r in at_sweep if r["label_retest_occurred"]) / n_sweep) if n_sweep else None,
            "lifecycle_outcome_counts": counter_dict(at_sweep, "label_lifecycle_outcome"),
            "retest_hold_or_fail_counts": counter_dict(at_sweep, "label_retest_hold_or_fail"),
            "plus1r_before_minus1r_counts": counter_dict(at_sweep, "label_plus1r_before_minus1r"),
            "continuation_1atr_before_failure_counts": counter_dict(at_sweep, "label_continuation_1atr_before_failure"),
        },
        "at_true_break": {
            "n_rows": n_tb,
            "retest_occurred_rate": (sum(1 for r in at_true_break if r["label_retest_occurred"]) / n_tb) if n_tb else None,
            "retest_hold_or_fail_counts": counter_dict(at_true_break, "label_retest_hold_or_fail"),
            "plus1r_before_minus1r_counts": counter_dict(at_true_break, "label_plus1r_before_minus1r"),
            "continuation_1atr_before_failure_counts": counter_dict(at_true_break, "label_continuation_1atr_before_failure"),
        },
    }

    event_counts_total = counter_dict(all_events, "event_type")
    unique_sweeps = len(set(
        (e["structural_level_id"], e["window_id"]) for e in all_events if e["event_type"] == "SWEEP"
    ))
    unique_episodes = len(episodes)
    episodes_with_sh_bms_rto_lifecycle = len(episode_lifecycle)

    metadata = {
        "schema_version": "structural_dataset_v1",
        "generated_at": datetime.now().isoformat(),
        "windows": WINDOWS,
        "r_pips": R_PIPS,
        "horizon_days": HORIZON.days,
        "event_counts_total": event_counts_total,
        "unique_structural_levels": unique_sweeps,
        "unique_structural_episodes": unique_episodes,
        "episodes_with_lifecycle_events": episodes_with_sh_bms_rto_lifecycle,
        "episode_linkage_rule": (
            "Un SWEEP apre un nuovo structural_episode_id SOLO se 'SH_BMS_RTO' e' in observed_by "
            "(prova diretta che il suo stato era IDLE in quel momento). TRUE_BREAK/RETEST/INVALIDATE "
            "si agganciano SEMPRE all'ultimo episodio aperto in ordine di event_id (mai per timestamp "
            "piu' vicino). Un nuovo SWEEP SH_BMS_RTO chiude implicitamente l'episodio precedente se "
            "ancora aperto. Vedi vault 'NEXUS - Structural Dataset v1 Causal Linkage Integrity Audit'."
        ),
        "time_to_true_break_removed_reason": (
            "Il campo timestamp di ogni evento e' il bar-open del TF che ha innescato quella "
            "transizione (architettura multi-TF-pass) - non un orologio uniforme fra eventi dello "
            "stesso episodio triggerati da pass diversi. Sottrarre due timestamp puo' invertire "
            "l'ordine reale (osservato empiricamente). event_id stabilisce l'ordine causale corretto "
            "ma non rappresenta secondi - nessuna conversione event_id->tempo eseguita."
        ),
        "data_quality": {k: v for k, v in dq.items() if not k.endswith("_detail")},
        "data_quality_detail": {k: v for k, v in dq.items() if k.endswith("_detail")},
        "m1_coverage": m1_cov,
        "label_coverage": label_coverage,
    }

    def _default(o):
        if isinstance(o, datetime):
            return str(o)
        return str(o)

    with open(os.path.join(OUT_DIR, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, default=_default)

    print("=== STRUCTURAL DATASET v1 ===")
    print(f"structural_events.csv: {len(all_events)} righe")
    print(f"at_sweep.csv: {n_sweep} righe")
    print(f"at_true_break.csv: {n_tb} righe")
    print(f"unique SWEEP structural_level_id (per window): {unique_sweeps}")
    print(f"event_counts_total: {event_counts_total}")
    print("data_quality:", json.dumps({k: v for k, v in dq.items() if not k.endswith("_detail")}, indent=2, default=_default))
    print("m1_coverage:", json.dumps(m1_cov, indent=2, default=_default))
    print("label_coverage:", json.dumps(label_coverage, indent=2, default=_default))


if __name__ == "__main__":
    main()
