"""Shared, frozen-input utilities for MACD Phase 1 selection and test."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

from macd_features import extract_macd_features


HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3]
DATASET_DIR = ROOT / "server/research_datasets/market_state_v1"
PREREG_PATH = HERE / "macd_preregistration_v1.json"
PREREG_SIDECAR = HERE / "macd_preregistration_v1.sha256"
SELECTION_PATH = HERE / "macd_selection_manifest_v1.json"
SELECTION_SIDECAR = HERE / "macd_selection_manifest_v1.sha256"
EXPECTED_PREREG_SHA256 = "8d04447c4542babe47b140bd0bbcabce7ca299335743f72c4d4efca3dc6477ad"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_frozen_preregistration() -> dict:
    actual = file_sha256(PREREG_PATH)
    sidecar = PREREG_SIDECAR.read_text(encoding="ascii").strip().split()[0]
    if actual != EXPECTED_PREREG_SHA256 or sidecar != EXPECTED_PREREG_SHA256:
        raise RuntimeError("preregistration hash mismatch; fail-closed")
    prereg = json.loads(PREREG_PATH.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_NOT_EXECUTED":
        raise RuntimeError("preregistration is not FROZEN_NOT_EXECUTED")
    return prereg


def verify_dataset_hashes(prereg: dict) -> None:
    expected = {
        "market_state_dataset_v1.csv": prereg["dataset"]["market_state_sha256"],
        "xauusd_h4_bars.csv": prereg["dataset"]["bars_sha256"],
    }
    for filename, digest in expected.items():
        if file_sha256(DATASET_DIR / filename) != digest:
            raise RuntimeError(f"dataset hash mismatch: {filename}")


def load_analysis_frame(prereg: dict) -> pd.DataFrame:
    verify_dataset_hashes(prereg)
    bars = pd.read_csv(DATASET_DIR / "xauusd_h4_bars.csv")
    state = pd.read_csv(DATASET_DIR / "market_state_dataset_v1.csv")
    regime = pd.read_csv(ROOT / "server/research_scripts/phase5_5/regime_layer_v1.csv")
    if not (len(bars) == len(state) == len(regime) == prereg["dataset"]["row_count"]):
        raise RuntimeError("dataset/regime row-count mismatch")
    if not bars["bar_epoch"].equals(state["bar_epoch"]):
        raise RuntimeError("bars/state row identity mismatch")
    if not bars["bar_epoch"].equals(regime["bar_epoch"]):
        raise RuntimeError("bars/regime row identity mismatch")

    frame = bars.copy()
    frame["atr"] = pd.to_numeric(state["atr"], errors="coerce")
    frame["regime_v1"] = regime["regime_v1"]
    frame["bar_time_utc"] = pd.to_datetime(frame["bar_time_utc"], utc=True)
    frame["period_bucket"] = frame["bar_time_utc"].dt.year.astype(str)
    frame = pd.concat([frame, extract_macd_features(frame)], axis=1)
    frame["row_id"] = frame.index.astype(int)
    return frame


def split_boundaries(prereg: dict) -> dict:
    return {
        "discovery": tuple(prereg["split_boundaries"]["discovery_rows"]),
        "internal_validation": tuple(prereg["split_boundaries"]["internal_validation_rows"]),
    }


def event_direction(crossover: str) -> str | None:
    return {"BULLISH_CROSS": "BUY", "BEARISH_CROSS": "SELL"}.get(crossover)


def prepare_observations(prereg: dict, frame: pd.DataFrame) -> tuple[list[dict], list[int], dict]:
    horizon = prereg["test_family"]["horizon_H4_bars"]
    crossover_rows = set(frame.index[frame["crossover"].isin(["BULLISH_CROSS", "BEARISH_CROSS"])])
    events = []
    missing = {"missing_regime": 0, "missing_atr": 0, "censored_horizon": 0}
    for row, item in frame.iterrows():
        direction = event_direction(item["crossover"])
        if direction is None:
            continue
        if pd.isna(item["regime_v1"]):
            missing["missing_regime"] += 1
            continue
        if pd.isna(item["atr"]) or float(item["atr"]) <= 0:
            missing["missing_atr"] += 1
            continue
        complete_horizon = row + horizon < len(frame)
        if not complete_horizon:
            missing["censored_horizon"] += 1
        events.append({
            "event_id": f"MACD-X-{row:04d}",
            "row": int(row),
            "timestamp": item["bar_time_utc"].isoformat(),
            "direction": direction,
            "regime_v1": item["regime_v1"],
            "period_bucket": item["period_bucket"],
            "complete_horizon": complete_horizon,
        })

    control_rows = [
        int(row) for row, item in frame.iterrows()
        if row not in crossover_rows
        and item["crossover"] != "UNAVAILABLE"
        and pd.notna(item["regime_v1"])
        and pd.notna(item["atr"])
        and float(item["atr"]) > 0
        and row + horizon < len(frame)
    ]
    return events, control_rows, missing


def run_outcome_blind_matching(prereg: dict, frame: pd.DataFrame, events: list[dict], control_rows: list[int]):
    engine_dir = ROOT / "server/research_scripts/phase7/engine"
    sys.path.insert(0, str(engine_dir))
    try:
        from baseline_engine_v4 import BaselineEngineV4
    finally:
        sys.path.pop(0)

    baseline = prereg["baseline"]
    engine = BaselineEngineV4(
        match_dimensions=baseline["match_dimensions"],
        k=baseline["controls_per_event_k"],
        split_boundaries=split_boundaries(prereg),
        minimum_control_count=baseline["minimum_control_pool_after_filters"],
        max_control_reuse_per_run=baseline["max_control_reuse_per_run"],
        feature_version="MACD_CONTEXTUAL_PHASE1_FOUNDATION_V1",
    )
    discovery_features = {
        row: {"regime_v1": frame.at[row, "regime_v1"], "period_bucket": frame.at[row, "period_bucket"]}
        for row in control_rows if row < prereg["split_boundaries"]["discovery_rows"][1]
    }
    engine.fit_normalization(discovery_features)

    control_ids = [f"C{row:04d}:{direction}" for row in control_rows for direction in ("BUY", "SELL")]
    row_by_id = {f"C{row:04d}:{direction}": row for row in control_rows for direction in ("BUY", "SELL")}
    direction_by_id = {f"C{row:04d}:{direction}": direction for row in control_rows for direction in ("BUY", "SELL")}
    features_by_id = {
        f"C{row:04d}:{direction}": {
            "regime_v1": frame.at[row, "regime_v1"],
            "period_bucket": frame.at[row, "period_bucket"],
        }
        for row in control_rows for direction in ("BUY", "SELL")
    }

    results = []
    for event in sorted(events, key=lambda item: (item["row"], item["event_id"])):
        if not event["complete_horizon"]:
            results.append({
                "event_id": event["event_id"], "event_row": event["row"],
                "status": "CENSORED_HORIZON", "matches": [],
                "controls_available": 0, "controls_used": 0,
            })
            continue
        match = engine.match(
            event_id=event["event_id"],
            event_row=event["row"],
            event_direction=event["direction"],
            event_features={"regime_v1": event["regime_v1"], "period_bucket": event["period_bucket"]},
            control_pool=control_ids,
            control_row_by_id=row_by_id,
            control_direction_by_id=direction_by_id,
            control_features_by_id=features_by_id,
        )
        results.append({"event_row": event["row"], **match})
    return results, engine.reuse_usage_report()
