#!/usr/bin/env python3
"""Phase 7.9J - punto 3 della revisione: tabella direzione x
allineamento x esito, DOPO la correzione di causalita' (EMA100 regime
di lungo periodo, EMA20 trend locale, entrambi corretti/aggiunti in
Phase 7.9J). Non implementa alcuna nuova ipotesi.
"""
import os
import statistics
import sys

PHASE79J_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE79I_DIR = os.path.abspath(os.path.join(PHASE79J_DIR, "..", "phase7_9i"))
ROOT = os.path.abspath(os.path.join(PHASE79J_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import save_json, wrap_with_provenance  # noqa: E402

sys.path.insert(0, PHASE79I_DIR)
import nxs_mechanism_context as ctx  # noqa: E402


def _stats(values):
    values = [v for v in values if v is not None]
    if not values:
        return {"n": 0}
    out = {"n": len(values), "mean": round(statistics.mean(values), 4),
           "median": round(statistics.median(values), 4)}
    if len(values) > 1:
        out["stdev"] = round(statistics.stdev(values), 4)
    return out


def build():
    feat = ctx.build_feature_table()
    rows = feat["rows"]
    pop_b = [r for r in rows if r["funnel_terminal_stage"] == "OPENED"]

    # --- Verifica di variazione: esiste ANCHE UN SOLO evento (in TUTTI i 75, non solo i
    # 47 OPENED) non allineato, su ciascuno dei due proxy? ---
    n_misaligned_ema100_all75 = sum(1 for r in rows if r["htf_proxy_trend_aligned"] is False)
    n_misaligned_ema20_all75 = sum(1 for r in rows if r["local_trend_aligned"] is False)
    n_with_ema100_data = sum(1 for r in rows if r["htf_proxy_trend_aligned"] is not None)
    n_with_ema20_data = sum(1 for r in rows if r["local_trend_aligned"] is not None)

    # --- Tabella direzione x allineamento (EMA100 regime, EMA20 locale) x esito -
    # su Population B (47 OPENED, unica con esito/path reale). ---
    table = []
    for d in ("BUY", "SELL"):
        grp = [r for r in pop_b if r["direction_label"] == d]
        n_cont = sum(1 for r in grp if r["post_entry_path_anatomy"]
                    and r["post_entry_path_anatomy"]["horizons"].get("fwd_return_60d1_price_units", 0)
                    and r["post_entry_path_anatomy"]["horizons"]["fwd_return_60d1_price_units"] > 0)
        table.append({
            "direction": d, "n": len(grp),
            "n_regime_aligned_ema100": sum(1 for r in grp if r["htf_proxy_trend_aligned"]),
            "n_regime_NOT_aligned_ema100": sum(1 for r in grp if r["htf_proxy_trend_aligned"] is False),
            "n_local_aligned_ema20": sum(1 for r in grp if r["local_trend_aligned"]),
            "n_local_NOT_aligned_ema20": sum(1 for r in grp if r["local_trend_aligned"] is False),
            "n_continuation_60d1": n_cont,
            "pct_continuation": round(100 * n_cont / len(grp), 1) if grp else None,
            "mfe": _stats([r["post_entry_path_anatomy"]["mfe_price_units"] for r in grp
                          if r["post_entry_path_anatomy"]]),
            "mae": _stats([r["post_entry_path_anatomy"]["mae_price_units"] for r in grp
                          if r["post_entry_path_anatomy"]]),
        })

    zero_variation = (n_misaligned_ema100_all75 == 0 and n_misaligned_ema20_all75 == 0)

    confound_discussion = (
        "PROBLEMA STRUTTURALE CONFERMATO: su TUTTI i 75 eventi (non solo i 47 OPENED), "
        f"{n_with_ema100_data - n_misaligned_ema100_all75}/{n_with_ema100_data} sono "
        "allineati al regime EMA100 e "
        f"{n_with_ema20_data - n_misaligned_ema20_all75}/{n_with_ema20_data} al trend "
        "locale EMA20 - CIOE' il 100% su ENTRAMBI i proxy, senza eccezioni, per l'intera "
        "storia 2019-2026 di eventi che hanno superato il gate di Acceptance. Non esiste "
        "un solo evento non-allineato con cui confrontare gli eventi allineati - "
        "l'allineamento di trend e la direzione del segnale sono PERFETTAMENTE CONFUSI "
        "(collineari) in questo campione: non e' possibile, con questi dati, distinguere "
        "se il comportamento favorevole osservato sui BUY dipenda (a) dall'essere "
        "allineati al trend, (b) dall'essere semplicemente BUY in un periodo di mercato "
        "rialzista, o (c) da qualche altra caratteristica correlata a entrambi. "
        "'TREND_PERSISTENCE_DIRECTION_DEPENDENT' (Phase 7.9I) resta un'ETICHETTA "
        "descrittiva plausibile del pattern osservato, non un meccanismo causale isolato "
        "o testato - la distinzione fra 'trend-alignment' e 'direzione BUY in questo "
        "periodo' e' concettualmente diversa ma OSSERVAZIONALMENTE INDISTINGUIBILE qui. "
        "Nota aggiuntiva: l'allineamento al trend LOCALE (EMA20) potrebbe essere "
        "parzialmente TAUTOLOGICO rispetto alla definizione stessa di Acceptance (un "
        "prezzo che rompe un massimo/minimo di 20 barre e' quasi meccanicamente sopra/"
        "sotto la propria media a 20 periodi) - solo l'allineamento EMA100 (orizzonte "
        "indipendente dalla finestra di 20 barre del trigger) e' un test davvero "
        "indipendente, e anche quello risulta 100% allineato senza eccezioni."
    )

    return {
        "phase": "7.9J",
        "population_used": "B_opened (47, per l'esito/path) - il controllo di variazione "
            "dell'allineamento usa TUTTI i 75 eventi (population-agnostic, la feature e' "
            "disponibile per ogni evento con dati di prezzo).",
        "direction_x_alignment_x_outcome_table": table,
        "zero_variation_in_alignment_across_all_75_events": zero_variation,
        "n_misaligned_ema100_regime_all75": n_misaligned_ema100_all75,
        "n_misaligned_ema20_local_all75": n_misaligned_ema20_all75,
        "confound_discussion": confound_discussion,
        "new_hypothesis_not_implemented": True,
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE79J_DIR, "breakout_acc_direction_alignment_outcome_v1.json"), doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print("zero_variation:", payload["zero_variation_in_alignment_across_all_75_events"])
    return doc


if __name__ == "__main__":
    main()
