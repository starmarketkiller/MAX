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
                 max_control_reuse_per_run: int, discovery_split_name: str = "discovery",
                 feature_version: str = "feature_registry_v2"):
        """max_control_reuse_per_run (Phase 7.4A Baseline Matching Integrity
        Patch) - OBBLIGATORIO, nessun default implicito: ogni NUOVA sequence
        family che usa questo adapter deve dichiararlo esplicitamente nel
        proprio frozen spec, esattamente come match_dimensions - mai
        ereditato silenziosamente."""
        if not match_dimensions:
            raise ValueError("match_dimensions deve essere dichiarato esplicitamente dalla sequence family - "
                              "nessun default implicito ammesso (sec.6: 'non usare un pacchetto fisso').")
        if not max_control_reuse_per_run or max_control_reuse_per_run < 1:
            raise ValueError("max_control_reuse_per_run deve essere dichiarato esplicitamente (>=1) dalla sequence "
                              "family - stesso principio di match_dimensions, nessun default implicito (Phase 7.4A "
                              "Baseline Matching Integrity Patch).")
        self.engine = BaselineEngineV4(match_dimensions=match_dimensions, k=k, split_boundaries=split_boundaries,
                                        discovery_split_name=discovery_split_name, feature_version=feature_version,
                                        max_control_reuse_per_run=max_control_reuse_per_run)
        self.split_boundaries = split_boundaries
        self.match_dimensions = match_dimensions
        self.max_control_reuse_per_run = max_control_reuse_per_run

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
        profondita', cross_split_safety chiamata internamente).

        NOTA SEMANTICA (Phase 7.4A Structural Verdict Semantics Patch,
        2026-09-20 - terminologia, nessuna modifica di comportamento):
        control_direction_by_id assegna a OGNI candidato la STESSA
        direzione dell'evento - questa e' una DIRECTION-CONDITIONED
        COUNTERFACTUAL BASELINE ("valutati come ipotetico BUY/SELL",
        baseline_contract_v4.json:direction_aware.rule), NON la direzione
        osservata indipendentemente della barra di controllo stessa. Il
        controllo risponde alla domanda 'rispetto a una barra nello stesso
        stato, COSA SAREBBE SUCCESSO SE fosse stata negoziata nella stessa
        direzione dell'evento?' - non 'qual era la direzione naturale di
        quella barra?'. Coerente con il contratto v4, verificato
        esplicitamente in questa patch - comportamento invariato."""
        direction = sequence_event["direction"]
        control_direction_by_id = {cid: direction for cid in control_pool_same_split}  # direction-conditioned counterfactual, vedi nota sopra
        return self.engine.match(
            event_id=sequence_event["sequence_event_id"], event_row=sequence_event["event_a_index"],
            event_direction=direction, event_features=sequence_event["state_snapshot"],
            control_pool=control_pool_same_split, control_row_by_id=control_row_by_id,
            control_direction_by_id=control_direction_by_id, control_features_by_id=control_features_by_id,
        )

    def audit_report(self, match_results: list):
        return build_quality_report(match_results)

    def reuse_usage_report(self):
        """Phase 7.4A Baseline Matching Integrity Patch - passthrough al
        report del ledger reale dell'engine sottostante (mai None per una
        sequence family, dato che max_control_reuse_per_run e' obbligatorio)."""
        return self.engine.reuse_usage_report()


if __name__ == "__main__":
    # Demo sintetica (nessun dato NEXUS) - dimostra il ciclo fit-discovery-only -> match -> audit.
    boundaries = {"discovery": (0, 200), "internal_validation": (200, 280),
                  "locked_validation": (280, 360), "final_holdout": (360, 440)}

    # Test negativo: max_control_reuse_per_run non dichiarato -> rifiutato (Phase 7.4A Integrity Patch).
    try:
        SequenceBaselineAdapter(match_dimensions=["volatility_state"], k=5, split_boundaries=boundaries, max_control_reuse_per_run=None)
        print("ERRORE: max_control_reuse_per_run mancante avrebbe dovuto essere rifiutato!")
    except ValueError:
        print("max_control_reuse_per_run mancante correttamente rifiutato (obbligatorio, nessun default implicito).")

    adapter = SequenceBaselineAdapter(match_dimensions=["volatility_state"], k=5, split_boundaries=boundaries,
                                       max_control_reuse_per_run=5)

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

    usage = adapter.reuse_usage_report()
    assert usage is not None and usage["max_reuse_observed"] <= 5
    print(f"reuse_usage_report: {usage} (mai None per una sequence family, tetto rispettato).")

    print("\nSequenceBaselineAdapter verificato (nessuna logica di matching duplicata, solo adattamento; reuse enforcement Phase 7.4A attivo).")
