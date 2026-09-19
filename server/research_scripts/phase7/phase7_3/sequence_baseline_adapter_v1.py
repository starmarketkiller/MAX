#!/usr/bin/env python3
"""Phase 7.3 sec.6 - Sequence Baseline Adapter: collega i sequence_event
del Sequence Discovery Engine a BaselineEngineV4 (Phase 7.0B, REALE,
non reimplementata qui). Nessun pacchetto fisso di dimensioni di
matching - ogni sequence family dichiara le proprie match_dimensions nel
proprio frozen spec (baseline_match_dimensions), mai ereditate
automaticamente da H006/Phase 7.1."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7", "engine"))
from baseline_engine_v4 import BaselineEngineV4, FitIsolationViolation, build_quality_report  # noqa: E402
from cross_split_safety import assign_split, CrossSplitViolation  # noqa: E402


class SequenceBaselineAdapter:
    """Wrapper sottile - non duplica la logica di BaselineEngineV4, la
    adatta all'interfaccia sequence_event/state_snapshot del Sequence
    Discovery Engine."""

    def __init__(self, match_dimensions: list, k: int, split_boundaries: dict,
                 discovery_split_name: str = "discovery", feature_version: str = "feature_registry_v2"):
        if not match_dimensions:
            raise ValueError("match_dimensions deve essere dichiarato esplicitamente dalla sequence family - "
                              "nessun default implicito ammesso (sec.6: 'non usare un pacchetto fisso').")
        self.engine = BaselineEngineV4(match_dimensions=match_dimensions, k=k, split_boundaries=split_boundaries,
                                        discovery_split_name=discovery_split_name, feature_version=feature_version)
        self.split_boundaries = split_boundaries
        self.match_dimensions = match_dimensions

    def fit_on_discovery_only(self, discovery_state_snapshots_by_row: dict):
        """discovery_state_snapshots_by_row: {row_index: state_snapshot} -
        SOLO righe del discovery split. Solleva FitIsolationViolation se
        una riga fuori discovery viene passata (enforcement gia' in
        BaselineEngineV4, riusato qui, non riscritto)."""
        numeric_feats = {row: {k: v for k, v in snap.items() if isinstance(v, (int, float))}
                          for row, snap in discovery_state_snapshots_by_row.items()}
        return self.engine.fit_normalization(numeric_feats)

    def match_sequence_event(self, sequence_event: dict, control_pool_same_split: list,
                              control_row_by_id: dict, control_features_by_id: dict):
        """Il pool di controllo DEVE essere gia' filtrato allo stesso split
        dell'evento dal chiamante (episode/discovery pipeline) - questo
        metodo comunque ri-verifica via BaselineEngineV4.match() (difesa in
        profondita', cross_split_safety chiamata internamente)."""
        direction = sequence_event["direction"]
        control_direction_by_id = {cid: direction for cid in control_pool_same_split}  # ipotetico, vedi baseline_contract_v4
        return self.engine.match(
            event_id=sequence_event["sequence_event_id"], event_row=sequence_event["event_a_index"],
            event_direction=direction, event_features=sequence_event["state_snapshot"],
            control_pool=control_pool_same_split, control_row_by_id=control_row_by_id,
            control_direction_by_id=control_direction_by_id, control_features_by_id=control_features_by_id,
        )

    def audit_report(self, match_results: list):
        return build_quality_report(match_results)


if __name__ == "__main__":
    # Demo sintetica (nessun dato NEXUS) - dimostra il ciclo fit-discovery-only -> match -> audit.
    boundaries = {"discovery": (0, 200), "internal_validation": (200, 280),
                  "locked_validation": (280, 360), "final_holdout": (360, 440)}
    adapter = SequenceBaselineAdapter(match_dimensions=["volatility_state"], k=5, split_boundaries=boundaries)

    discovery_snapshots = {i: {"volatility_state": "HIGH" if i % 2 == 0 else "LOW"} for i in range(0, 200, 2)}
    adapter.fit_on_discovery_only(discovery_snapshots)
    print("fit_on_discovery_only: OK")

    # Test negativo: fit su riga fuori discovery -> FitIsolationViolation (riusata da BaselineEngineV4).
    try:
        adapter.fit_on_discovery_only({250: {"volatility_state": "HIGH"}})
        print("ERRORE: fit su non-discovery avrebbe dovuto fallire!")
    except FitIsolationViolation:
        print("Fit isolation (riusata da BaselineEngineV4) correttamente applicata dall'adapter.")

    control_pool = list(range(0, 40, 2))
    seq_event = {"sequence_event_id": "DEMO-EVT-1", "event_a_index": 10, "direction": "BUY",
                 "state_snapshot": {"volatility_state": "HIGH"}}
    control_row_by_id = {c: c for c in control_pool}
    control_features_by_id = {c: {"volatility_state": "HIGH"} for c in control_pool}
    result = adapter.match_sequence_event(seq_event, control_pool, control_row_by_id, control_features_by_id)
    print("match_sequence_event:", result["status"], "controls_used=", result["controls_used"])
    assert result["status"] in ("MATCHED", "MATCHED_K_SHORTFALL")

    report = adapter.audit_report([result])
    print("audit_report:", report["match_quality_counts"])
    print("\nSequenceBaselineAdapter verificato (nessuna logica di matching duplicata, solo adattamento).")
