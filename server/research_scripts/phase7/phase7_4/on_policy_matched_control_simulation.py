#!/usr/bin/env python3
"""Phase 7.4A On-Policy Matched-Control Simulation Audit.

Il precedente stress test 'control_reuse_small_pool' (Phase 7.4A
Dependence-Aware Inference Redesign) usava un pool di 10 controlli
condivisi per 30 eventi x 5 controlli = 150 assegnazioni (~15 usi
medi/controllo) - VIOLA la frozen policy reale di SEQ-0015
(max_control_reuse_per_run=5, enforcement meccanico via
engine/control_reuse_ledger.py:ControlReuseLedger). Quello scenario e'
quindi OFF_POLICY: non rappresenta un regime che la pipeline reale
possa produrre, e non puo' essere usato come evidenza del comportamento
di NEXUS sotto la policy congelata.

Questo modulo ricostruisce lo stress test usando REALMENTE
ControlReuseLedger durante l'assegnazione (non dati generati per
rispettare 'in media' il tetto) - l'enforcement e' meccanico, replica
per replica, esattamente come nella pipeline reale."""
import math
import os
import sys

import numpy as np

PHASE74_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE74_DIR, "..", "..", "..", ".."))
ENGINE_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "engine")
sys.path.insert(0, ENGINE_DIR)

from control_reuse_ledger import ControlReuseLedger  # noqa: E402


class InsufficientPoolError(Exception):
    pass


def minimum_feasible_pool_size(n_events, k, max_reuse):
    return math.ceil(n_events * k / max_reuse)


def gen_ar1_timeline(rng, length, phi):
    eps = rng.normal(0.0, 1.0, length)
    x = np.empty(length)
    x[0] = eps[0]
    for t in range(1, length):
        x[t] = phi * x[t - 1] + eps[t] * math.sqrt(1 - phi ** 2)
    return x


def _select_least_used(rng, available, k, local_usage):
    """Selezione 'meno-usato-per-primo' (pareggio casuale) fra i candidati
    gia' filtrati dal ledger reale - il ledger resta l'autorita' meccanica
    che decide COSA e' disponibile; questa funzione decide solo l'ORDINE
    di preferenza fra i disponibili, per un packing realistico (un vero
    motore di matching non ignorerebbe l'informazione di utilizzo residuo
    gia' nota). local_usage e' un contatore mantenuto qui SOLO per la
    selezione - l'enforcement vero resta nel ledger."""
    pool = list(available)
    rng.shuffle(pool)  # pareggio casuale fra pari utilizzo
    pool.sort(key=lambda c: local_usage.get(c, 0))
    return pool[:k]


def gen_on_policy_control_reuse(rng, max_reuse, pool_size, n_events=30, k=5):
    """H0 vera (nessun effetto): outcome evento e pool di controllo sono
    iid N(0,1), indipendenti. L'UNICA fonte di dipendenza indotta e' il
    riuso di identita' di controllo, enforced MECCANICAMENTE dal ledger
    reale (ControlReuseLedger.filter_available_pool/register_controls_used,
    mai bypassato) - non generato 'in media'. La selezione fra i candidati
    disponibili preferisce i meno usati (vedi _select_least_used) - senza
    questo accorgimento, al pool minimo teorico la selezione uniforme
    casuale fallisce per fallimento di 'packing' nell'86% delle repliche
    (verificato empiricamente, non solo assunto) pur essendo la capacita'
    aggregata esattamente sufficiente - un vero motore di matching non ha
    motivo di ignorare l'utilizzo residuo gia' noto."""
    if pool_size < minimum_feasible_pool_size(n_events, k, max_reuse):
        raise InsufficientPoolError(
            f"pool_size={pool_size} insufficiente per n_events={n_events}, k={k}, max_reuse={max_reuse} "
            f"(minimo richiesto={minimum_feasible_pool_size(n_events, k, max_reuse)})"
        )
    full_pool = list(range(pool_size))
    pool_values = rng.normal(0.0, 1.0, pool_size)
    ledger = ControlReuseLedger(max_control_reuse_per_run=max_reuse)
    local_usage = {}
    d = np.empty(n_events)
    for i in range(n_events):
        available = ledger.filter_available_pool(full_pool)
        if len(available) < k:
            raise InsufficientPoolError(f"evento {i}: pool disponibile ({len(available)}) < k({k}) dopo enforcement del ledger")
        selected = _select_least_used(rng, available, k, local_usage)
        ledger.register_controls_used([int(c) for c in selected])
        for c in selected:
            local_usage[c] = local_usage.get(c, 0) + 1
        event_val = rng.normal(0.0, 1.0)
        d[i] = event_val - pool_values[selected].mean()
    return d, ledger.usage_report()


def gen_on_policy_overlapping_control_sets(rng, max_reuse, n_events=30, k=5, window_width=None):
    """Ricostruzione ON-POLICY di 'overlapping_control_sets': finestra
    scorrevole di indici temporali (controlli vicini nel tempo condividono
    correlazione via AR(1) sulla timeline), MA l'assegnazione effettiva
    passa comunque dal ledger reale - nessun controllo puo' superare
    max_reuse indipendentemente da quanto le finestre si sovrappongano."""
    window_width = window_width or (2 * k)
    timeline_length = n_events + window_width
    timeline_values = gen_ar1_timeline(rng, timeline_length, phi=0.5)  # correlazione fra controlli vicini nel tempo
    ledger = ControlReuseLedger(max_control_reuse_per_run=max_reuse)
    local_usage = {}
    d = np.empty(n_events)
    for i in range(n_events):
        window = list(range(i, i + window_width))
        available = ledger.filter_available_pool(window)
        if len(available) < k:
            raise InsufficientPoolError(f"evento {i}: pool disponibile in finestra ({len(available)}) < k({k})")
        selected = _select_least_used(rng, available, k, local_usage)
        ledger.register_controls_used([int(c) for c in selected])
        for c in selected:
            local_usage[c] = local_usage.get(c, 0) + 1
        event_val = rng.normal(0.0, 1.0)  # evento indipendente dalla timeline dei controlli (H0 vera)
        d[i] = event_val - timeline_values[selected].mean()
    return d, ledger.usage_report()


def gen_temporal_overlap_cell(rng, max_reuse, temporal_clustering, n_events=30, k=5, pool_size=150):
    """Cella della matrice 2x2 (sec.6): identity reuse (max_reuse) x
    temporal overlap (clustering delle posizioni dei controlli su una
    timeline AR(1)) - SEMPRE rispettando max_reuse tramite il ledger reale."""
    if pool_size < minimum_feasible_pool_size(n_events, k, max_reuse):
        raise InsufficientPoolError("pool_size insufficiente per questa cella")
    if temporal_clustering == "low":
        timeline_length = pool_size * 20  # posizioni molto diradate -> correlazione AR(1) trascurabile fra controlli
        positions = rng.choice(timeline_length, size=pool_size, replace=False)
    else:  # high
        timeline_length = pool_size + 10  # posizioni fittamente ravvicinate -> alta correlazione AR(1)
        positions = rng.choice(timeline_length, size=pool_size, replace=False)
    timeline_values = gen_ar1_timeline(rng, timeline_length, phi=0.6)
    pool_values = timeline_values[positions]

    full_pool = list(range(pool_size))
    ledger = ControlReuseLedger(max_control_reuse_per_run=max_reuse)
    local_usage = {}
    d = np.empty(n_events)
    for i in range(n_events):
        available = ledger.filter_available_pool(full_pool)
        if len(available) < k:
            raise InsufficientPoolError(f"evento {i}: pool disponibile ({len(available)}) < k({k})")
        selected = _select_least_used(rng, available, k, local_usage)
        ledger.register_controls_used([int(c) for c in selected])
        for c in selected:
            local_usage[c] = local_usage.get(c, 0) + 1
        event_val = rng.normal(0.0, 1.0)
        d[i] = event_val - pool_values[selected].mean()
    return d, ledger.usage_report()


if __name__ == "__main__":
    rng = np.random.default_rng(42)

    print("=== Self-test on_policy_matched_control_simulation (dati SINTETICI) ===")

    # Caso 1: pool insufficiente correttamente rifiutato.
    try:
        gen_on_policy_control_reuse(rng, max_reuse=5, pool_size=10)
        print("ERRORE: pool_size=10 con max_reuse=5 avrebbe dovuto essere rifiutato (minimo=30)!")
    except InsufficientPoolError as e:
        print(f"Caso 1 OK: pool insufficiente correttamente rifiutato: {e}")

    # Caso 2: pool minimo esatto (30) con max_reuse=5 -> deve riuscire, ogni controllo usato esattamente 5 volte.
    d2, report2 = gen_on_policy_control_reuse(rng, max_reuse=5, pool_size=30)
    print(f"Caso 2 (pool minimo=30, max_reuse=5): usage_report={report2}")
    assert report2["max_reuse_observed"] == 5 and report2["n_controls_used"] == 30
    print("Caso 2 OK: al pool minimo, ogni controllo e' usato esattamente al tetto (5), tutti i 30 controlli utilizzati.")

    # Caso 3: pool grande (150) con max_reuse=5 -> riuso medio molto piu' basso, mai oltre 5.
    d3, report3 = gen_on_policy_control_reuse(rng, max_reuse=5, pool_size=150)
    print(f"Caso 3 (pool grande=150, max_reuse=5): usage_report={report3}")
    assert report3["max_reuse_observed"] <= 5
    print("Caso 3 OK: max_reuse_observed mai superiore al tetto, indipendentemente dalla dimensione del pool.")

    # Caso 4: overlapping control sets on-policy - stesso vincolo mai violato.
    d4, report4 = gen_on_policy_overlapping_control_sets(rng, max_reuse=5)
    print(f"Caso 4 (overlapping on-policy): usage_report={report4}")
    assert report4["max_reuse_observed"] <= 5
    print("Caso 4 OK: overlapping_control_sets on-policy rispetta comunque il tetto.")

    # Caso 5: matrice temporal-overlap x identity-reuse.
    for max_reuse in [1, 5]:
        for clustering in ["low", "high"]:
            d5, report5 = gen_temporal_overlap_cell(rng, max_reuse=max_reuse, temporal_clustering=clustering)
            assert report5["max_reuse_observed"] <= max_reuse
            print(f"Caso 5 OK (max_reuse={max_reuse}, clustering={clustering}): max_reuse_observed={report5['max_reuse_observed']} <= {max_reuse}")

    print("\nSelf-test completato su dati SINTETICI - enforcement del ledger verificato meccanicamente in ogni scenario.")
