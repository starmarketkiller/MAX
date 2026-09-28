#!/usr/bin/env python3
"""Phase 7.23 Fase B punto 4/5 - LIQ_SWEEP historical evidence map.
Classifica ogni vecchio risultato REUSABLE/PARTIALLY_REUSABLE/
CONTAMINATED/CANNOT_DETERMINE, usando date git verificate (non
supposizioni) per determinare quale codice era attivo quando ogni
evidenza e' stata prodotta. Il PF 1.04 di sweep37 NON e' usato come
prova di edge - solo come motivo per investigare (gia' fatto in
liq_sweep_identity_map_v1.json)."""
import os
import sys

PHASE723_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE723_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

# Date git verificate (git log -L / git show -s --format=%ci), non supposizioni.
DELIVERY_CANDLE_FILTER_ADDED = "2026-07-16"   # commit 6052636
SWEEP37_BASELINE_COMMIT_DATE = "2026-07-18"   # commit e6ce816
PF248_COMMENT_DATE = "2026-07-10"             # commit 0a86001 (PRIMA del filtro 0.7xATR)
PYTHON_IS091_COMMENT_DATE = "2026-08-12"      # commit 6b2ff81
DETECTOR_INTEGRITY_FIX_COMMIT_DATE = "2026-09-14"  # commit 9b77f83


def build():
    payload = {
        "principle": "Un artifact storico non viene mai cancellato - viene classificato rispetto "
                    "all'identita' implementativa CANONICA ATTUALE, usando le date git REALI (non "
                    "supposte) del codice che era attivo quando l'evidenza e' stata generata.",
        "key_dates_verified_via_git": {
            "delivery_candle_filter_0_7xATR_added": DELIVERY_CANDLE_FILTER_ADDED,
            "sweep37_baseline_commit_date": SWEEP37_BASELINE_COMMIT_DATE,
            "pf248_comment_date": PF248_COMMENT_DATE,
            "python_is091_comment_date": PYTHON_IS091_COMMENT_DATE,
            "sweepext_detector_integrity_fix_date": DETECTOR_INTEGRITY_FIX_COMMIT_DATE,
        },
        "items": [
            {
                "artifact": "Commento NXS_StrategyProfiles.mqh:109 'PF2.48 R2.0' (10/07)",
                "kind": "COMMENTO_SVILUPPATORE_NON_ARTIFACT_STRUTTURATO",
                "classification": "CONTAMINATED",
                "reasoning": f"Datato {PF248_COMMENT_DATE} - PRECEDE l'aggiunta del filtro "
                    f"delivery-candle 0.7xATR ({DELIVERY_CANDLE_FILTER_ADDED}). Misura una "
                    "versione dell'entry trigger STRUTTURALMENTE DIVERSA da quella attuale (senza "
                    "il filtro di qualita' candela) - non rappresenta l'identita' canonica di oggi.",
            },
            {
                "artifact": "knowledge/backtest_database.json, sweep37 S07 LIQ_SWEEP (PF 1.04, "
                          "baseline e6ce816, 2019.07.11-2025.07.11, XM Global, 30% tick reali)",
                "kind": "MT5_STRATEGY_TESTER_SWEEP_RESULT",
                "classification": "CONTAMINATED",
                "reasoning": f"Baseline {SWEEP37_BASELINE_COMMIT_DATE} - e' un ANTENATO git "
                    f"verificato del commit di fix {DETECTOR_INTEGRITY_FIX_COMMIT_DATE} "
                    "(9b77f83): misura il comportamento SOTTO il difetto NOTO e gia' corretto di "
                    "NXS_DetectSweepExt() (struct locale non azzerata correttamente in ~1 chiamata "
                    "su 7, 'Detector Integrity Fix') - il rilevatore di sweep condiviso da 10+ "
                    "strategie (incluso LIQ_SWEEP) produceva risultati corrotti con probabilita' "
                    "non trascurabile. Il filtro delivery-candle ERA gia' presente (post 16/07), "
                    "quindi l'entry trigger era strutturalmente quello attuale, ma eseguito su un "
                    "detector difettoso.",
            },
            {
                "artifact": "Commento NXS_StrategyProfiles.mqh:405 'Python DEBOLE, IS 0.91 sotto "
                          "pareggio' (12/08)",
                "kind": "COMMENTO_SVILUPPATORE_RIFERITO_A_MOTORE_PYTHON",
                "classification": "CONTAMINATED",
                "reasoning": f"Datato {PYTHON_IS091_COMMENT_DATE} - POST filtro delivery-candle "
                    f"({DELIVERY_CANDLE_FILTER_ADDED}, quindi trigger allineato) ma PRE fix "
                    f"detector ({DETECTOR_INTEGRITY_FIX_COMMIT_DATE}, quindi ANCHE questo "
                    "risultato Python e' passato attraverso il detector condiviso difettoso, dato "
                    "che _sweep_ext_at_raw dichiara fedelta' riga-per-riga con lo stesso "
                    "NXS_DetectSweepExt()). INOLTRE (motivo separato e sufficiente da solo): "
                    "misura l'uscita DINAMICA su liquidita' opposta (_liq_sweep_target), non "
                    "l'uscita FISSA ATR che MQL5 esegue dal vivo - due strategie diverse "
                    "nell'uscita, MAI direttamente comparabili in PF.",
            },
            {
                "artifact": "server/backtest.py::sig_liq_sweep (superseded, '26 trade reali in 8 "
                          "anni')",
                "kind": "PYTHON_FUNZIONE_DICHIARATAMENTE_SUPERATA",
                "classification": "CONTAMINATED",
                "reasoning": "L'autore stesso dichiara esplicitamente questa funzione SUPERATA il "
                    "16/07 da sig_liq_sweep_ext - usa un rilevatore di sweep generico (estremo a "
                    "20 barre) invece del vero motore ICT (PDH/PDL/Asia/EQH-EQL) - non rappresenta "
                    "l'identita' canonica per nessuna versione recente.",
            },
        ],
        "no_reusable_evidence_found_for_current_canonical_identity": True,
        "reason": "OGNI pezzo di evidenza quantitativa trovato per LIQ_SWEEP (MT5 o Python) e' "
            "stato prodotto O sotto un entry trigger strutturalmente diverso da quello attuale, O "
            "sotto il detector di sweep condiviso difettoso (corretto solo il 14/09), O misura "
            "una logica di USCITA diversa da quella che MQL5 esegue dal vivo (o una combinazione "
            "delle precedenti) - nessuna conclusione economica (positiva o negativa) puo' essere "
            "tratta da questi artifact per l'identita' canonica attuale.",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE723_DIR, "liq_sweep_historical_evidence_map_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")


if __name__ == "__main__":
    main()
