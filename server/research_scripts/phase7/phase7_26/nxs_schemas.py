#!/usr/bin/env python3
"""Phase 7.26 - schemi condivisi (campi richiesti + enum di lifecycle)
per tutti i registry della Safety Net. Un campo mancante nel backfill
e' sempre None/'NOT_AVAILABLE' esplicito, mai inventato - i builder di
questa fase leggono SOLO da artifact gia' esistenti (Phase 7.9x-7.25),
mai da assunzioni nuove sulla strategia."""

DATA_EXPOSURE_REQUIRED_FIELDS = [
    "dataset_id", "symbol", "timeframe", "date_range", "strategy_identity",
    "implementation_identity", "experiment_run_ids", "first_seen_date",
    "development_exposure", "integrity_audit_exposure", "mechanism_discovery_exposure",
    "visual_review_exposure", "optimization_exposure", "validation_exposure",
    "oos_exposure", "forward_exposure", "holdout_status",
]

EXPERIMENT_REQUIRED_FIELDS = [
    "experiment_id", "hypothesis_id", "strategy_identity", "implementation_identity",
    "run_id", "dataset_id", "code_sha", "config_hash", "period", "method", "metrics",
    "artifacts", "verdict", "confidence", "limitations", "created_at",
]

HYPOTHESIS_LIFECYCLE_STATES = [
    "OBSERVATION", "HYPOTHESIS", "PREREGISTERED", "TESTING", "SUPPORTED", "REJECTED",
    "INCONCLUSIVE",
]

HYPOTHESIS_REQUIRED_FIELDS = [
    "hypothesis_id", "statement", "lifecycle_state", "discovery_dataset_id",
    "validation_dataset_ids", "originating_strategies", "evidence_level",
]

LEARNING_PACKET_REQUIRED_FIELDS = [
    "strategy_identity", "mechanism", "pre_entry_context", "regime", "direction",
    "volatility", "trend", "structure", "session", "level_context", "winner_anatomy",
    "loser_anatomy", "mfe_mae", "time_to_mfe_mae", "favorable_before_loss",
    "adverse_before_win", "execution_degradation", "cost_sensitivity", "exit_efficiency",
    "capital_efficiency", "concentration", "temporal_concentration", "oos_behavior",
    "failure_modes", "observations", "candidate_hypotheses", "confidence", "fidelity",
    "provenance",
]

FAILURE_MODE_TAXONOMY = [
    "NO_SIGNAL_INFORMATION", "WRONG_DIRECTION", "POOR_ENTRY_TIMING", "STOP_BEFORE_MOVE",
    "INSUFFICIENT_FOLLOW_THROUGH", "EXIT_TOO_EARLY", "EXIT_TOO_LATE", "REGIME_DEPENDENT",
    "DIRECTION_DEPENDENT", "OUTLIER_DEPENDENT", "TEMPORALLY_CONCENTRATED", "COST_DESTROYED",
    "EXECUTION_DESTROYED", "LOW_SAMPLE", "OOS_DEGRADATION", "IMPLEMENTATION_DEFECT",
    "DATA_QUALITY", "UNKNOWN",
]

SYNTHESIS_ALLOWED_VERDICTS = ["OBSERVATION", "CROSS_STRATEGY_PATTERN", "CANDIDATE_HYPOTHESIS"]

PRE_ENTRY_FEATURE_REQUIRED_FIELDS = [
    "value", "source", "timestamp", "availability_time", "timeframe",
    "forming_or_closed_bar", "causal_verified", "fidelity",
]

STRATEGIES_BACKFILLED_V1 = ["BREAKOUT_ACC", "ORDER_BLOCK", "TSI", "LIQ_SWEEP"]

NOT_AVAILABLE = "NOT_AVAILABLE"  # placeholder esplicito per un campo mai calcolato in nessuna
                                # fase precedente - mai una ricostruzione inventata


def missing_required(payload: dict, required: list) -> list:
    return [f for f in required if f not in payload]
