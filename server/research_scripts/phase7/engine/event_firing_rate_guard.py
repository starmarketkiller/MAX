#!/usr/bin/env python3
"""Phase 7.0B sec.4-5 - Event Firing Rate Guard. Gap gia' osservato
storicamente (PULLBACK, Phase 5.5: 83% delle barre, risultati NO_EDGE
non informativi ma dall'aspetto di un test valido - vedi
failure_memory_registry_v1.json FAIL-004). Questo modulo lo rende un
check MECCANICO invece di un'osservazione retroattiva.

Nessuna metrica di outcome/edge viene calcolata qui - solo proprieta'
STRUTTURALI del detector (quante barre attiva, quanto sono clusterizzati
gli eventi nel tempo) - conforme a sec.19 (no edge evaluation) di
Phase 7.0B.
"""
import statistics

# POLICY_THRESHOLD - non derivati da una formula statistica, scelti per
# separare "evento raro/informativo" da "il detector si attiva su quasi
# tutto il dataset" (rationale: un detector che spara su >40% delle
# barre non seleziona piu' un sottoinsieme interessante da confrontare
# con un baseline - il confronto diventa essenzialmente il dataset con
# se stesso, come gia' osservato con PULLBACK).
FIRING_RATE_THRESHOLDS = {
    "SPARSE_MAX": 0.02,
    "NORMAL_MAX": 0.15,
    "HIGH_MAX": 0.40,
}


class DetectorNotAllowedForDiscovery(Exception):
    pass


def assert_allowed_for_discovery(health_record: dict):
    """Enforcement REALE (non solo un flag descrittivo in un JSON) - una
    futura discovery run che tenti di usare un detector PATHOLOGICAL deve
    passare da qui e ricevere un rifiuto, non un'ispezione manuale del
    campo allowed_for_discovery."""
    if not health_record.get("allowed_for_discovery", False):
        raise DetectorNotAllowedForDiscovery(
            f"Detector '{health_record.get('event_family')}' non ammesso per discovery: "
            f"status={health_record.get('status')} - {health_record.get('reason')}"
        )


def classify_firing_rate(firing_rate: float) -> str:
    if firing_rate < FIRING_RATE_THRESHOLDS["SPARSE_MAX"]:
        return "SPARSE"
    if firing_rate < FIRING_RATE_THRESHOLDS["NORMAL_MAX"]:
        return "NORMAL"
    if firing_rate < FIRING_RATE_THRESHOLDS["HIGH_MAX"]:
        return "HIGH"
    return "PATHOLOGICAL"


def compute_firing_stats(n_bars: int, event_row_indices: list, cluster_gap_threshold: int = 10) -> dict:
    n_events = len(event_row_indices)
    firing_rate = n_events / n_bars if n_bars else 0.0
    sorted_idx = sorted(set(event_row_indices))
    gaps = [sorted_idx[i + 1] - sorted_idx[i] for i in range(len(sorted_idx) - 1)]
    median_gap = statistics.median(gaps) if gaps else None
    n_clustered = sum(1 for g in gaps if g <= cluster_gap_threshold)
    clustering_rate = (n_clustered / len(gaps)) if gaps else 0.0
    return {
        "n_bars": n_bars, "n_events": n_events, "firing_rate": firing_rate,
        "median_gap_bars": median_gap, "clustering_rate": clustering_rate,
        "cluster_gap_threshold": cluster_gap_threshold,
    }


def build_detector_health(event_family: str, n_bars: int, event_row_indices: list,
                           cluster_gap_threshold: int = 10) -> dict:
    stats = compute_firing_stats(n_bars, event_row_indices, cluster_gap_threshold)
    status = classify_firing_rate(stats["firing_rate"])
    allowed = status != "PATHOLOGICAL"
    if status == "PATHOLOGICAL":
        reason = (f"firing_rate={stats['firing_rate']:.3f} >= {FIRING_RATE_THRESHOLDS['HIGH_MAX']} "
                  f"(soglia PATHOLOGICAL) - il detector si attiva su una quota patologica delle barre, "
                  f"non autorizzato per discovery senza revisione umana esplicita del detector stesso.")
    elif status == "HIGH":
        reason = (f"firing_rate={stats['firing_rate']:.3f} nella fascia HIGH - ammesso per discovery "
                  f"ma segnalato per revisione, non bloccato automaticamente.")
    else:
        reason = f"firing_rate={stats['firing_rate']:.3f} nella fascia {status} - nessuna preoccupazione strutturale."
    return {
        "event_family": event_family,
        "firing_rate": stats["firing_rate"],
        "n_events": stats["n_events"],
        "n_bars": stats["n_bars"],
        "clustering_metrics": {
            "median_gap_bars": stats["median_gap_bars"],
            "clustering_rate": stats["clustering_rate"],
            "cluster_gap_threshold": stats["cluster_gap_threshold"],
        },
        "status": status,
        "allowed_for_discovery": allowed,
        "reason": reason,
    }


if __name__ == "__main__":
    # Demo su dati sintetici (nessun dato di mercato reale) - vedi
    # build_event_detector_health_v1.py per l'applicazione ai detector
    # REALI di Phase 5 (solo conteggi/row_index, mai outcome).
    n_bars_demo = 4809

    sparse_rows = list(range(0, n_bars_demo, 500))  # ~10 eventi
    normal_rows = list(range(0, n_bars_demo, 40))  # ~120 eventi
    pathological_rows = list(range(0, n_bars_demo, 1))[: int(n_bars_demo * 0.85)]  # 85% delle barre

    h_sparse = build_detector_health("DEMO_SPARSE", n_bars_demo, sparse_rows)
    h_normal = build_detector_health("DEMO_NORMAL", n_bars_demo, normal_rows)
    h_pathological = build_detector_health("DEMO_PATHOLOGICAL", n_bars_demo, pathological_rows)

    print(f"DEMO_SPARSE: status={h_sparse['status']} allowed={h_sparse['allowed_for_discovery']}")
    print(f"DEMO_NORMAL: status={h_normal['status']} allowed={h_normal['allowed_for_discovery']}")
    print(f"DEMO_PATHOLOGICAL: status={h_pathological['status']} allowed={h_pathological['allowed_for_discovery']}")

    assert h_sparse["status"] == "SPARSE"
    assert h_normal["status"] == "NORMAL"
    assert h_pathological["status"] == "PATHOLOGICAL"
    assert h_pathological["allowed_for_discovery"] is False
    assert h_sparse["allowed_for_discovery"] is True and h_normal["allowed_for_discovery"] is True
    print("\nTutte le classificazioni attese verificate (incluso il blocco del caso patologico).")
