#!/usr/bin/env python3
"""Phase 7.23 Fase B punto 5 - semantic parity matrix MQL5 vs Python,
UN livello del funnel alla volta - confronta solo i livelli realmente
equivalenti (non forza un confronto dove le due implementazioni fanno
cose strutturalmente diverse)."""
import os
import sys

PHASE723_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE723_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402


def build():
    payload = {
        "funnel_levels_compared": {
            "1_sweep_detection": {
                "mql5": "NXS_DetectSweepExt() - PDH/PDL/Asia High-Low/PWH-PWL/PMH-PML/EQH-EQL, "
                       "ordine sequenziale fisso (Asia->daily->weekly->monthly, EQH/EQL come "
                       "fallback), corretto per inizializzazione struct il 2026-09-14.",
                "python": "_sweep_ext_at_raw() - STESSI livelli, STESSO ordine sequenziale "
                         "dichiarato (commento 04/08: 'fedelta' verificata riga-per-riga').",
                "verdict": "STRUTTURALMENTE ALLINEATO (claim informale pre-esistente, non "
                          "ri-verificato a hash in questa fase) - MA nessuna evidenza quantitativa "
                          "esistente e' stata generata DOPO il fix del 14/09, quindi la fedelta' "
                          "strutturale del confronto non e' comunque garanzia che le ESECUZIONI "
                          "storiche fossero equivalenti (vedi historical_evidence_map).",
                "parity_status": "PARTIAL_STRUCTURAL_MODEL",
            },
            "2_delivery_candle_filter": {
                "mql5": "|close[1]-open[1]| >= 0.7*ATR (aggiunto 2026-07-16)",
                "python": "abs(c1-o1) < 0.7*atr: return 0 (stessa soglia, stessa formula)",
                "verdict": "IDENTICO per lettura diretta del codice.",
                "parity_status": "EVENT_LEVEL_FAITHFUL_FOR_THIS_SUBCOMPONENT",
            },
            "3_direction_gate": {
                "mql5": "sw.dir==BUY && c1>o1 -> BUY; sw.dir==SELL && c1<o1 -> SELL",
                "python": "sw['dir']==1 and c1>o1 -> 1; sw['dir']==-1 and c1<o1 -> -1",
                "verdict": "IDENTICO per lettura diretta del codice.",
                "parity_status": "EVENT_LEVEL_FAITHFUL_FOR_THIS_SUBCOMPONENT",
            },
            "4_htf_alignment_filter": {
                "mql5": "NXS_Profile_HTF('LIQ_SWEEP')=true -> px200 (close TF attivo) vs g_ema200, "
                       "applicato A VALLE nel router (NXS_CollectRaw, dentro ogni pass multi-TF).",
                "python": "NON investigato in questo confronto - il motore Python di backtest non "
                         "replica il router multi-TF live tick-per-tick (e' single-pass su una "
                         "sola serie), quindi questo livello NON E' equivalente per costruzione.",
                "verdict": "LIVELLO NON CONFRONTABILE (Python non ha un equivalente diretto del "
                          "router multi-TF live) - verificato pero' separatamente che il "
                          "meccanismo MQL5 stesso NON ha il mismatch inizialmente sospettato "
                          "(vedi liq_sweep_identity_map_v1.json).",
                "parity_status": "NOT_APPLICABLE_STRUCTURAL_DIFFERENCE",
            },
            "5_exit_sl_tp": {
                "mql5": "NXS_DefaultSLTP() - FISSO: SL=ATRx1.5, TP=ATRx3.0 (R:R=2.0)",
                "python": "_liq_sweep_target() - DINAMICO: TP sulla liquidita' OPPOSTA "
                         "(PDH/PDL/Asia/swing_ext), min_rr=1.2, sl_mult=1.5",
                "verdict": "MISMATCH CONFERMATO - due logiche di uscita strutturalmente diverse. "
                          "Il commento Python stesso dichiara che il dinamico sostituisce 'un "
                          "multiplo fisso di ATR' (cioe' proprio cio' che MQL5 esegue dal vivo).",
                "parity_status": "STRUCTURALLY_DIFFERENT_NOT_COMPARABLE",
            },
        },
        "overall_python_suitability": "PARTIAL_STRUCTURAL_MODEL_FOR_ENTRY_ONLY - il motore Python "
            "e' strutturalmente allineato a MQL5 SOLO per l'entry trigger (sweep+delivery-candle+"
            "direzione) - NON per l'uscita (SL/TP), che e' un'implementazione diversa per "
            "costruzione. Qualunque PF/expectancy calcolato da Python per LIQ_SWEEP misura una "
            "strategia CON LO STESSO INGRESSO ma un'uscita diversa - non e' evidenza economica "
            "della strategia che MQL5 esegue dal vivo.",
        "not_event_level_faithful_overall": True,
        "not_unsuitable_either": "Il livello di ingresso (1-3) e' comunque strutturalmente utile "
            "per un CONFRONTO DI SEGNALI (non di P&L) - es. verificare che le date/direzioni dei "
            "trigger generati da MQL5 e Python coincidano - non svolto in questa fase (nessun "
            "nuovo run Python lanciato, fuori scope di un audit di integrita').",
        "mt5_remains_ground_truth": "Coerente con la lezione di Phase 7.16 e con l'istruzione "
            "esplicita del task - qualunque evidenza economica futura per LIQ_SWEEP deve venire "
            "da un run MT5 reale, non dal motore Python.",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE723_DIR, "liq_sweep_semantic_parity_matrix_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")


if __name__ == "__main__":
    main()
