#!/usr/bin/env python3
"""Phase 7.27 punto 2 - generatori dei 4 benchmark preregistrati (+
buy-and-hold come contesto, gestito separatamente). Ogni funzione usa
SOLO indici di barra e il regime GIA' classificato causalmente (Phase
7.27's nxs_regime_classifier) - nessuna informazione futura."""
import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nxs_gold_d1_loader import load_d1  # noqa: E402
from nxs_regime_classifier import build_regime_table, regime_bucket_key  # noqa: E402
import nxs_prereg_constants as C  # noqa: E402


def _period_bounds_idx(period_start_dt, period_end_dt):
    df = load_d1()
    mask = (df["time"] >= period_start_dt) & (df["time"] <= period_end_dt)
    idxs = df.index[mask]
    return int(idxs[0]), int(idxs[-1])


def random_timestamps_matched(period_start_dt, period_end_dt, n, seed):
    start_idx, end_idx = _period_bounds_idx(period_start_dt, period_end_dt)
    rng = random.Random(seed)
    pool = list(range(start_idx, end_idx + 1))
    return sorted(rng.sample(pool, min(n, len(pool))))


def unconditional_population(period_start_dt, period_end_dt):
    start_idx, end_idx = _period_bounds_idx(period_start_dt, period_end_dt)
    return list(range(start_idx, end_idx + 1))


def periodic_entries(period_start_dt, period_end_dt, n):
    start_idx, end_idx = _period_bounds_idx(period_start_dt, period_end_dt)
    span = end_idx - start_idx
    if n <= 0 or span <= 0:
        return []
    step = max(1, span // n)
    idxs = list(range(start_idx, end_idx + 1, step))
    return idxs[:n]


def regime_matched_random(real_bar_indices, period_start_dt, period_end_dt, seed):
    """Per ogni indice reale, campiona UN indice diverso nella stessa
    finestra con lo STESSO bucket di regime (trend, vol_tercile) - se
    il bucket ha <2 barre disponibili (solo la barra reale stessa),
    quell'evento resta NOT_AVAILABLE per questo benchmark (dichiarato,
    non forzato su un bucket diverso)."""
    start_idx, end_idx = _period_bounds_idx(period_start_dt, period_end_dt)
    regime_df = build_regime_table()
    window = regime_df.iloc[start_idx:end_idx + 1]
    buckets = {}
    for idx, row in window.iterrows():
        key = (row["sma50_slope"], row["vol_tercile"])
        buckets.setdefault(key, []).append(int(idx))

    rng = random.Random(seed)
    matched = []
    for real_idx in real_bar_indices:
        row = regime_df.iloc[real_idx]
        key = (row["sma50_slope"], row["vol_tercile"])
        pool = [i for i in buckets.get(key, []) if i != real_idx]
        if not pool:
            matched.append(None)
            continue
        matched.append(rng.choice(pool))
    return matched


def seed_for(strategy_identity, benchmark_name):
    """Seed deterministico per-strategia-per-benchmark, derivato dal
    seed base preregistrato - MAI scelto per ottenere un risultato
    specifico (dichiarato prima di ogni campionamento). Usa un hash
    STABILE (zlib.crc32), non l'hash builtin di Python (randomizzato
    fra processi per le stringhe - non riproducibile)."""
    import zlib
    key = f"{strategy_identity}|{benchmark_name}".encode("utf-8")
    return (C.RANDOM_SEED_BASE + zlib.crc32(key)) % (2 ** 31)
