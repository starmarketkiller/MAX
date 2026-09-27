#!/usr/bin/env python3
"""Phase 7.17 punto 6 - mappa (senza cancellare nulla) dell'evidenza
storica TSI. Classificazione: UNAFFECTED / POSSIBLY_CONTAMINATED /
CONTAMINATED / CANNOT_DETERMINE. Nessun PF/WR reinterpretato
economicamente.
"""
import os
import sys

PHASE717_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE717_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

ITEMS = [
    {
        "artifact": "knowledge/backtest_database.json, campagna 'sweep37 ROUND CORRENTE "
                   "(baseline)', passata S05 = TSI (commit e6ce816, 839 trade, PF 0.76, "
                   "periodo 2019.07.11-2025.07.11, XM Global GOLD)",
        "kind": "MT5_STRATEGY_TESTER_SWEEP_RESULT",
        "classification": "POSSIBLY_CONTAMINATED",
        "reasoning": "Metadati del database: 'timeframe: per strategia (TF profilo)' e "
                    "'trade: ... isolato, lotto fisso' - coerente con un run a "
                    "InpStrategySelector isolato (S05=selettore 5=TSI) con "
                    "InpUseStrategyProfiles/InpProfileMultiTF attivi (stessa convenzione "
                    "gia' vista per i run ORDER_BLOCK in Phase 7.13). Se confermato, il "
                    "meccanismo di contaminazione sarebbe stato strutturalmente presente "
                    "(TSI non ha una guardia TF, verificato in questa fase). La "
                    "configurazione ESATTA (InpProfileMultiTF on/off) non e' verificabile "
                    "dal solo database - POSSIBLY_, non CONTAMINATED tout court. Qualita' "
                    "dati dichiarata 'Every tick, 30% tick reali' - PIU' BASSA della "
                    "qualita' usata nei run diagnostici ORDER_BLOCK di Phase 7.14 (100% tick "
                    "reali) - un'ulteriore riserva sulla qualita' di questa evidenza, "
                    "indipendente dal difetto cross-TF.",
        "implication": "Il PF 0.76 su 839 trade NON viene reinterpretato ne' come prova a "
                       "favore ne' contro l'edge della strategia canonica - l'identita' "
                       "eseguita in quel run non e' accertata al 100%.",
    },
    {
        "artifact": "results/phase2_baseline_20260705_v2.0.27.csv, riga InpStrat_TSI "
                   "(15 trade, PF 0.51, 'history_quality: 100% ticks reali')",
        "kind": "MT5_STRATEGY_TESTER_REAL_TICK_RESULT",
        "classification": "POSSIBLY_CONTAMINATED",
        "reasoning": "Stessa struttura del corrispondente ORDER_BLOCK gia' classificato in "
                    "Phase 7.13 - esecuzione a tick reali del vero EA MQL5, ma la "
                    "configurazione esatta (multi-TF on/off) di QUESTO specifico run non e' "
                    "verificabile dal solo CSV.",
        "implication": "Campione minuscolo (15 trade) - nessuna conclusione economica "
                       "comunque estraibile, a prescindere dalla contaminazione.",
    },
    {
        "artifact": "results/phase_partB_silent_diagnostic_20260706.csv, riga TSI "
                   "(pattern_fired_count=3874, dominant_block_stage=PREFLIGHT(10), "
                   "note='blocked_by_gate:PREFLIGHT(ambiguous)')",
        "kind": "MT5_DIAGNOSTIC_RAW_SIGNAL_COUNT",
        "classification": "POSSIBLY_CONTAMINATED",
        "reasoning": "Conteggio di 'pattern_fired' (raw trigger) su una configurazione non "
                    "documentata in questo artifact. L'ordine di grandezza (3874) e' "
                    "compatibile con un conteggio contaminato multi-TF (questa fase trova "
                    "60 segnali D1 generati SOLO nel confronto Stream A su 2.9 anni - "
                    "un valore molto piu' basso, ma qui la finestra/configurazione non e' "
                    "nota) - NON trattato come conferma numerica, solo coerenza plausibile.",
        "implication": "Nessuna reinterpretazione quantitativa.",
    },
    {
        "artifact": "server/backtest.py::sig_tsi/tsi_series (motore Python)",
        "kind": "PYTHON_BACKTEST_ENGINE_IMPLEMENTATION",
        "classification": "UNAFFECTED_BUT_NOT_REPRESENTATIVE_OF_LIVE",
        "reasoning": "Single-TF per costruzione (nessun loop multi-pass) - strutturalmente "
                    "equivalente alla ricostruzione TF-scoped di questa fase (Stream B), "
                    "confermato con un confronto diretto (tsi_python_fidelity_v1.json: 100% "
                    "delle barre D1 con TSI vicino, tutti i segnali TF-scoped contenuti in "
                    "Python).",
        "implication": "Qualunque PF/WR storico calcolato con questo motore per TSI NON e' "
                       "rappresentativo di cio' che l'EA MQL5 dal vivo esegue oggi "
                       "(dimostrato materialmente diverso in tsi_impact_comparison_v1.json: "
                       "100% delle barre D1 con TSI numericamente diverso fra Stream A "
                       "contaminato e Stream B) - e' la misura di un'IDENTITA' DIVERSA da "
                       "quella live.",
    },
]


def build():
    counts = {}
    for it in ITEMS:
        counts[it["classification"]] = counts.get(it["classification"], 0) + 1
    payload = {
        "principle": "un PF/WR non viene mai reinterpretato come evidenza della strategia "
                    "canonica se l'identita' eseguita (single-TF pulito vs multi-TF "
                    "contaminato) non e' stabilita per quell'artifact specifico - nessun "
                    "artifact viene cancellato, solo classificato",
        "classifications_used": ["UNAFFECTED", "UNAFFECTED_BUT_NOT_REPRESENTATIVE_OF_LIVE",
                                 "POSSIBLY_CONTAMINATED", "CONTAMINATED", "CANNOT_DETERMINE"],
        "items": ITEMS,
        "counts_by_classification": counts,
        "no_artifact_deleted_or_modified": True,
        "no_pf_reinterpreted_as_canonical_evidence": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE717_DIR, "tsi_historical_evidence_map_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  classificazioni: {payload['counts_by_classification']}")


if __name__ == "__main__":
    main()
