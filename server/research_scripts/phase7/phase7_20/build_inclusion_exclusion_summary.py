#!/usr/bin/env python3
"""Phase 7.20 punto 3 - motivazione sintetica di inclusione/esclusione,
una riga per ciascuna delle 9 strategie valutate in profondita' (Tier
A) piu' le regole di Tier B/C. Riassume evaluation_matrix_v1.json e
shortlist_v1.json - non introduce nuovi giudizi."""
import os
import sys

PHASE720_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE720_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402


def build():
    matrix = load_json(os.path.join(PHASE720_DIR, "evaluation_matrix_v1.json"))["payload"]
    tier_a = matrix["tier_a_deep_dive"]

    one_liner = {
        "BREAKOUT_ACC": "INCLUSA - unica strategia con integrita' certificata E dataset economico a fill "
            "reali gia' pronto; evidenza debole (confidence bassa dichiarata) ma sufficiente a meritare "
            "un test economico vero, non altro bug-hunting.",
        "ORDER_BLOCK": "INCLUSA - integrita' certificata al livello piu' alto del corpus; nessuna "
            "evidenza economica ancora, ma il gap e' 'serve un run', non 'serve un altro audit' - "
            "distinzione che la rende pronta per il PROSSIMO passo (validazione), non per un ulteriore "
            "ciclo di integrity work.",
        "TSI": "ESCLUSA nonostante l'integrita' pulita - campione post-fix troppo piccolo (8 eventi/8 "
            "mesi, servirebbero anni) e PF pre-fix gia' debole (0.76, il piu' basso del corpus insieme a "
            "BJORGUM) - rapporto costo/beneficio sfavorevole rispetto a BREAKOUT_ACC/ORDER_BLOCK.",
        "ADX_RSI": "ESCLUSA - integrita' mai verificata (nessuna guardia TF, mescolamento sospetto TF "
            "fisso/variabile trovato in questa fase) E PF debole (0.82) in due fonti indipendenti.",
        "SAR": "ESCLUSA - integrita' mai verificata E quasi nessuna evidenza quantitativa propria "
            "('ambiguo' su un motore terzo, nessun PF MT5 dedicato trovato).",
        "LIQ_SWEEP": "ESCLUSA ma marcata PROMISING - miglior PF del corpus (1.04) ma integrita' MAI "
            "controllata; priorita' 1 per un futuro audit dedicato.",
        "FVG_CONT": "ESCLUSA ma marcata PROMISING - PF quasi breakeven + un segnale A/B non validato "
            "su MT5; priorita' 2, con un gap aggiuntivo di mappatura wrapper (IFVG/FVG_MIT/FVG_MIT_"
            "WINDOW).",
        "BOLLINGER": "ESCLUSA - classificazione SUSPECT non chiusa (Phase 7.10) + PF debole (0.79).",
        "MACD": "ESCLUSA - integrita' mai verificata per questa esatta variante + PF debole (0.79).",
    }

    tier_b_rules_summary = {
        "DEFECT_CONFIRMED_UNFIXED (8 strategie)": "ESCLUSE - stesso difetto strutturale gia' fissato 3 "
            "volte in questa sessione (BREAKOUT_ACC/ORDER_BLOCK/TSI), qui ancora NON corretto. Nessuna "
            "nuova modifica MQL5 autorizzata in questa fase di sola classificazione.",
        "SUSPECT_INTEGRITY_UNRESOLVED (4 strategie)": "ESCLUSE - stesso profilo di rischio di ADX_RSI/"
            "BOLLINGER/MACD (stateless, nessuna guardia TF, mai chiuso con un audit dedicato).",
        "SAFE_INTEGRITY_BUT_NO_REAL_EVIDENCE (7 strategie)": "ESCLUSE - integrita' confermata pulita, ma "
            "zero evidenza quantitativa reale trovata (nessun trade economico mai registrato).",
        "WRAPPER_OF_TIER_A_OR_TIER_B_CANDIDATE (4 strategie)": "ESCLUSE - ereditano lo stato della "
            "strategia riusata, comportamento dinamico con entrambe abilitate mai osservato dal vivo.",
        "TIER_C bulk (59 strategie)": "ESCLUSE in blocco - nessuna evidenza quantitativa trovata in "
            "nessuna fonte consultata, integrita' mai auditata; la maggioranza non e' mai stata live "
            "(RESEARCH_ONLY, varianti esplorative Python-only).",
    }

    payload = {
        "tier_a_one_liner": one_liner,
        "tier_b_tier_c_rules_summary": tier_b_rules_summary,
        "shortlisted": [sid for sid, v in tier_a.items() if v["category"] == "READY_FOR_EDGE_VALIDATION"],
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE720_DIR, "inclusion_exclusion_summary_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")


if __name__ == "__main__":
    main()
