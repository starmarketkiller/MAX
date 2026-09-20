#!/usr/bin/env python3
"""Phase 7.4A Dependence-Aware Inference Redesign sec.10 - simulazione
BH-FDR a 21 celle SENZA gating, per i 3 metodi candidati. Stessi 3
scenari della validazione precedente (global null iid, global null
dipendenza mista, misto 14 null + 7 effetti) - qui pero' NESSUNA cella
viene mai scartata o sostituita con p=1."""
import json
import math
import os
import sys
import time

import numpy as np

PHASE74_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE74_DIR, "..", "..", "..", ".."))
ENGINE_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "engine")
sys.path.insert(0, ENGINE_DIR)

from dependence_aware_mean_tests import null_centered_block_bootstrap_p, studentized_block_bootstrap_p, hac_newey_west_p  # noqa: E402
from ungated_bh_family import build_ungated_bh_family  # noqa: E402

METHODS = {
    "A_null_centered_block_bootstrap": (null_centered_block_bootstrap_p, {"n_boot": 500}),
    "B_studentized_block_bootstrap": (studentized_block_bootstrap_p, {"n_boot": 500}),
    "C_hac_newey_west": (hac_newey_west_p, {}),
}
Q_FDR = 0.10


def mc_tolerance(true_rate, n_reps, n_sigma=3):
    return n_sigma * math.sqrt(true_rate * (1 - true_rate) / n_reps)


def gen_ar1(rng, phi, n=30, mean_shift=0.0):
    eps = rng.normal(0.0, 1.0, n)
    x = np.empty(n)
    x[0] = eps[0] + mean_shift
    for t in range(1, n):
        x[t] = phi * x[t - 1] + eps[t] * np.sqrt(1 - phi ** 2) + mean_shift * (1 - phi)
    return x


def build_cells(rng, spec):
    cells = []
    idx = 0
    for n_cells, phi, mean_shift in spec:
        for _ in range(n_cells):
            d = gen_ar1(rng, phi, n=30, mean_shift=mean_shift)
            cells.append({"cell_id": f"CELL-{idx}", "d_values": list(d), "_true_effect": mean_shift != 0.0})
            idx += 1
    return cells


def run_scenario(method_name, name, spec, n_true_effects, n_family_reps):
    fn, kw = METHODS[method_name]
    rng = np.random.default_rng(hash(f"{method_name}_{name}") % (2**32))
    t0 = time.time()
    any_rejection, fdps, powers = [], [], []
    for rep in range(n_family_reps):
        cells = build_cells(rng, spec)
        result = build_ungated_bh_family(cells, fn, kw, q=Q_FDR)
        sig_cells = [c for c in result["cells"] if c["bh_result"]["significant_at_q"]]
        n_sig = len(sig_cells)
        n_false_disc = sum(1 for c in sig_cells if not c["_true_effect"])
        fdps.append(n_false_disc / n_sig if n_sig > 0 else 0.0)
        any_rejection.append(n_sig > 0)
        if n_true_effects > 0:
            powers.append(sum(1 for c in sig_cells if c["_true_effect"]) / n_true_effects)
    elapsed = time.time() - t0
    row = {"method": method_name, "scenario": name, "n_family_reps": n_family_reps,
          "family_size": sum(s[0] for s in spec), "n_true_effects": n_true_effects, "elapsed_sec": round(elapsed, 1),
          "probability_any_rejection": float(np.mean(any_rejection)), "empirical_fdr": float(np.mean(fdps)),
          "mc_tolerance_fdr": mc_tolerance(Q_FDR, n_family_reps)}
    if n_true_effects > 0:
        row["power"] = float(np.mean(powers))
    print(f"[21cell] {method_name} {name}: P(any_rej)={row['probability_any_rejection']:.4f} "
          f"FDR={row['empirical_fdr']:.4f} {'power='+format(row.get('power',0),'.4f') if n_true_effects else ''} ({elapsed:.1f}s)")
    return row


def main():
    method_name = sys.argv[1]
    n_family_reps = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    scenarios = [
        ("global_null_iid_21_cells", [(21, 0.0, 0.0)], 0),
        ("global_null_mixed_dependence_21_cells", [(6, 0.0, 0.0), (5, 0.2, 0.0), (5, 0.5, 0.0), (5, 0.7, 0.0)], 0),
        ("mixed_14null_7effect_iid", [(14, 0.0, 0.0), (7, 0.0, 0.8)], 7),
    ]
    rows = [run_scenario(method_name, name, spec, n_eff, n_family_reps) for name, spec, n_eff in scenarios]
    out_path = os.path.join(PHASE74_DIR, f"_dac_21cell_{method_name}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)
    print(f"\nScritto: {out_path}")


if __name__ == "__main__":
    main()
