#!/usr/bin/env python3
"""Phase 7.23 Fase B - diagnostica minima, PRIMA di qualunque run
lungo. Checklist richiesta dal task: casi deterministici, signal
identity, TF/session/HTF, confronto MT5/Python solo sui livelli
equivalenti, classificazione Python."""
import os
import sys

PHASE723_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE723_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402


def build():
    payload = {
        "1_deterministic_cases": {
            "method": "Traccia statica del flusso di controllo (non un caso numerico ad hoc) - "
                     "per LIQ_SWEEP la logica e' STATELESS e puramente condizionale (nessun "
                     "calcolo ricorsivo/iterativo come TSI che richiederebbe un caso ad aritmetica "
                     "esatta) - il caso deterministico rilevante e' la SEQUENZA DI CHIAMATE "
                     "verificata riga per riga nel codice sorgente, non un valore numerico "
                     "calcolato a mano.",
            "case_1_htf_filter_sequencing": {
                "question": "g_ema200 e px200 sono sempre sulla stessa TF quando il filtro HTF "
                    "valuta un segnale LIQ_SWEEP (canonico D1) durante un pass multi-TF?",
                "trace": [
                    "1. NXS_CollectAllSignals() itera passes[] (ogni TF canonico distinto).",
                    "2. Per il pass D1: NXS_ActivateTF(PERIOD_D1) scambia g_hEMA200 sull'handle "
                    "D1 E CHIAMA NXS_UpdateIndicators() (NEXUS_EA_v2.mq5:232) - g_ema200 viene "
                    "RICALCOLATO qui, sull'handle D1 ora attivo.",
                    "3. NXS_CollectRaw() viene chiamata SUBITO DOPO, nello STESSO pass - il "
                    "filtro HTF al suo interno legge px200=iClose(...,NXS_EffTF(),0) (D1, fresco) "
                    "e lo confronta con g_ema200 (gia' aggiornato al punto 2, stesso D1).",
                    "4. Nessuna altra chiamata a NXS_ActivateTF/UpdateIndicators avviene fra i "
                    "punti 2 e 3 per questo pass.",
                ],
                "conclusion": "px200 e g_ema200 SONO sulla stessa TF (D1) quando il filtro valuta "
                    "il segnale LIQ_SWEEP - ipotesi di mismatch INIZIALMENTE SOSPETTATA (per "
                    "istruzione esplicita del task), poi VERIFICATA E RESPINTA.",
            },
        },
        "2_signal_identity": {
            "verified": "s.strat=STRAT_LIQ_SWEEP, s.stratName='LIQ_SWEEP' (MQL5); nessuna "
                       "ambiguita' di identita' trovata (nessun alias/wrapper che riusi "
                       "STRAT_LIQ_SWEEP da altre funzioni, a differenza di OB_MIT/FVG_MIT).",
        },
        "3_tf_session_htf": {
            "tf": "Canonico D1 (NXS_Profile_TF), filtrato a valle dal router (riga 710) - "
                 "verificato nessuna contaminazione cross-TF possibile (funzione stateless).",
            "session": "Non session-bound (a differenza di JUDAS_SWING/LDN_REVERSAL/NY_REVERSAL) "
                     "- LIQ_SWEEP valuta ad ogni barra D1 chiusa, nessuna finestra oraria.",
            "htf": "Verificato al punto 1 sopra - nessun mismatch confermato.",
        },
        "4_mt5_python_comparison_only_equivalent_levels": {
            "note": "Vedi liq_sweep_semantic_parity_matrix_v1.json - confrontati SOLO i livelli "
                   "realmente equivalenti (sweep detection, delivery-candle filter, direction "
                   "gate) - l'uscita SL/TP e il filtro HTF multi-TF NON sono stati forzati in un "
                   "confronto diretto perche' strutturalmente diversi/non applicabili.",
        },
        "5_python_classification": {
            "classification": "PARTIAL_STRUCTURAL_MODEL",
            "not_event_level_faithful": "L'uscita (SL/TP) e' strutturalmente diversa - qualunque "
                "P&L calcolato da Python NON rappresenta l'identita' MQL5 dal vivo.",
            "not_unsuitable_for_everything": "L'ingresso (sweep+delivery-candle+direzione) resta "
                "strutturalmente utile per confronti di SEGNALE (non di P&L) - non sfruttato in "
                "questa fase (nessun nuovo run Python lanciato, fuori scope di un audit di "
                "integrita').",
        },
        "minimum_mt5_run_needed": {
            "decision": "SI, MA BREVE - nessuna evidenza quantitativa esistente rappresenta "
                "l'identita' canonica attuale POST-fix del detector (2026-09-14) - serve un primo "
                "run diagnostico/economico fresco, ma la diagnostica statica sopra NON ha trovato "
                "un difetto strutturale in MQL5 che richieda un run pluriennale per essere "
                "isolato (a differenza di TSI/ORDER_BLOCK, dove serviva confrontare pre/post "
                "fix) - qui non esiste un 'pre-fix' da confrontare (il fix del detector e' gia' "
                "applicato e comune a 10+ strategie, non specifico a LIQ_SWEEP).",
            "window_chosen": "Vedi liq_sweep_diagnostic_run_v1.json per il periodo scelto e la "
                            "motivazione - run eseguito con il nuovo harness di isolamento "
                            "(Fase A di questa stessa fase).",
            "no_automatic_multi_year_run": True,
        },
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE723_DIR, "liq_sweep_diagnostic_findings_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")


if __name__ == "__main__":
    main()
