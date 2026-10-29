"""Preregistered gate + sizing variants. Causal: weight at t applies to t→t+1."""
from __future__ import annotations

from .series import (
    filter_eval_indices,
    log_returns,
    realized_vol,
    trailing_return,
    vol_weight,
)


def _sign_gate(r12, mode):
    """Return desired direction in {-1, 0, +1}."""
    if r12 is None:
        return None
    if mode == "long_if_r12_positive_else_flat":
        if r12 > 0:
            return 1
        return 0
    if mode == "sign_of_r12":
        if r12 > 0:
            return 1
        if r12 < 0:
            return -1
        return 0
    raise ValueError(f"unknown gate mode {mode}")


def build_variant_rows(bars, prereg, split, variant_id):
    """One row per evaluation day for a single variant + matched BH."""
    params = prereg["params"]
    spec = prereg["variants"][variant_id]
    lookback = int(params["lookback_bars"])
    vol_lb = int(params["vol_lookback_bars"])
    target = float(params["target_vol_annual"])
    cap = float(params["leverage_cap"])
    cost_bps = float(params["cost_bps_roundtrip"])
    tpy = float(params["trading_days_per_year"])
    warm_up = lookback + vol_lb

    closes = [b["close"] for b in bars]
    lrets = log_returns(closes)
    indices = filter_eval_indices(bars, prereg, split, warm_up)

    rows = []
    prev_w = 0.0
    prev_bh = 0.0
    for i in indices:
        r12 = trailing_return(closes, i, lookback)
        sigma = realized_vol(lrets, i, vol_lb, tpy)
        direction = _sign_gate(r12, spec["gate"])
        if direction is None:
            continue
        asset_ret = lrets[i + 1]
        if asset_ret is None:
            continue

        if spec["sizing"] == "unit":
            scale = 1.0
            bh_scale = 1.0
        elif spec["sizing"] == "vol_target":
            scale = vol_weight(sigma, target, cap)
            bh_scale = scale  # same σ̂ day; BH always long
            if scale is None:
                continue
        else:
            raise ValueError(spec["sizing"])

        w = direction * scale
        bh_w = bh_scale  # always long matched size
        # Cost on absolute weight change (strategy and BH separately).
        strat_cost = (cost_bps / 10000.0) * abs(w - prev_w)
        bh_cost = (cost_bps / 10000.0) * abs(bh_w - prev_bh)
        # Approximate: weight * simple log asset return − cost (cost in return units).
        strat_ret = w * asset_ret - strat_cost
        bh_ret = bh_w * asset_ret - bh_cost
        excess = strat_ret - bh_ret
        prev_w = w
        prev_bh = bh_w

        rows.append({
            "status": "CLOSED",
            "variant_id": variant_id,
            "date": bars[i]["date"],
            "entry_time": bars[i]["ts"],
            "exit_time": bars[i + 1]["ts"],
            "r12": r12,
            "sigma_ann": sigma,
            "weight": w,
            "bh_weight": bh_w,
            "asset_log_return": asset_ret,
            "strategy_log_return": strat_ret,
            "bh_log_return": bh_ret,
            "excess_log_return": excess,
            "year": bars[i]["date"][:4],
            "month": bars[i]["date"][:7],
            "split_tag": split,
        })
    return rows


def build_all_variants(bars, prereg, split):
    out = {}
    for vid in prereg["params"]["variant_ids"]:
        out[vid] = build_variant_rows(bars, prereg, split, vid)
    return out
