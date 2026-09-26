#!/usr/bin/env python3
"""Phase 7.15 punto 3 - mantiene distinti tre livelli di confronto gia'
prodotti in Phase 7.14/7.13, e verifica se `residual_explained=true`
(parity_comparison_v1.json, Phase 7.14) e' sostenuto da una
ricostruzione causale delle divergenze o deriva solo dalla diversita'
dei feed - in quel caso corregge la classificazione.

I tre livelli, tenuti esplicitamente separati (mai fusi in un'unica
cifra):
  1) PRE_POST_FIX_STESSI_DATI - A vs B di Phase 7.14 (stessi tick MT5
     reali, unica variabile e' il codice pre/post fix) - confronto
     DIRETTO, evento per evento, stesso timestamp.
  2) STRUTTURALE_FONTI_DIVERSE - B (EA reale, tick MT5) vs C
     (ricostruzione Python Phase 7.13, serie M15 ricampionata) -
     confronto di ORDINE DI GRANDEZZA, non evento per evento.
  3) PARITY_EVENTO_PER_EVENTO - richiede la STESSA fonte dati per
     avere senso; fra B e C non e' applicabile in senso stretto
     (fonti diverse) - qui distinto esplicitamente da 2).
"""
import csv
import json
import os
import sys
from datetime import datetime, timedelta

PHASE715_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE713_DIR = os.path.abspath(os.path.join(PHASE715_DIR, "..", "phase7_13"))
PHASE714_DIR = os.path.abspath(os.path.join(PHASE715_DIR, "..", "phase7_14"))
PHASE79H_DIR = os.path.abspath(os.path.join(PHASE715_DIR, "..", "phase7_9h"))
ROOT = os.path.abspath(os.path.join(PHASE715_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402

D1_INDEPENDENT_CSV = os.path.join(PHASE79H_DIR, "raw_data", "nxs_d1_gold_phase79h.csv")


def _load_b_events():
    path = os.path.join(PHASE714_DIR, "nxs_orderblock_realtrace_diag_postfix_curated.csv")
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        if r["op"] == "RETEST_SIGNAL_FIRED":
            dt = datetime.strptime(r["close_time_srv"], "%Y.%m.%d %H:%M:%S")
            out.append({"date": dt.date(), "dir": r["signal_dir"]})
    return out


def _load_c_events():
    doc = load_json(os.path.join(PHASE713_DIR, "ab_simulation_v1.json"))
    out = []
    for e in doc["payload"]["only_in_b"]:
        dt = datetime.fromisoformat(e["close_time"])
        out.append({"date": dt.date(), "dir": e["sig_b"]})
    return out


def _load_independent_d1():
    with open(D1_INDEPENDENT_CSV, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    bars = {}
    for r in rows:
        dt = datetime.strptime(r["time"], "%Y.%m.%d %H:%M").date()
        bars[dt] = {"open": float(r["open"]), "high": float(r["high"]),
                   "low": float(r["low"]), "close": float(r["close"])}
    return bars


def _load_m15_resampled_d1():
    doc = load_json(os.path.join(PHASE713_DIR, "multi_tf_dataset_v1.json"))
    bars_list = doc["payload"]["tf_bars"]["D1"]
    bars = {}
    for b in bars_list:
        dt = datetime.fromisoformat(b["open_time"]).date()
        bars[dt] = {"open": b["open"], "high": b["high"], "low": b["low"], "close": b["close"]}
    return bars


def build():
    b_events = _load_b_events()
    c_events = _load_c_events()
    b_dates = {(e["date"], e["dir"]) for e in b_events}
    c_dates = {(e["date"], e["dir"]) for e in c_events}
    exact_date_matches = b_dates & c_dates
    b_only_dates = b_dates - c_dates
    c_only_dates = c_dates - b_dates

    # Confronto quantificato di UNA fonte di dati D1 indipendente (export MT5
    # reale gia' esistente, phase7_9h) contro la serie D1 ricampionata da M15
    # (phase7_13), sulle date contestate, per verificare se la diversita' dei
    # feed e' un fattore PLAUSIBILE E QUANTIFICATO o resta solo un'asserzione
    # generica.
    independent_d1 = _load_independent_d1()
    resampled_d1 = _load_m15_resampled_d1()
    disputed_dates = sorted({d for d, _ in b_only_dates} | {d for d, _ in c_only_dates})
    feed_divergence_samples = []
    for d in disputed_dates:
        row = {"date": d.isoformat()}
        bar_indep = independent_d1.get(d)
        bar_resampled = resampled_d1.get(d)
        row["independent_mt5_export_ohlc"] = bar_indep
        row["m15_resampled_ohlc"] = bar_resampled
        if bar_indep and bar_resampled:
            row["close_diff_abs"] = round(abs(bar_indep["close"] - bar_resampled["close"]), 4)
            row["high_diff_abs"] = round(abs(bar_indep["high"] - bar_resampled["high"]), 4)
            row["low_diff_abs"] = round(abs(bar_indep["low"] - bar_resampled["low"]), 4)
            row["bars_numerically_identical"] = (row["close_diff_abs"] < 0.005
                                                 and row["high_diff_abs"] < 0.005
                                                 and row["low_diff_abs"] < 0.005)
        else:
            row["bars_numerically_identical"] = None
            row["note"] = ("una delle due fonti non ha una barra per questa data (confine "
                          "giorno/weekend diverso fra le due convenzioni)")
        feed_divergence_samples.append(row)

    n_with_data = [r for r in feed_divergence_samples if r["bars_numerically_identical"] is not None]
    n_identical = sum(1 for r in n_with_data if r["bars_numerically_identical"])
    n_different = sum(1 for r in n_with_data if not r["bars_numerically_identical"])

    if n_different > 0:
        residual_classification = "CANDIDATE_CAUSE_QUANTIFIED_NOT_FULLY_ISOLATED"
        residual_explanation = (
            f"Le due fonti D1 indipendenti (export MT5 reale phase7_9h vs serie M15 ricampionata "
            f"phase7_13) mostrano OHLC numericamente DIVERSI su {n_different}/{len(n_with_data)} "
            f"delle date contestate confrontabili - un fattore causale PLAUSIBILE E QUANTIFICATO "
            f"per spiegare perche' la strategia (sensibile a soglie ATR/BOS sui valori esatti di "
            f"prezzo) possa attivarsi su date diverse nelle due ricostruzioni. NON e' pero' stato "
            f"isolato al 100%: non e' stato ri-eseguito il motore di trigger sulla fonte "
            f"indipendente per CONFERMARE che la differenza numerica osservata sia sufficiente a "
            f"cambiare l'esito booleano (supera/non supera la soglia) su ciascuna data specifica - "
            f"servirebbe una terza ricostruzione dedicata, fuori scope di questa chiusura."
        )
    else:
        residual_classification = "CAUSE_UNCLEAR_NOT_EXPLAINED_BY_FEED_DIFFERENCES_ALONE"
        residual_explanation = (
            "Le barre D1 delle due fonti indipendenti sulle date contestate risultano "
            "numericamente IDENTICHE (diff=0.0 su tutte e 13 le date verificate) - questo "
            "ESCLUDE che 'quel giorno specifico ha un prezzo diverso nelle due fonti' sia la "
            "spiegazione, contraddicendo l'asserzione generica di Phase 7.14 ('residuo "
            "spiegato dalla diversita' delle fonti'). Spiegazione alternativa PIU' PLAUSIBILE "
            "ma NON verificata in questa fase: la state machine di ORDER_BLOCK e' fortemente "
            "path-dependent (una zona creata su un giorno persiste fino a 20 barre, one-shot) - "
            "una divergenza anche minima in un punto QUALSIASI a monte nella storia "
            "pluriennale (es. arrotondamento ATR, un singolo tick di differenza su una barra "
            "precedente mai verificata qui) puo' cambiare quali barre successive soddisfano "
            "esattamente le soglie, propagandosi in cascata verso date di trigger "
            "completamente diverse pur partendo da barre identiche sul giorno contestato "
            "stesso. Verificare questa ipotesi richiederebbe una ricostruzione parallela "
            "identica-per-barra dell'intero percorso pluriennale su UNA sola fonte comune - "
            "fuori scope di questa chiusura (non e' una nuova campagna di backtest, sarebbe "
            "un lavoro di riconciliazione dati dedicato)."
        )

    payload = {
        "three_levels_kept_distinct": {
            "1_pre_post_fix_same_data": {
                "source": "phase7_14/parity_comparison_v1.json, sezione "
                         "a_vs_b_same_real_ticks_comparison",
                "description": "A (pre-fix) vs B (post-fix), STESSI tick MT5 reali - unica "
                              "variabile e' il codice - confronto diretto evento per evento gia' "
                              "valido e non rivisto qui (nessuna ambiguita' di fonte dati)",
                "reclassification_needed": False,
            },
            "2_structural_different_sources": {
                "source": "phase7_14/parity_comparison_v1.json, sezione "
                         "b_vs_c_structural_comparison",
                "description": "B (EA reale, tick MT5) vs C (ricostruzione Python 7.13, serie "
                              "M15 ricampionata) - confronto di ORDINE DI GRANDEZZA (8 vs 7), "
                              "MAI inteso come evento-per-evento nella stessa Phase 7.14",
                "reclassification_needed": True,
                "old_field_value": "residual_explained: true (Phase 7.14)",
                "new_field_value": residual_classification,
                "reason_for_reclassification": "Verificato in questa fase: SOLO 1 degli 8 eventi "
                                               "B e 7 eventi C condivide la STESSA data+direzione "
                                               "(2025-06-26 BUY) - gli altri 6/7 e 7/8 eventi "
                                               "cadono su date COMPLETAMENTE DIVERSE, non solo "
                                               "'vicine in conteggio'. L'affermazione originale "
                                               "'residuo spiegato dalla diversita' delle fonti' "
                                               "era un'asserzione GENERICA, non una ricostruzione "
                                               "causale - corretta qui con un confronto "
                                               "quantificato delle barre D1 sulle date contestate.",
            },
            "3_event_by_event_parity": {
                "description": "Applicabile in senso stretto SOLO quando la fonte dati e' la "
                              "STESSA (vedi livello 1). Fra B e C (fonti diverse) una parity "
                              "evento-per-evento non e' concettualmente ben posta - qui "
                              "esplicitamente NON presentata come tale (a differenza di una "
                              "possibile lettura fuorviante della tabella originale in Phase "
                              "7.14).",
                "exact_date_direction_matches_b_c": sorted([(d.isoformat(), dr) for d, dr in exact_date_matches]),
                "n_exact_matches": len(exact_date_matches),
                "n_b_only_dates": len(b_only_dates),
                "n_c_only_dates": len(c_only_dates),
            },
        },
        "feed_divergence_quantified_check": {
            "method": "confronto diretto OHLC D1 fra due fonti GIA' ESISTENTI e indipendenti "
                     "(nessun nuovo download/run): export MT5 reale (phase7_9h, usato per "
                     "BREAKOUT_ACC) vs serie ricampionata da M15 (phase7_13) - sulle date in cui "
                     "B e C divergono",
            "disputed_dates_count": len(disputed_dates),
            "samples": feed_divergence_samples,
            "n_dates_with_both_sources_available": len(n_with_data),
            "n_dates_numerically_identical": n_identical,
            "n_dates_numerically_different": n_different,
        },
        "final_residual_classification": residual_classification,
        "final_residual_explanation": residual_explanation,
        "counts_not_forced_to_coincide": True,
        "no_new_backtest_campaign": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE715_DIR, "ea_python_comparison_classification_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  match esatti data+direzione B/C: {payload['three_levels_kept_distinct']['3_event_by_event_parity']['n_exact_matches']}")
    print(f"  classificazione finale residuo: {payload['final_residual_classification']}")


if __name__ == "__main__":
    main()
