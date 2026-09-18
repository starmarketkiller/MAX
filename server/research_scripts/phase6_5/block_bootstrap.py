#!/usr/bin/env python3
"""Phase 6.5 sec.3 - Block Bootstrap (generico, riutilizzabile).

Moving Block Bootstrap (MBB) per una sequenza ORDINATA NEL TEMPO di
osservazioni binarie (outcome TARGET_FIRST=1/STOP_FIRST=0), pensato per
preservare la dipendenza locale che un bootstrap i.i.d. distrugge
(ogni resample i.i.d. rimescola l'ordine, cancellando qualunque
autocorrelazione/clustering reale).

Criterio di lunghezza blocco DICHIARATO PRIMA di guardare l'effetto sul
risultato: L = ceil(n^(1/3)) (regola empirica standard per il block
bootstrap, Politis & Romano - non scelta per allargare o stringere
l'intervallo di H006, e' la stessa formula che verra' applicata a
QUALUNQUE campione futuro con questo modulo).

Nota di scope: qui si applica il block bootstrap alla sequenza degli
EVENTI (dove la dipendenza temporale e' il problema esplicito di questa
fase); il pool di baseline continua a essere trattato con bootstrap
i.i.d. per semplicita' - dichiarato esplicitamente come limite, non
nascosto.
"""
import math

import numpy as np


def block_length_default(n: int) -> int:
    return max(1, math.ceil(n ** (1 / 3)))


def moving_block_bootstrap_ci(binary_series, n_boot=2000, block_length=None, seed=42, alpha=0.05):
    """binary_series: array-like di 0/1 (NaN esclusi PRIMA di chiamare
    questa funzione), ORDINATO per tempo/riga."""
    x = np.asarray([v for v in binary_series if v is not None and not (isinstance(v, float) and np.isnan(v))], dtype=float)
    n = len(x)
    if n < 5:
        return {"n": n, "note": "campione troppo piccolo per block bootstrap"}
    L = block_length or block_length_default(n)
    n_blocks_needed = math.ceil(n / L)
    max_start = n - L
    rng = np.random.default_rng(seed)

    boot_means = np.empty(n_boot)
    for b in range(n_boot):
        starts = rng.integers(0, max_start + 1, size=n_blocks_needed)
        resampled = np.concatenate([x[s:s + L] for s in starts])[:n]
        boot_means[b] = resampled.mean()

    return {
        "n": n, "block_length": L, "n_blocks_needed": n_blocks_needed, "n_boot": n_boot,
        "mean": float(boot_means.mean()),
        "ci_low": float(np.percentile(boot_means, 100 * alpha / 2)),
        "ci_high": float(np.percentile(boot_means, 100 * (1 - alpha / 2))),
        "std": float(boot_means.std()),
    }


def iid_bootstrap_ci(binary_series, n_boot=2000, seed=42, alpha=0.05):
    x = np.asarray([v for v in binary_series if v is not None and not (isinstance(v, float) and np.isnan(v))], dtype=float)
    n = len(x)
    if n < 5:
        return {"n": n, "note": "campione troppo piccolo per bootstrap"}
    rng = np.random.default_rng(seed)
    boot_means = np.empty(n_boot)
    for b in range(n_boot):
        s = rng.choice(x, size=n, replace=True)
        boot_means[b] = s.mean()
    return {
        "n": n, "n_boot": n_boot,
        "mean": float(boot_means.mean()),
        "ci_low": float(np.percentile(boot_means, 100 * alpha / 2)),
        "ci_high": float(np.percentile(boot_means, 100 * (1 - alpha / 2))),
        "std": float(boot_means.std()),
    }


def compare_iid_vs_block(binary_series, n_boot=2000, seed=42):
    iid = iid_bootstrap_ci(binary_series, n_boot=n_boot, seed=seed)
    block = moving_block_bootstrap_ci(binary_series, n_boot=n_boot, seed=seed)
    width_iid = (iid["ci_high"] - iid["ci_low"]) if "ci_high" in iid else None
    width_block = (block["ci_high"] - block["ci_low"]) if "ci_high" in block else None
    widening_pct = ((width_block / width_iid) - 1) * 100 if (width_iid and width_block) else None
    ess_from_block_variance = None
    if "std" in block and block["std"] > 0:
        p_hat = block["mean"]
        ess_from_block_variance = (p_hat * (1 - p_hat)) / (block["std"] ** 2)
    return {
        "iid_bootstrap": iid,
        "block_bootstrap": block,
        "ci_width_iid": width_iid,
        "ci_width_block": width_block,
        "ci_widening_pct_block_vs_iid": widening_pct,
        "ess_from_block_bootstrap_variance": ess_from_block_variance,
    }


if __name__ == "__main__":
    import json
    import os

    ROOT = r"C:\Users\User\ClaudeWork\MAX"
    PHASE6_DIR = os.path.join(ROOT, "server", "research_scripts", "phase6")
    primary = json.load(open(os.path.join(PHASE6_DIR, "h006_primary_result.json"), encoding="utf-8"))
    events = sorted(primary["event_outcomes_summary"], key=lambda e: e["_row"])
    series = []
    for e in events:
        v = e.get("outcome_1.0")
        series.append(1.0 if v == "TARGET_FIRST" else (0.0 if v == "STOP_FIRST" else None))

    result = compare_iid_vs_block(series)
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "h006_block_bootstrap_audit.json")
    json.dump(result, open(out_path, "w", encoding="utf-8"), indent=2, default=str)
    print(json.dumps(result, indent=2, default=str))
    print(f"\nwritten: {out_path}")
