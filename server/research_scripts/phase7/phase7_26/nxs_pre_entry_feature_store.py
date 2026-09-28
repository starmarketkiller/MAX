#!/usr/bin/env python3
"""Phase 7.26.G - PRE_ENTRY_FEATURE_STORE_V1. Ogni feature porta la
propria provenance temporale esplicita - il verificatore RIFIUTA
qualunque feature la cui availability_time sia successiva al
decision_timestamp (leakage strutturale, non solo statistico)."""
from datetime import datetime

FEATURE_REQUIRED_FIELDS = ["value", "source", "timestamp", "availability_time", "timeframe",
                          "forming_or_closed_bar", "causal_verified", "fidelity"]

ALLOWED_FORMING_OR_CLOSED = {"FORMING", "CLOSED"}
ALLOWED_FIDELITY = {"EVENT_LEVEL_FAITHFUL", "PARTIAL_STRUCTURAL_MODEL", "APPROXIMATE", "UNKNOWN"}


class FeatureLeakageError(Exception):
    pass


def make_feature(value, source, timestamp, availability_time, timeframe,
                 forming_or_closed_bar, fidelity, decision_timestamp):
    """Costruisce un record feature e verifica la causalita' SUBITO
    (fail-closed): se availability_time > decision_timestamp, solleva
    invece di salvare un record silenziosamente contaminato."""
    if forming_or_closed_bar not in ALLOWED_FORMING_OR_CLOSED:
        raise ValueError(f"forming_or_closed_bar non valido: {forming_or_closed_bar}")
    if fidelity not in ALLOWED_FIDELITY:
        raise ValueError(f"fidelity non valida: {fidelity}")
    causal_ok = availability_time <= decision_timestamp
    if not causal_ok:
        raise FeatureLeakageError(
            f"feature '{source}' disponibile solo dopo il timestamp di decisione "
            f"({availability_time} > {decision_timestamp}) - RIFIUTATA, non salvata.")
    return {
        "value": value, "source": source,
        "timestamp": timestamp.isoformat() if isinstance(timestamp, datetime) else timestamp,
        "availability_time": availability_time.isoformat()
                            if isinstance(availability_time, datetime) else availability_time,
        "timeframe": timeframe, "forming_or_closed_bar": forming_or_closed_bar,
        "causal_verified": True, "fidelity": fidelity,
    }


def verify_feature_set_causal(features: list, decision_timestamp) -> list:
    """Verifica indipendente (non fidata dal solo flag causal_verified
    gia' settato in fase di costruzione) - ricontrolla ogni record
    contro il decision_timestamp fornito. Ritorna la lista di errori
    (vuota se tutto ok) - usata dal verificatore globale."""
    errors = []
    for f in features:
        missing = [k for k in FEATURE_REQUIRED_FIELDS if k not in f]
        if missing:
            errors.append(f"feature '{f.get('source', '?')}' manca campi: {missing}")
            continue
        avail = f["availability_time"]
        dec = decision_timestamp.isoformat() if isinstance(decision_timestamp, datetime) else decision_timestamp
        if isinstance(avail, str) and isinstance(dec, str) and avail > dec:
            errors.append(f"feature '{f['source']}' disponibile dopo la decisione "
                         f"({avail} > {dec}) - LEAKAGE non filtrato")
        if f.get("causal_verified") is not True:
            errors.append(f"feature '{f['source']}' non ha causal_verified=True")
    return errors
