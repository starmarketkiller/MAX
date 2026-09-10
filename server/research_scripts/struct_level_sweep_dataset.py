"""STRUCT_LEVEL_SWEEP - dataset offline Python (10/09).

Richiesto dall'utente PRIMA di toccare Structure Engine/Reaction Engine/
strategie: costruire una distribuzione statistica "penetration depth ->
probability/magnitude of reversal" usando dati storici GOLD gia' presenti nel
repo, SENZA guardare SL/TP per definire successo (misura il comportamento
naturale del prezzo dopo l'interazione col livello).

FONTE DATI: server/research_scripts/nxs_m15_gold_extended.csv (M15,
2023-10-02 -> 2026-08-25). E' la fonte piu' fine disponibile nel repo - NON
esiste dato M1/M5. Verificato: il resample M15->H4 (resample('4h',
origin='start_day')) e' BIT-ESATTO contro nxs_h4_gold_29-08.csv sul periodo
in comune (2533 barre, diff massima 0.0 su OHLC) - alta fiducia sulla
ricostruzione H4/H1. La ricostruzione D1 (resample('1D') a mezzanotte) NON e'
verificata contro un file D1 di riferimento - i broker aprono tipicamente la
giornata FX/commodity intorno alle 22-23 GMT, non a mezzanotte: usata SOLO
come fonte pivot secondaria (D1), fedelta' non garantita, flag esplicito nel
report.

FEDELTA' DICHIARATA (obbligo esplicito dell'utente):
  - Swing high/low (Structure Engine, wing=3): fedele. Nessuna dipendenza da
    ATR, stessa identica logica di NXS_IsSwingHigh/Low (confronto stretto
    <, non <=, replicato esattamente).
  - Wick H4 (livello WICK_SWEEP_REV): fedele. Nessuna dipendenza da ATR,
    stessa soglia in pip fissi di _NXS_WickSweep_UpdateLevel.
  - Pivot frattali multi-TF H1/H4/D1 (wing=5, pool PIVOT_WICK/LEVEL_REACTION):
    fedele su H1/H4 (resample verificato), FEDELTA' D1 NON VERIFICATA (vedi
    sopra).
  - SNR H4 (rolling 12-barre chiusura, fonte 2 di LEVEL_REACTION): fedele,
    nessuna dipendenza da ATR.
  - OB/FVG: NON REPLICATI in questo primo giro. NXS_DetectOrderBlocks/
    NXS_DetectFVG dipendono da g_atr (handle iATR live, Wilder-smoothed,
    stato di warm-up non bit-verificabile offline con la stessa precisione
    delle altre 4 fonti) E da una soglia di displacement sulla candela
    SUCCESSIVA - due gradi di liberta' in piu' che avrebbero reso il
    confronto fedelta'-vs-le-altre-4-fonti meno onesto. Rimandato a un
    secondo giro se questo primo dataset si rivela utile.

NESSUN LOOKAHEAD: un livello "nasce" (created_at) SOLO quando le barre
necessarie a confermarlo sono gia' chiuse nel tempo (uno swing con wing=3
richiede 3 barre DOPO il pivot - created_at = tempo del pivot + 3 barre
della sua TF, mai il tempo del pivot stesso). L'interazione (touch) e'
analizzata SOLO su barre M15 con timestamp >= created_at.

USO SL/TP: NESSUNO. Il "successo" qui e' definito SOLO da reclaim/broken/
MFE/MAE a orizzonti di tempo fissi (15m/30m/1h/4h - NON 5m, dato non
disponibile a quella risoluzione, vedi sopra), mai da una soglia di
rischio ipotetica.

Uso:
    python3 struct_level_sweep_dataset.py
Output:
    struct_level_sweep_events.csv   (un rigo per touch event)
    struct_level_sweep_bins.csv     (aggregato per bin di penetrazione)
    stampa a schermo il report leggibile
"""
from __future__ import annotations
import pandas as pd
import numpy as np

# ============================= PARAMETRI ESPLICITI ==========================
# Ogni soglia qui e' un giudizio metodologico dichiarato, non un fatto - vedi
# report finale per la lista di cosa e' "misurato" vs "assunto per costruire
# lo studio".
PIP = 0.10                          # 1 pip = $0.10 su GOLD (convenzione Nexus/vault)
SWING_WING = 3                       # = InpSwingWing (NXS_Structure.mqh)
PIVOT_WING = 5                       # = InpPivotWickLookback (NXS_Strategies.mqh)
WICK_MIN_PIPS = 15.0                 # = InpWickSweep_MinWickPips (soglia di GENERAZIONE, non di sweep)
SNR_LOOKBACK_BARS = 12               # = fonte 2 di LEVEL_REACTION (rolling H4 close)
RECLAIM_BUFFER_PIPS = 0.0            # reclaim = chiusura M15 di ritorno al livello, nessun margine extra
BROKEN_HORIZON_DAYS = 5              # oltre questo, se non reclamato -> "broken" (provvisorio, dato a dirci se e' troppo corto/lungo)
MFE_MAE_HORIZONS_M15 = {"15m": 1, "30m": 2, "1h": 4, "4h": 16}   # in barre M15
PENETRATION_BINS = [0, 10, 20, 30, 40, 50, 75, 100, np.inf]
PENETRATION_LABELS = ["0-10", "10-20", "20-30", "30-40", "40-50", "50-75", "75-100", "100+"]

DATA_PATH = "nxs_m15_gold_extended.csv"
OUT_EVENTS = "struct_level_sweep_events.csv"
OUT_BINS = "struct_level_sweep_bins.csv"


def load_m15():
    df = pd.read_csv(DATA_PATH, parse_dates=["time"], date_format="%Y.%m.%d %H:%M")
    df = df.set_index("time").sort_index()
    df = df[~df.index.duplicated(keep="first")]
    return df


def resample_ohlc(m15, rule, origin="start_day"):
    return m15.resample(rule, origin=origin).agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}
    ).dropna()


# --------------------------- SOURCE 1: SWING (Structure Engine) -------------
def find_swing_levels(h4, wing):
    """Replica esatta di NXS_IsSwingHigh/Low (Structure.mqh:80-98): confronto
    STRETTO su wing barre a sx e dx. confirm_idx = pivot_idx + wing (barre
    DOPO il pivot necessarie per confermarlo dal vivo - niente lookahead)."""
    highs = h4["high"].values
    lows = h4["low"].values
    times = h4.index
    n = len(h4)
    events = []
    for i in range(wing, n - wing):
        h, l = highs[i], lows[i]
        is_high = all(highs[i - k] < h for k in range(1, wing + 1)) and all(highs[i + k] < h for k in range(1, wing + 1))
        is_low = all(lows[i - k] > l for k in range(1, wing + 1)) and all(lows[i + k] > l for k in range(1, wing + 1))
        confirm_i = i + wing
        if confirm_i >= n:
            continue
        created_at = times[confirm_i]
        if is_high:
            events.append(dict(source="SWING", source_tf="H4", level_price=h, direction="SELL",
                                created_at=created_at, pivot_time=times[i]))
        if is_low:
            events.append(dict(source="SWING", source_tf="H4", level_price=l, direction="BUY",
                                created_at=created_at, pivot_time=times[i]))
    return events


# --------------------------- SOURCE 2: WICK H4 (WICK_SWEEP_REV) -------------
def find_wick_levels(h4, min_pips):
    """Replica _NXS_WickSweep_UpdateLevel: wick della candela H4 appena
    chiusa >= soglia -> livello. created_at = chiusura della barra (bar
    time + 4h), MAI il suo tempo di apertura."""
    events = []
    min_dist = min_pips * PIP
    for t, row in h4.iterrows():
        body_top = max(row["open"], row["close"])
        body_bot = min(row["open"], row["close"])
        upper_wick = row["high"] - body_top
        lower_wick = body_bot - row["low"]
        created_at = t + pd.Timedelta(hours=4)
        if upper_wick >= min_dist:
            events.append(dict(source="WICK_H4", source_tf="H4", level_price=row["high"], direction="SELL",
                                created_at=created_at, pivot_time=t))
        if lower_wick >= min_dist:
            events.append(dict(source="WICK_H4", source_tf="H4", level_price=row["low"], direction="BUY",
                                created_at=created_at, pivot_time=t))
    return events


# --------------------------- SOURCE 3: PIVOT multi-TF -----------------------
def find_pivot_levels(tf_bars, tf_name, wing):
    """Stessa logica di find_swing_levels ma parametrizzata per TF - replica
    il pool pivot condiviso PIVOT_WICK/LEVEL_REACTION (H1/H4/D1, wing=5)."""
    events = []
    for e in find_swing_levels(tf_bars, wing):
        e["source"] = "PIVOT"
        e["source_tf"] = tf_name
        events.append(e)
    return events


# --------------------------- SOURCE 4: SNR H4 rolling-12-close --------------
def find_snr_levels(h4, lookback):
    """Replica la fonte 2 di LEVEL_REACTION: iHighest/iLowest su MODE_CLOSE,
    12 barre H4, shift 1 (barre CHIUSE, esclude quella in corso). Livello
    ricalcolato ogni barra - registriamo l'evento solo quando il valore
    CAMBIA rispetto alla barra precedente, per non duplicare lo stesso
    livello 12 volte di fila."""
    close = h4["close"]
    roll_max = close.shift(1).rolling(lookback).max()
    roll_min = close.shift(1).rolling(lookback).min()
    events = []
    last_hi, last_lo = None, None
    for t, hi, lo in zip(h4.index, roll_max, roll_min):
        created_at = t   # il valore e' gia' noto ALL'APERTURA di questa barra (usa solo barre precedenti chiuse)
        if pd.notna(hi) and hi != last_hi:
            events.append(dict(source="SNR_H4", source_tf="H4", level_price=hi, direction="SELL",
                                created_at=created_at, pivot_time=created_at))
            last_hi = hi
        if pd.notna(lo) and lo != last_lo:
            events.append(dict(source="SNR_H4", source_tf="H4", level_price=lo, direction="BUY",
                                created_at=created_at, pivot_time=created_at))
            last_lo = lo
    return events


# --------------------------- TOUCH / REACTION ANALYSIS ----------------------
# Vettorizzato con numpy: la ricerca del PROSSIMO touch (stato AWAY, che su
# migliaia di livelli e decine di migliaia di barre e' il costo dominante)
# usa np.flatnonzero invece di un loop barra-per-barra in Python puro - stessa
# semantica del design a stati originale, molto piu' veloce. Ogni episodio
# TOUCHING resta comunque limitato a broken_horizon barre (bound piccolo).
BARS_PER_DAY_M15 = 24 * 4
MAX_TOUCHES_PER_LEVEL = 50   # safety cap, vedi commento dentro analyze_level


def analyze_level(level, m15_times, m15_high, m15_low, m15_close, last_data_time, broken_horizon):
    """Vedi design originale: AWAY -> TOUCHING (episodio) -> reclaim chiude
    l'episodio, un nuovo touch puo' iniziare subito dopo (chop ripetuto sullo
    stesso livello = touch multipli, realistico). Niente lookahead: si parte
    da created_at, mai prima."""
    price = level["level_price"]
    direction = level["direction"]
    created_at = level["created_at"]
    n = len(m15_times)

    start_idx = np.searchsorted(m15_times, np.datetime64(created_at), side="left")
    if start_idx >= n:
        return []

    breach_arr = (m15_high - price) if direction == "SELL" else (price - m15_low)
    touched_arr = breach_arr >= 0.0
    buf = RECLAIM_BUFFER_PIPS * PIP
    if direction == "SELL":
        reclaim_arr = m15_close <= (price - buf)
    else:
        reclaim_arr = m15_close >= (price + buf)

    horizon_bars = int(broken_horizon * BARS_PER_DAY_M15)

    rows = []
    touch_number = 0
    i = start_idx
    while i < n:
        if touch_number >= MAX_TOUCHES_PER_LEVEL:
            # 10/09 - safety cap: alcuni livelli (soprattutto SNR_H4, ricalcolato
            # ogni barra sul rolling delle chiusure) restano "incollati" al
            # prezzo e producono migliaia di micro touch/reclaim consecutivi -
            # non un bug di analisi, ma non informativo oltre un certo punto e
            # costoso da scandire per intero. Oltre MAX_TOUCHES_PER_LEVEL si
            # ferma l'analisi DI QUESTO livello (i touch gia' raccolti restano
            # validi, quelli oltre il cap sono omessi, non fabbricati).
            break
        rel = np.flatnonzero(touched_arr[i:])
        if rel.size == 0:
            break
        ep_start_idx = i + int(rel[0])
        touch_number += 1

        end_bound = min(ep_start_idx + horizon_bars, n - 1)
        reclaim_rel = np.flatnonzero(reclaim_arr[ep_start_idx:end_bound + 1])

        if reclaim_rel.size > 0:
            reclaim_idx = ep_start_idx + int(reclaim_rel[0])
            window = breach_arr[ep_start_idx:reclaim_idx + 1]
            ep_max_pen_idx = ep_start_idx + int(window.argmax())
            ep_max_pen = float(window[ep_max_pen_idx - ep_start_idx])
            rows.append(_build_row(level, touch_number, ep_start_idx, ep_max_pen, ep_max_pen_idx,
                                    reclaim_idx=reclaim_idx, broken=False, censored=False,
                                    m15_times=m15_times, m15_high=m15_high, m15_low=m15_low, m15_close=m15_close))
            i = reclaim_idx + 1
        else:
            window = breach_arr[ep_start_idx:end_bound + 1]
            ep_max_pen_idx = ep_start_idx + int(window.argmax())
            ep_max_pen = float(window[ep_max_pen_idx - ep_start_idx])
            # censurato (non "broken") solo se i dati sono finiti PRIMA che
            # l'orizzonte fosse trascorso davvero - altrimenti e' una vera
            # non-reclaim osservata per intero.
            elapsed_days = (pd.Timestamp(m15_times[end_bound]) - pd.Timestamp(m15_times[ep_start_idx])) / np.timedelta64(1, "D")
            data_exhausted_early = (end_bound == n - 1) and (elapsed_days < broken_horizon)
            rows.append(_build_row(level, touch_number, ep_start_idx, ep_max_pen, ep_max_pen_idx,
                                    reclaim_idx=None, broken=(not data_exhausted_early), censored=data_exhausted_early,
                                    m15_times=m15_times, m15_high=m15_high, m15_low=m15_low, m15_close=m15_close))
            i = end_bound + 1
    return rows


def _build_row(level, touch_number, ep_start_idx, max_pen, max_pen_idx, reclaim_idx, broken, censored,
               m15_times, m15_high, m15_low, m15_close):
    direction = level["direction"]
    price = level["level_price"]
    first_touch_at = pd.Timestamp(m15_times[ep_start_idx])
    age_at_touch = (first_touch_at - level["created_at"]) / np.timedelta64(1, "h")  # ore

    reclaimed = reclaim_idx is not None
    time_to_reclaim_h = ((pd.Timestamp(m15_times[reclaim_idx]) - first_touch_at) / np.timedelta64(1, "h")) if reclaimed else np.nan
    time_to_max_pen_h = (pd.Timestamp(m15_times[max_pen_idx]) - first_touch_at) / np.timedelta64(1, "h")

    row = dict(
        source=level["source"], source_tf=level["source_tf"], level_price=price, direction=direction,
        created_at=level["created_at"], first_touch_at=first_touch_at, age_at_touch_hours=round(age_at_touch, 2),
        touch_number=touch_number, max_penetration_pips=round(max_pen / PIP, 2),
        time_to_max_penetration_hours=round(time_to_max_pen_h, 2),
        reclaimed=reclaimed, time_to_reclaim_hours=round(time_to_reclaim_h, 2) if reclaimed else np.nan,
        broken=broken, censored=censored,
    )

    entry_price = price
    n = len(m15_times)
    for label, bars in MFE_MAE_HORIZONS_M15.items():
        end_idx = min(ep_start_idx + bars, n - 1)
        window_high = m15_high[ep_start_idx:end_idx + 1].max()
        window_low = m15_low[ep_start_idx:end_idx + 1].min()
        if direction == "BUY":
            mfe = (window_high - entry_price) / PIP
            mae = (entry_price - window_low) / PIP
        else:
            mfe = (entry_price - window_low) / PIP
            mae = (window_high - entry_price) / PIP
        row[f"MFE_{label}"] = round(mfe, 2)
        row[f"MAE_{label}"] = round(mae, 2)
    return row


def main():
    m15 = load_m15()
    last_data_time = m15.index.max()
    print(f"M15 caricato: {len(m15)} barre, {m15.index.min()} -> {last_data_time}")
    print("ATTENZIONE FEDELTA': dato piu' fine disponibile = M15. MFE/MAE_5m NON calcolabile, omesso.\n")

    h4 = resample_ohlc(m15, "4h", origin="start_day")
    h1 = resample_ohlc(m15, "1h", origin="start_day")
    d1 = resample_ohlc(m15, "1D", origin="start_day")
    print(f"H4: {len(h4)} barre (verificato bit-esatto vs nxs_h4_gold_29-08.csv)")
    print(f"H1: {len(h1)} barre (stessa metodologia verificata di H4, non ri-verificato singolarmente)")
    print(f"D1: {len(d1)} barre (FEDELTA' NON VERIFICATA - confine giornata approssimato a mezzanotte)\n")

    levels = []
    levels += find_swing_levels(h4, SWING_WING)
    levels += find_wick_levels(h4, WICK_MIN_PIPS)
    levels += find_pivot_levels(h1, "H1", PIVOT_WING)
    levels += find_pivot_levels(h4, "H4", PIVOT_WING)
    levels += find_pivot_levels(d1, "D1", PIVOT_WING)
    levels += find_snr_levels(h4, SNR_LOOKBACK_BARS)
    for idx, lv in enumerate(levels):
        lv["level_id"] = idx
    print(f"Livelli generati (pre-interazione): {len(levels)}")
    by_source = pd.DataFrame(levels).groupby(["source", "source_tf"]).size()
    print(by_source, "\n")

    m15_times = m15.index.values
    m15_high = m15["high"].values
    m15_low = m15["low"].values
    m15_close = m15["close"].values

    all_rows = []
    import time as _time
    t0 = _time.time()
    import sys as _sys
    for k, lv in enumerate(levels):
        all_rows.extend(analyze_level(lv, m15_times, m15_high, m15_low, m15_close,
                                       last_data_time, BROKEN_HORIZON_DAYS))
        if (k + 1) % 500 == 0:
            print(f"  ...{k+1}/{len(levels)} livelli analizzati ({_time.time()-t0:.1f}s, "
                  f"ultimo={lv['source']}/{lv['source_tf']})")
            _sys.stdout.flush()
    print(f"Analisi livelli completata in {_time.time()-t0:.1f}s\n")

    ev = pd.DataFrame(all_rows)
    print(f"Touch events totali: {len(ev)} (di cui censurati per fine-dataset: {ev['censored'].sum()})\n")

    ev_valid = ev[~ev["censored"]].copy()
    ev_valid["penetration_bin"] = pd.cut(ev_valid["max_penetration_pips"], bins=PENETRATION_BINS,
                                          labels=PENETRATION_LABELS, right=False)

    ev.to_csv(OUT_EVENTS, index=False)
    print(f"Scritto {OUT_EVENTS} ({len(ev)} righe)\n")

    # ---- aggregazione per bin ----
    agg_rows = []
    for label in PENETRATION_LABELS:
        sub = ev_valid[ev_valid["penetration_bin"] == label]
        n = len(sub)
        if n == 0:
            agg_rows.append(dict(bin=label, n_events=0))
            continue
        n_resolved = sub[~sub["broken"].isna()]
        pct_reclaim = 100.0 * sub["reclaimed"].sum() / n
        pct_broken = 100.0 * sub["broken"].sum() / n
        first_touch = sub[sub["touch_number"] == 1]
        repeat_touch = sub[sub["touch_number"] > 1]
        agg_rows.append(dict(
            bin=label, n_events=n,
            pct_reclaim=round(pct_reclaim, 1),
            pct_broken_or_continuation=round(pct_broken, 1),
            median_MFE_1h=round(sub["MFE_1h"].median(), 2), mean_MFE_1h=round(sub["MFE_1h"].mean(), 2),
            median_MAE_1h=round(sub["MAE_1h"].median(), 2), mean_MAE_1h=round(sub["MAE_1h"].mean(), 2),
            median_MFE_4h=round(sub["MFE_4h"].median(), 2), mean_MFE_4h=round(sub["MFE_4h"].mean(), 2),
            median_MAE_4h=round(sub["MAE_4h"].median(), 2), mean_MAE_4h=round(sub["MAE_4h"].mean(), 2),
            median_time_to_reclaim_h=round(sub.loc[sub["reclaimed"], "time_to_reclaim_hours"].median(), 2)
                if sub["reclaimed"].any() else np.nan,
            n_first_touch=len(first_touch), n_repeat_touch=len(repeat_touch),
            median_age_at_touch_h=round(sub["age_at_touch_hours"].median(), 2),
        ))
    bins_df = pd.DataFrame(agg_rows)
    bins_df.to_csv(OUT_BINS, index=False)

    print("=" * 100)
    print("REPORT PER BIN DI PENETRAZIONE (1 pip = $0.10, GOLD)")
    print("=" * 100)
    print(bins_df.to_string(index=False))

    print("\n" + "=" * 100)
    print("DISTRIBUZIONE PER SOURCE_TF (tutti i touch validi, non censurati)")
    print("=" * 100)
    print(ev_valid.groupby(["source", "source_tf"]).agg(
        n=("level_price", "size"),
        pct_reclaim=("reclaimed", lambda s: round(100 * s.sum() / len(s), 1)),
        median_max_penetration_pips=("max_penetration_pips", "median"),
    ))

    print("\n" + "=" * 100)
    print("FIRST TOUCH vs REPEATED TOUCH (tutti i bin)")
    print("=" * 100)
    ft = ev_valid[ev_valid["touch_number"] == 1]
    rt = ev_valid[ev_valid["touch_number"] > 1]
    print(f"First touch:  n={len(ft)}  pct_reclaim={100*ft['reclaimed'].sum()/len(ft):.1f}%  "
          f"median_penetration={ft['max_penetration_pips'].median():.1f}pip")
    print(f"Repeat touch: n={len(rt)}  pct_reclaim={100*rt['reclaimed'].sum()/len(rt):.1f}%  "
          f"median_penetration={rt['max_penetration_pips'].median():.1f}pip")


if __name__ == "__main__":
    main()
