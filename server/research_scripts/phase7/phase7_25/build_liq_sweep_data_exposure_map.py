#!/usr/bin/env python3
"""Phase 7.25 punto 1 - DATA_EXPOSURE_MAP, PRIMA di qualunque conclusione
economica. Principio: 'esiste gia' nel dataset canonico' NON equivale a
'e' stato analizzato economicamente'. I 42 trade chiusi sono stati
GIA' VISTI in Phase 7.24 (net P&L totale calcolato e riportato: +$1.076,30)
- NON sono quindi un campione 'blind'/OOS per la domanda 'net P&L
esiste?'. Sono pero' genuinamente untouched per OGNI statistica piu'
fine costruita in questa fase (expectancy per direzione, concentrazione,
CI bootstrap, cost stress, robustezza temporale, path anatomy) - nessuna
di queste e' mai stata calcolata prima d'ora."""
import os
import sys

PHASE725_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE725_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

DIAGNOSTIC_START = "2023.10.02"
DIAGNOSTIC_END = "2026.06.30"
FORWARD_START = "2026.07.01"
TODAY = "2026.09.27"


def build():
    payload = {
        "principle": "Un periodo/statistica e' UNTOUCHED per una data domanda solo se nessuno script "
                    "di ricerca ha mai calcolato QUELLA statistica specifica prima d'ora su quei dati. "
                    "'Il dataset canonico esiste gia'' (Phase 7.24) NON equivale a 'l'expectancy per "
                    "direzione/la concentrazione/il CI sono gia' stati calcolati'.",
        "categories_used": ["development", "integrity_audit", "mechanism_analysis", "seen",
                           "untouched", "true_oos"],
        "periods": [
            {
                "period": f"prima del {DIAGNOSTIC_START}",
                "category": "untouched",
                "detail": "Nessun dato LIQ_SWEEP canonico (post-fix delivery-candle 2026-07-16, "
                        "post-fix detector 2026-09-14) esiste per questo periodo in questo "
                        "progetto - non investigato, non usato.",
            },
            {
                "period": f"{DIAGNOSTIC_START} - {DIAGNOSTIC_END} (finestra del run diagnostico "
                         "isolato di Phase 7.23, 43 eventi / 42 chiusi)",
                "category": ["integrity_audit", "mechanism_analysis", "seen"],
                "used_for_development": False,
                "used_in_phase_7_23_integrity_audit": "SI - identita' canonica, ipotesi HTF "
                    "(verificata e respinta), mismatch exit Python/MQL5 (confermato) - MAI P&L/"
                    "expectancy/PF/concentrazione/CI.",
                "used_in_phase_7_24_adjudication": "SI - funnel accounting, adjudication del "
                    "residuo 42 vs 43, costruzione del dataset canonico - il NET P&L TOTALE "
                    "(+$1.076,30) e' gia' stato calcolato e riportato in Phase 7.24. QUESTO "
                    "NUMERO SPECIFICO (net P&L aggregato ALL) NON E' BLIND in questa fase.",
                "seen_for": ["esistenza del dataset", "funnel accounting", "net P&L totale ALL "
                            "aggregato (+$1.076,30)"],
                "genuinely_untouched_for": ["expectancy/PF/WR per direzione (BUY/SELL separati)",
                    "concentrazione del profitto (top-N)", "incertezza statistica (bootstrap CI)",
                    "cost stress scenari", "robustezza temporale (per anno/rolling/regime)",
                    "path anatomy (MFE/MAE)", "visual audit stratificato",
                    "minimum viable capital", "gate finale di edge validation"],
                "verdict": "POPOLAZIONE PRIMARIA di questa fase per OGNI statistica elencata sopra "
                    "come genuinamente untouched - MA il net P&L aggregato ALL non e' una sorpresa "
                    "'blind' (gia' visibile dal titolo di Phase 7.24). Non chiamato OOS.",
            },
            {
                "period": f"{FORWARD_START} - {TODAY} (finestra FORWARD)",
                "category": "true_oos",
                "used_for_development": False, "used_in_phase_7_23": False,
                "used_in_phase_7_24": False, "seen_in_reports": False,
                "genuinely_untouched": True,
                "verdict": "VERO HOLDOUT - nessun run, nessuna analisi, nessun report ha mai "
                    "toccato questa finestra per LIQ_SWEEP. Richiede un NUOVO run MT5 dedicato "
                    "(harness di isolamento Phase 7.23) per essere popolato - eseguito in questa "
                    "fase, punto 10 (OOS/holdout).",
            },
        ],
        "m15_price_series_provenance": "server/research_scripts/nxs_m15_gold_extended.csv - file "
            "gia' presente nel progetto (usato in precedenza da Phase 7.13/7.16 per altre domande "
            "di ricerca), copre 2023-10-02 -> 2026-08-25. Provenienza non ri-accertata oltre il "
            "controllo di plausibilita' gia' documentato in Phase 7.13 (formato e range di prezzo "
            "coerenti con altre esportazioni XAUUSD del progetto) - limite dichiarato, non "
            "nascosto. Usato SOLO per visual audit/path anatomy descrittivi (research-only), MAI "
            "come fonte di P&L (che resta il campo actual_pnl del dataset canonico MT5).",
        "forward_window": [FORWARD_START, TODAY],
        "conclusion": "Nessun vero holdout storico indipendente esiste all'interno dei 42 trade "
            "chiusi - trattati come popolazione primaria per l'analisi economica fine, MAI come "
            "conferma indipendente del net P&L aggregato (gia' visto). La finestra forward e' "
            "l'unica genuinamente idonea a un test OOS in senso stretto.",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE725_DIR, "data_exposure_map_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")


if __name__ == "__main__":
    main()
