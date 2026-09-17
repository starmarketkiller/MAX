#!/usr/bin/env python3
"""Phase 5.5 sec.3 - Multiple Testing Ledger.

Conta ESATTAMENTE quante ipotesi/metriche/subgroup/periodi/varianti sono
stati testati in Phase 5.F-J, calcola un p-value grezzo (two-proportion
z-test) per ogni confronto evento-vs-baseline disponibile, e applica la
correzione Benjamini-Hochberg per FDR SEPARATAMENTE per famiglia di test
comparabili (non tutto in un unico pool, per non confondere test
confirmatori con test esplorativi di sottogruppo).

Famiglie dichiarate:
- FAMILY_DISCOVERY: le 14 ipotesi (9 evento + 5 interazione), fase discovery
- FAMILY_VALIDATION: le stesse 14, fase validation (il test piu' rilevante
  per una conclusione, essendo out-of-sample)
- FAMILY_SUBGROUP_DIRECTION: le 14 ipotesi x (BUY,SELL) = fino a 28 test
- FAMILY_SUBGROUP_YEAR: le 14 ipotesi x anno (fino a 4) = fino a 56 test

QUESTO NON SOSTITUISCE la validazione indipendente - e' un guardrail
aggiuntivo (dichiarato esplicitamente, vedi report). Un'ipotesi con
p-value aggiustato significativo ma senza validazione indipendente vera
resta comunque POST_HOC_CANDIDATE, non SUPPORTED.
"""
import json
import math
import os

from scipy import stats

ROOT = r"C:\Users\User\ClaudeWork\MAX"
EDGE_RESULTS = os.path.join(ROOT, "server", "research_scripts", "phase5", "data", "edge_results_v1.json")
OUT_JSON = os.path.join(ROOT, "server", "research_scripts", "phase5_5", "multiple_testing_ledger_v1.json")


def two_proportion_p(w1, n1, w2, n2):
    if n1 == 0 or n2 == 0:
        return None
    p1, p2 = w1 / n1, w2 / n2
    p_pool = (w1 + w2) / (n1 + n2)
    se = math.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    if se == 0:
        return None
    z = (p1 - p2) / se
    return float(2 * stats.norm.sf(abs(z)))  # two-sided


def benjamini_hochberg(pvals_with_ids, q=0.10):
    """pvals_with_ids: list of (id, p). Ritorna dict id->{'p':p,'rank':r,
    'bh_critical':crit,'adjusted_p':adj,'significant_at_q':bool}."""
    valid = [(i, p) for i, p in pvals_with_ids if p is not None]
    m = len(valid)
    if m == 0:
        return {}
    valid_sorted = sorted(valid, key=lambda x: x[1])
    out = {}
    # adjusted p-values (Benjamini-Hochberg step-up), monotone from the top
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
        crit = (rank / m) * q
        if p <= crit:
            max_sig_rank = rank
    for k, (i, p) in enumerate(valid_sorted):
        rank = k + 1
        out[i] = {
            "raw_p": p, "rank": rank, "m_family": m,
            "bh_critical_value_q": (rank / m) * q,
            "adjusted_p_bh": adj[k],
            "significant_at_q": rank <= max_sig_rank,
        }
    return out


def main():
    edge = json.load(open(EDGE_RESULTS, encoding="utf-8"))
    all_hyps = {}
    all_hyps.update(edge["event_alone"])
    all_hyps.update(edge["interactions"])

    families = {"FAMILY_DISCOVERY": [], "FAMILY_VALIDATION": [],
                "FAMILY_SUBGROUP_DIRECTION": [], "FAMILY_SUBGROUP_YEAR": []}
    n_metrics_per_hyp = {}

    for hid, res in all_hyps.items():
        n_metrics = 0
        if "discovery" in res and res["discovery"].get("event", {}).get("n"):
            e, b = res["discovery"]["event"], res["discovery"]["baseline"]
            p = two_proportion_p(e["wins"], e["n"], b["wins"], b["n"])
            families["FAMILY_DISCOVERY"].append((hid, p))
            n_metrics += 1
        if "validation" in res and res["validation"].get("event", {}).get("n"):
            e, b = res["validation"]["event"], res["validation"]["baseline"]
            p = two_proportion_p(e["wins"], e["n"], b["wins"], b["n"])
            families["FAMILY_VALIDATION"].append((hid, p))
            n_metrics += 1
        for side in ("buy", "sell"):
            r = res.get(side)
            if r and r.get("event", {}).get("n"):
                e, b = r["event"], r["baseline"]
                p = two_proportion_p(e["wins"], e["n"], b["wins"], b["n"])
                families["FAMILY_SUBGROUP_DIRECTION"].append((f"{hid}__{side}", p))
                n_metrics += 1
        for yr, r in res.get("by_year", {}).items():
            if isinstance(r, dict) and r.get("event", {}).get("n"):
                e, b = r["event"], r["baseline"]
                p = two_proportion_p(e["wins"], e["n"], b["wins"], b["n"])
                families["FAMILY_SUBGROUP_YEAR"].append((f"{hid}__{yr}", p))
                n_metrics += 1
        n_metrics_per_hyp[hid] = n_metrics

    bh_results = {}
    for fam_name, pairs in families.items():
        bh_results[fam_name] = benjamini_hochberg(pairs, q=0.10)

    ledger = {
        "schema_version": 1,
        "n_hypotheses_tested": len(all_hyps),
        "n_metrics_per_hypothesis": n_metrics_per_hyp,
        "n_total_statistical_comparisons": sum(len(v) for v in families.values()),
        "n_subgroup_direction_tests": len(families["FAMILY_SUBGROUP_DIRECTION"]),
        "n_subgroup_year_tests": len(families["FAMILY_SUBGROUP_YEAR"]),
        "n_variants_interactions_predefinite": 5,
        "pre_registered_analyses": [
            "9 event-alone detectors (ex-ante, sec.C Phase5)",
            "5 interazioni predefinite (ex-ante, sec.F Phase5)",
            "soglia primaria di classificazione 1.0xATR (ex-ante)",
            "split 70/30 discovery/validation (ex-ante, dichiarato prima di ogni risultato)",
        ],
        "added_after_seeing_data": [
            "la PROMOZIONE di RECLAIM a headline/EDGE_COMPONENT (post_hoc_selection_from_batch=true nel Hypothesis Registry, sec.1)",
            "la lettura qualitativa 'SWEEP+RECLAIM' come narrativa (SWEEP e RECLAIM erano gia' 2 dei 14 test pre-registrati, ma la LORO RELAZIONE come 'storia' e' stata notata dopo, non ipotizzata prima)",
        ],
        "benjamini_hochberg_q": 0.10,
        "families": bh_results,
        "reclaim_discovery_and_validation_pvalues": {
            "discovery_raw_p": dict(families["FAMILY_DISCOVERY"]).get("RECLAIM"),
            "validation_raw_p": dict(families["FAMILY_VALIDATION"]).get("RECLAIM"),
            "discovery_bh": bh_results["FAMILY_DISCOVERY"].get("RECLAIM"),
            "validation_bh": bh_results["FAMILY_VALIDATION"].get("RECLAIM"),
        },
        "guardrail_statement": (
            "Questo ledger e' un controllo AGGIUNTIVO, non un sostituto della "
            "validazione indipendente. Un'ipotesi con adjusted_p significativo "
            "ma proveniente da un dataset di scoperta/selezione post-hoc resta "
            "POST_HOC_CANDIDATE finche' non superi una validazione indipendente "
            "vera (vedi Independent Validation Integrity, sec.4)."
        ),
    }
    json.dump(ledger, open(OUT_JSON, "w", encoding="utf-8"), indent=2, default=str)
    print(json.dumps({k: v for k, v in ledger.items() if k not in ("families",)}, indent=2, default=str))
    print()
    print("RECLAIM p-values:", json.dumps(ledger["reclaim_discovery_and_validation_pvalues"], indent=2))
    print(f"\nwritten: {OUT_JSON}")


if __name__ == "__main__":
    main()
