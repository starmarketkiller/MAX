#!/usr/bin/env python3
"""Phase 7.19 punto 21 - gap analysis dopo la costruzione dei 3 esempi:
ALREADY_AVAILABLE / DERIVABLE / MISSING_BUT_NEEDED / OPTIONAL."""
import os
import sys

PHASE719_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE719_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402


def build():
    payload = {
        "method": "Basato sui 3 packet dimostrativi (example_packets_v1.json) - ogni campo "
                 "ABSENT osservato negli esempi e' stato classificato qui.",
        "ALREADY_AVAILABLE": [
            "signal_price, actual_fill_price, exit_fill_price (BREAKOUT_ACC, da NXS_LogTradeCSV "
            "+ HistoryDealGetDouble - gia' esportati per BREAKOUT_ACC in Phase 7.9H)",
            "state_before/state_after per strategie a stato discreto (ORDER_BLOCK, con "
            "istrumentazione diagnostica TEMPORANEA gia' dimostrata in Phase 7.14/7.18 - non "
            "ancora permanente)",
            "post_entry_path_anatomy / MFE-MAE-horizons (BREAKOUT_ACC, Phase 7.9H-K)",
            "canonical_strategy_identity, code_commit_sha (tracciabile via git per ogni fase "
            "committata)",
        ],
        "DERIVABLE": [
            "multi_timeframe_context.bars_by_timeframe (ricostruibile da un export D1/H4/H1/M30/"
            "M15 gia' dimostrato in Phase 7.13 - richiede solo un builder dedicato, nessun dato "
            "nuovo)",
            "pre_entry_feature_snapshot per trend/volatility/atr (derivabile causalmente da "
            "indicatori gia' calcolati dall'EA, se esportati - oggi NON esportati per la "
            "maggior parte delle strategie)",
            "fill_relative_path a partire da signal_relative_path + fill_time noto (solo per "
            "eventi con fill reale)",
        ],
        "MISSING_BUT_NEEDED": [
            {
                "field": "RUNTIME_IDENTITY_MANIFEST_V1 (intero schema)",
                "why_needed": "NESSUNO dei 3 esempi ha potuto popolare runtime_fingerprint/"
                              "build_id/ex5_hash - senza questo, un packet Fidelity A e' "
                              "strutturalmente impossibile da raggiungere, per qualunque "
                              "strategia.",
                "priority": "ALTA",
            },
            {
                "field": "actual fill reale per eventi catturati da istrumentazione diagnostica "
                        "(es. ORDER_BLOCK Phase 7.14/7.18)",
                "why_needed": "L'istrumentazione attuale cattura SOLO lo stato interno della "
                              "strategia, mai il fill reale associato - un evento con stato "
                              "reale ma fill assente resta bloccato a Fidelity B/C.",
                "priority": "ALTA",
            },
            {
                "field": "state snapshot per strategie SENZA istrumentazione diagnostica "
                        "temporanea attiva (es. SH_BMS_RTO, la maggioranza delle strategie del "
                        "registro)",
                "why_needed": "Oggi lo stato interno e' visibile SOLO per le strategie "
                              "diagnosticate una-tantum (ORDER_BLOCK, TSI) con istrumentazione "
                              "poi rimossa - non esiste un meccanismo permanente e "
                              "generalizzato.",
                "priority": "ALTA",
            },
            {
                "field": "Bid/Ask al momento della decisione (non solo al fill)",
                "why_needed": "Nessuno dei 3 esempi ha Bid/Ask - necessario per calcolare "
                              "spread/slippage in modo affidabile per QUALUNQUE evento, non "
                              "solo quelli con fill reale.",
                "priority": "MEDIA",
            },
            {
                "field": "exact strategy decision timestamp distinto da signal_time",
                "why_needed": "Nei 3 esempi, decision_time coincide sempre con signal_time per "
                              "mancanza di un timestamp dedicato - il modello concettuale (6 "
                              "timestamp distinti) esiste ma la strumentazione attuale ne "
                              "produce di fatto 1-2.",
                "priority": "MEDIA",
            },
            {
                "field": "chart context visivo (screenshot o rendering riproducibile)",
                "why_needed": "visual_context_source e' NOT_AVAILABLE in tutti e 3 gli esempi - "
                              "nessuna pipeline di rendering grafico esiste oggi.",
                "priority": "MEDIA (dipendenza diretta per VISUAL_AUDIT_PROTOCOL_V1)",
            },
        ],
        "OPTIONAL": [
            "portfolio_context (nessuno dei 3 esempi lo popola - utile per il futuro Small "
            "Account Portfolio Engine, non bloccante per l'audit standard)",
            "tenant_id/ea_instance_id/account_scope_id (riservati per architettura "
            "multi-cliente futura, NOT_APPLICABLE oggi)",
            "volume (dati tick volume non sempre affidabili su FX/Gold via MT5)",
        ],
        "cross_cutting_finding": "In TUTTI E TRE gli esempi, il campo runtime_fingerprint e' "
                                "risultato NOT_AVAILABLE - questo e' il gap SINGOLO piu' "
                                "ricorrente e trasversale trovato in questa fase, coerente con "
                                "punto 10 della task originale ('Non basta il timestamp del "
                                "file EX5').",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE719_DIR, "gap_analysis_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  MISSING_BUT_NEEDED: {len(payload['MISSING_BUT_NEEDED'])} voci")


if __name__ == "__main__":
    main()
