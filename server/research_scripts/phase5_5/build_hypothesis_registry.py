#!/usr/bin/env python3
"""Phase 5.5 sec.1 - Hypothesis Registry.

Legge server/research_scripts/phase5/data/edge_results_v1.json (i 14
test di Phase 5: 9 event-alone + 5 interazioni predefinite) e li
trasforma in voci formali del registro delle ipotesi, applicando le
regole di pre-registrazione dichiarate qui (non decise guardando i
risultati - la distinzione pre_registered/post_hoc sotto riflette come
Phase 5 e' stata davvero condotta, non una rilettura comoda).

Regola di pre-registrazione usata:
- Il DETECTOR e la SOGLIA DI CLASSIFICAZIONE di ciascuno dei 14 test
  erano dichiarati ex-ante (prima di calcolare qualunque outcome) -
  quindi pre_registered_detector=true per tutti e 14.
- MA nessuno dei 14 era stato scelto in anticipo come "l'ipotesi
  principale della fase" - erano un batch di candidati equivalenti.
  La PROMOZIONE di uno specifico risultato (RECLAIM) a headline
  finding/EDGE_COMPONENT e' avvenuta DOPO aver visto che era l'unico
  dei 14 chiaramente positivo - questa selezione a posteriori da un
  batch e' post-hoc nel senso rilevante per il multiple-testing
  (vedi Multiple Testing Ledger, sec.3), anche se il detector stesso
  era congelato in anticipo. Per questo: RECLAIM ha
  pre_registered_detector=true MA post_hoc_selection_from_batch=true,
  e lo status finale e' POST_HOC_CANDIDATE, non SUPPORTED_EDGE.
"""
import json
import os
from datetime import datetime, timezone

ROOT = r"C:\Users\User\ClaudeWork\MAX"
EDGE_RESULTS = os.path.join(ROOT, "server", "research_scripts", "phase5", "data", "edge_results_v1.json")
OUT_JSON = os.path.join(ROOT, "server", "research_scripts", "phase5_5", "hypothesis_registry_v1.json")

VALID_STATUSES = {"PRE_REGISTERED", "DISCOVERY_ONLY", "POST_HOC_CANDIDATE",
                   "VALIDATION_PENDING", "SUPPORTED", "WEAK", "REFUTED",
                   "INSUFFICIENT_SAMPLE"}

BATCH_SIZE = 14  # 9 event-alone + 5 interazioni, lo stesso batch di Phase 5.F-J


def map_status(classification: str, is_reclaim: bool) -> str:
    if is_reclaim:
        return "POST_HOC_CANDIDATE"
    return {
        "SUPPORTED_EDGE": "SUPPORTED",
        "WEAK_EDGE": "WEAK",
        "NO_EDGE": "REFUTED",
        "OPPOSITE_EDGE": "REFUTED",
        "INSUFFICIENT_SAMPLE": "INSUFFICIENT_SAMPLE",
    }.get(classification, "INSUFFICIENT_SAMPLE")


def entry(hid, source, family_or_name, res, is_reclaim=False, condition_desc=None, base_family=None):
    disc = res.get("discovery", {})
    val = res.get("validation", {})
    classification = res.get("classification", "INSUFFICIENT_SAMPLE")
    return {
        "hypothesis_id": hid,
        "created_at": "2026-09-17T18:00:00Z",  # data di build della Phase 5 pipeline
        "source": source,
        "status": map_status(classification, is_reclaim),
        "pre_registered_detector": True,
        "pre_registered_as_primary_hypothesis": False if is_reclaim else (
            classification not in ("SUPPORTED_EDGE",)  # nessun altro test e' stato "promosso", quindi resta ex-ante
        ),
        "post_hoc_selection_from_batch": is_reclaim,
        "batch_id": "PHASE5_EDGE_DISCOVERY_BATCH_1" if not is_reclaim else "PHASE5_EDGE_DISCOVERY_BATCH_1",
        "batch_size": BATCH_SIZE,
        "discovery_dataset": "market_state_dataset_v1 + events_v1, righe [0,3366) (2019-02-03..2021-03-12)",
        "validation_dataset": "market_state_dataset_v1 + events_v1, righe [3366,4809) (2021-03-12..2022-02-03)",
        "primary_outcome": "P(+1xATR before -1xATR) dalla chiusura/conferma evento, orizzonte 40 barre H4",
        "secondary_outcomes": ["mfe_ATR medio (DeltaE)", "soglie 0.25/0.5/1.5/2/3xATR (outcomes_v1.csv)"],
        "baseline_definition": "barre non-evento matched per (terzile volatilita, terzile trend, anno), stessa direzione - vedi phase5_event_dataset_and_baseline_methodology.md",
        "direction_of_expected_effect": "positivo (P(evento)>P(baseline)) per ogni famiglia/interazione testata, dichiarato uniformemente prima dei risultati - nessuna direzione specifica per famiglia scelta ad-hoc",
        "minimum_material_effect": "CI95 Wilson non sovrapposte fra evento e baseline (criterio SUPPORTED_EDGE, edge_discovery.py:classify())",
        "allowed_subgroup_analyses": ["discovery", "validation", "BUY", "SELL", "per anno (2019-2022)"],
        "stop_condition": "n_discovery<15 o n_validation<15 -> INSUFFICIENT_SAMPLE, nessuna estensione del campione dopo il fatto",
        "result": {
            "classification_original": classification,
            "n_discovery": disc.get("event", {}).get("n"),
            "n_validation": val.get("event", {}).get("n"),
            "delta_p_discovery": disc.get("delta_p"),
            "delta_p_validation": val.get("delta_p"),
            "delta_e_validation": val.get("delta_e_mfe_atr"),
        },
        "family_or_name": family_or_name,
        "condition_desc": condition_desc,
        "base_family": base_family,
    }


def main():
    edge = json.load(open(EDGE_RESULTS, encoding="utf-8"))
    registry = []
    i = 1
    for fam, res in edge["event_alone"].items():
        hid = f"H{i:03d}_EVENT_{fam}"
        is_reclaim = (fam == "RECLAIM")
        registry.append(entry(hid, "Phase5.event_alone", fam, res, is_reclaim=is_reclaim))
        i += 1
    for name, res in edge["interactions"].items():
        hid = f"H{i:03d}_INTERACTION_{name}"
        registry.append(entry(hid, "Phase5.interaction", name, res,
                               condition_desc=res.get("condition_desc"), base_family=res.get("base_family")))
        i += 1

    # H015 - SAR external validation (non è un'ipotesi MARKET STATE+EVENT, ma
    # una validazione di segnale pre-esistente su fonte dati indipendente -
    # inclusa per completezza del registro).
    registry.append({
        "hypothesis_id": "H015_SAR_EXTERNAL_VALIDATION",
        "created_at": "2026-09-17T21:00:00Z",
        "source": "Phase5.L",
        "status": "REFUTED",
        "pre_registered_detector": True,
        "pre_registered_as_primary_hypothesis": True,
        "post_hoc_selection_from_batch": False,
        "batch_id": None, "batch_size": 1,
        "discovery_dataset": "N/A (segnale SAR gia' congelato da fasi precedenti, non scoperto in Phase 5)",
        "validation_dataset": "XAUUSD_DSC custom symbol, tick Dukascopy 2019-02-03..2022-02-03, MT5 Model=4",
        "primary_outcome": "Profit Factor del segnale SAR congelato (H4, SL1xATR/TP6xATR, RAW)",
        "secondary_outcomes": ["BUY/SELL split", "win rate", "Sharpe"],
        "baseline_definition": "N/A - confronto diretto contro 2 risultati precedenti indipendenti (broker XM PF1.281; Python pre-2023 Dukascopy PF0.93/0.97), non un baseline matched",
        "direction_of_expected_effect": "PF>=1.15 per confermare l'edge visto sul broker XM",
        "minimum_material_effect": "soglie dichiarate ex-ante: PASS>=1.15, BORDERLINE 0.95-1.15, FAIL<0.95 (vedi sar_dukascopy_independent_validation.md sec.6)",
        "allowed_subgroup_analyses": ["BUY", "SELL"],
        "stop_condition": "nessun rescue/filtro dopo aver visto il risultato",
        "result": {"classification_original": "SAR_EXTERNAL_CONFIRMATION_FAIL", "PF": 0.61, "n": 237},
        "family_or_name": "SAR_PSAR_EMA_TREND_SIGNAL",
        "condition_desc": None, "base_family": None,
    })

    for r in registry:
        assert r["status"] in VALID_STATUSES, r

    json.dump(registry, open(OUT_JSON, "w", encoding="utf-8"), indent=2, default=str)
    print(f"n_hypotheses={len(registry)}")
    for r in registry:
        print(f"  {r['hypothesis_id']:45s} status={r['status']:20s} post_hoc_selection={r['post_hoc_selection_from_batch']}")
    print(f"\nwritten: {OUT_JSON}")


if __name__ == "__main__":
    main()
