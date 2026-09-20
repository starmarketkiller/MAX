#!/usr/bin/env python3
"""Phase 7.4A Integrity Patch sec.2 - two_sample_block_bootstrap_percentile_p.

Estensione ESPLICITA di statistical_methods_policy.json (vedi voce
"two_sample_block_bootstrap_percentile_p"): compone due primitive gia'
ammesse (moving_block_bootstrap_ci per la serie evento, iid_bootstrap_ci
per il pool di baseline - entrambe da phase6_5/block_bootstrap.py, MAI
reimplementate qui) in un test di differenza a due campioni per outcome
CONTINUI dove Wilson CI95 non si applica (non e' una proporzione)."""
import os
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_5"))
from block_bootstrap import block_length_default  # noqa: E402


def two_sample_block_bootstrap_percentile_p(event_series, baseline_series, n_boot=2000, seed=42):
    """event_series: serie CONTINUA ordinata per tempo (dipendenza seriale
    possibile - ricampionata a blocchi). baseline_series: pool di controllo
    (ricampionato i.i.d. - limite dichiarato in block_bootstrap.py e in
    statistical_methods_policy.json). Ritorna delta_e osservato, la
    distribuzione bootstrap della differenza e un p-value a due code
    (percentile bootstrap test, completamente ispezionabile)."""
    ev = np.asarray([v for v in event_series if v is not None and not (isinstance(v, float) and np.isnan(v))], dtype=float)
    bl = np.asarray([v for v in baseline_series if v is not None and not (isinstance(v, float) and np.isnan(v))], dtype=float)
    n_ev, n_bl = len(ev), len(bl)
    if n_ev < 5 or n_bl < 5:
        return {"n_event": n_ev, "n_baseline": n_bl, "note": "campione troppo piccolo per il bootstrap a due campioni"}

    L = block_length_default(n_ev)
    n_blocks_needed = int(np.ceil(n_ev / L))
    max_start = n_ev - L
    rng = np.random.default_rng(seed)

    delta_boot = np.empty(n_boot)
    for b in range(n_boot):
        starts = rng.integers(0, max_start + 1, size=n_blocks_needed)
        ev_resampled = np.concatenate([ev[s:s + L] for s in starts])[:n_ev]
        bl_resampled = rng.choice(bl, size=n_bl, replace=True)
        delta_boot[b] = ev_resampled.mean() - bl_resampled.mean()

    delta_e_observed = float(ev.mean() - bl.mean())
    p_le0 = float(np.mean(delta_boot <= 0))
    p_ge0 = float(np.mean(delta_boot >= 0))
    p_value = min(1.0, 2 * min(p_le0, p_ge0))

    return {
        "n_event": n_ev, "n_baseline": n_bl, "block_length": L, "n_boot": n_boot,
        "event_mean": float(ev.mean()), "baseline_mean": float(bl.mean()),
        "delta_e_observed": delta_e_observed,
        "delta_e_boot_ci_low": float(np.percentile(delta_boot, 2.5)),
        "delta_e_boot_ci_high": float(np.percentile(delta_boot, 97.5)),
        "p_value": p_value,
        "method": "two_sample_block_bootstrap_percentile_p",
    }


if __name__ == "__main__":
    # ---- Self-test su dati SINTETICI - nessun dato NEXUS. ----
    rng = np.random.default_rng(7)

    # Caso 1: nessuna vera differenza (stessa distribuzione) -> p-value NON deve rifiutare sistematicamente H0.
    same_event = rng.normal(0.5, 0.2, 200)
    same_baseline = rng.normal(0.5, 0.2, 400)
    r1 = two_sample_block_bootstrap_percentile_p(same_event, same_baseline)
    print(f"Caso 1 (nessuna differenza vera): delta_e={r1['delta_e_observed']:.4f}, p={r1['p_value']:.4f}")
    assert r1["p_value"] > 0.05, "con nessuna vera differenza il p-value non dovrebbe risultare falsamente significativo in questo seed"

    # Caso 2: differenza chiara e ampia -> p-value deve rifiutare H0 (piccolo).
    diff_event = rng.normal(1.2, 0.2, 200)
    diff_baseline = rng.normal(0.5, 0.2, 400)
    r2 = two_sample_block_bootstrap_percentile_p(diff_event, diff_baseline)
    print(f"Caso 2 (differenza ampia e reale): delta_e={r2['delta_e_observed']:.4f}, p={r2['p_value']:.4f}")
    assert r2["p_value"] < 0.05, "con una differenza ampia e reale il p-value dovrebbe risultare significativo"

    # Caso 3: campione troppo piccolo -> nessun p-value calcolato, nota esplicita.
    r3 = two_sample_block_bootstrap_percentile_p([0.1, 0.2], [0.1, 0.2, 0.3])
    assert "p_value" not in r3 and "note" in r3
    print(f"Caso 3 (campione insufficiente): {r3['note']}")

    print("\nSelf-test two_sample_block_bootstrap_percentile_p completato su dati SINTETICI.")
