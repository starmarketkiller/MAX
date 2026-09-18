#!/usr/bin/env python3
"""Phase 7 sec.13 - Multiple Testing Control v2. Generalizza (riusa la
matematica di) server/research_scripts/phase5_5/build_multiple_testing_ledger.py
in una funzione libreria richiamabile per QUALUNQUE famiglia di
confronti futura, con family_id esplicito.

REGOLA DICHIARATA (non negoziabile): FDR correction != independent
validation. Un p-value aggiustato significativo NON promuove da solo
un candidato a PRE_REGISTERED_CANDIDATE/INDEPENDENT_VALIDATION - serve
comunque il passaggio attraverso partition_contract_v2.json (locked
validation / final holdout) prima di qualunque verdetto.
"""
import math

from scipy import stats


def two_proportion_p(w1, n1, w2, n2):
    if n1 == 0 or n2 == 0:
        return None
    p1, p2 = w1 / n1, w2 / n2
    p_pool = (w1 + w2) / (n1 + n2)
    se = math.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    if se == 0:
        return None
    z = (p1 - p2) / se
    return float(2 * stats.norm.sf(abs(z)))


def benjamini_hochberg(pvals_with_ids, q=0.10):
    valid = [(i, p) for i, p in pvals_with_ids if p is not None]
    m = len(valid)
    if m == 0:
        return {}
    valid_sorted = sorted(valid, key=lambda x: x[1])
    adj = [0.0] * m
    prev = 1.0
    for k in range(m - 1, -1, -1):
        rank = k + 1
        _, p = valid_sorted[k]
        val = min(prev, p * m / rank)
        adj[k] = val
        prev = val
    max_sig_rank = 0
    for k, (i, p) in enumerate(valid_sorted):
        rank = k + 1
        if p <= (rank / m) * q:
            max_sig_rank = rank
    out = {}
    for k, (i, p) in enumerate(valid_sorted):
        rank = k + 1
        out[i] = {
            "raw_p": p, "rank": rank, "m_family": m,
            "bh_critical_value_q": (rank / m) * q,
            "adjusted_p_bh": adj[k],
            "significant_at_q": rank <= max_sig_rank,
        }
    return out


def run_family(family_id: str, comparisons: list, q: float = 0.10):
    """comparisons: lista di dict {id, wins_event, n_event, wins_baseline, n_baseline}.
    Ritorna un multiple_testing_report_v2-compatibile per QUESTA famiglia."""
    pvals = []
    for c in comparisons:
        p = two_proportion_p(c["wins_event"], c["n_event"], c["wins_baseline"], c["n_baseline"])
        pvals.append((c["id"], p))
    bh = benjamini_hochberg(pvals, q=q)
    return {
        "family_id": family_id,
        "family_size": len(comparisons),
        "q": q,
        "results": bh,
        "guardrail_statement": (
            "FDR correction != independent validation. Un adjusted_p significativo qui NON "
            "autorizza una transizione di lifecycle oltre INTERNAL_VALIDATION - vedi "
            "candidate_lifecycle.py e partition_contract_v2.json."
        ),
    }


if __name__ == "__main__":
    # Dimostrazione con confronti sintetici (nessun dato di mercato reale)
    demo_family = [
        {"id": "DEMO-A", "wins_event": 62, "n_event": 100, "wins_baseline": 250, "n_baseline": 500},
        {"id": "DEMO-B", "wins_event": 55, "n_event": 100, "wins_baseline": 250, "n_baseline": 500},
        {"id": "DEMO-C", "wins_event": 48, "n_event": 100, "wins_baseline": 250, "n_baseline": 500},
    ]
    report = run_family("DEMO_FAMILY_1", demo_family, q=0.10)
    import json
    print(json.dumps(report, indent=2, default=str))
