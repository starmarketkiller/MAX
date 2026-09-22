#!/usr/bin/env python3
"""Phase 7.8G - Root cause analysis del run con 0 operazioni totali.

Il report ufficiale MT5 del Serious validation reale (raccolto e hashato
PRIMA di qualunque interpretazione in immutable_run_manifest_v1.json)
riporta "Numero di Operazioni di Trading Totali: 0" con "Qualita' dello
Storico: 100% ticks reali" - quindi NON e' un problema di dati.

La causa e' un secondo master-switch per-strategia, mai incluso in nessun
tester config congelato attraverso le fasi 7.8B-7.8G: InpStrat_
VolBreakoutConfirmed, default FALSE (NXS_Inputs.mqh:544, commento
esplicito "mai verificata su MT5 - default OFF"). Il segnale
NXS_Strat_VolatilityBreakoutConfirmed() ritorna immediatamente DIR_NONE se
questo flag e' false, PRIMA di valutare qualunque condizione di prezzo -
indipendentemente da InpStrategySelector=56 (gia' corretto).

Questo NON e' un esito di mercato (nessun segnale mai valutato, non
"nessun segnale trovato") e NON e' un rescue (nessun parametro di
strategia/rischio/soglia toccato - un prerequisito di abilitazione
mancante, analogo al bug Expert= gia' corretto in 7.8F). Nessun verdetto
preregistrato viene calcolato su questo run - sarebbe scientificamente
vuoto presentare 0 trade per misconfigurazione come INSUFFICIENT_SAMPLE.
"""
import os
import sys

PHASE78G_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE78G_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import file_sha256, load_json, save_json, wrap_with_provenance  # noqa: E402


def build():
    manifest = load_json(os.path.join(PHASE78G_DIR, "immutable_run_manifest_v1.json"))
    report_path = os.path.join(ROOT, manifest["payload"]["collected_files"]["report_htm"]["dest_path"])
    with open(report_path, encoding="utf-16", errors="ignore") as f:
        report_text = f.read()

    import re

    def extract_after(label_substr, text):
        idx = text.find(label_substr)
        if idx < 0:
            return "NOT_FOUND"
        m = re.search(r"<b>(.*?)</b>", text[idx: idx + 300])
        return m.group(1).strip() if m else "NOT_FOUND"

    total_trades = extract_after("Operazioni di Trading Totali", report_text)
    history_quality = extract_after("dello Storico", report_text)

    inputs_file = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Inputs.mqh")
    with open(inputs_file, encoding="utf-8") as f:
        inputs_src = f.read()
    flag_line = next(ln for ln in inputs_src.splitlines() if "InpStrat_VolBreakoutConfirmed" in ln and "input bool" in ln)

    strategies_file = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Strategies.mqh")
    with open(strategies_file, encoding="utf-8") as f:
        strategies_src = f.read()
    guard_line = next(ln for ln in strategies_src.splitlines() if "InpStrat_VolBreakoutConfirmed" in ln and "NXS_SelectorAllows" in ln)

    frozen_tester_config_78f = load_json(os.path.join(PHASE78G_DIR, "..", "phase7_8f",
                                                        "volatility_breakout_execution_config_audit_v1.json"))
    tester_config_raw = frozen_tester_config_78f["payload"]["tester_execution_config_final"]["raw_text"]
    flag_present_in_frozen_config = "InpStrat_VolBreakoutConfirmed" in tester_config_raw

    other_strat_flags_sample = [ln.strip() for ln in inputs_src.splitlines()
                                if "input bool     InpStrat_" in ln][:5]

    payload = {
        "phase": "7.8G",
        "artifact_role": "ZERO_TRADE_ROOT_CAUSE_ANALYSIS",
        "candidate_id": "VOLATILITY_BREAKOUT_CONFIRMED",
        "immutable_run_manifest_reference": {
            "canonical_sha256": manifest["canonical_sha256"],
        },
        "observed_fact": {
            "total_trades_in_official_report": total_trades,
            "history_quality": history_quality,
            "source": "report_htm reale, raccolto e hashato PRIMA di questa analisi (vedi immutable_run_manifest_v1.json)",
            "interpretation": "0 trade con storico 100% reale ESCLUDE un problema di copertura dati - la "
                              "causa e' strutturale/di configurazione, non di mercato o di dati.",
        },
        "root_cause": {
            "missing_input": "InpStrat_VolBreakoutConfirmed",
            "default_value_line": flag_line.strip(),
            "guard_in_signal_function": guard_line.strip(),
            "guard_location": "MQL5/Include/NEXUS_v1/NXS_Strategies.mqh, "
                              "NXS_Strat_VolatilityBreakoutConfirmed()",
            "effect": "Con InpStrat_VolBreakoutConfirmed=false (default), la funzione segnale ritorna "
                     "DIR_NONE IMMEDIATAMENTE, prima di valutare qualunque range/ATR/breakout - "
                     "indipendentemente da InpStrategySelector=56 (che era gia' corretto in tutte le "
                     "fasi precedenti).",
            "never_included_in_any_frozen_config": not flag_present_in_frozen_config,
            "checked_in_artifacts": ["7.8B prereg", "7.8C authorization", "7.8D manifest", "7.8E data freeze",
                                     "7.8F execution config", "7.8G reseal/run.ini"],
            "cross_check_pattern_is_consolidated": {
                "note": "InpStrat_<Nome> e' un pattern esistente e consolidato per OGNI strategia "
                       "dell'EA (non un caso isolato di VOLBRK) - alcuni default true, altri false per "
                       "strategie mai ancora verificate su MT5 (commento esplicito nel codice).",
                "sample_other_flags": other_strat_flags_sample,
            },
        },
        "why_this_is_not_a_valid_scientific_result": (
            "0 trade qui NON significa 'nessun breakout rilevato in ~3 anni di GOLD H4' (implausibile e "
            "contraddetto dal fast-structural test precedente, che aveva gia' rilevato eventi validi) - "
            "significa che il segnale non e' mai stato VALUTATO. Dichiarare INSUFFICIENT_SAMPLE o "
            "qualunque altro verdetto preregistrato su questo run sarebbe fuorviante e verrebbe scartato "
            "in qualunque revisione futura."
        ),
        "why_this_is_not_a_rescue": (
            "Nessun parametro di strategia (range_n, ATR multiplier, R multiplier, timeout), soglia di "
            "verdetto, o filtro e' stato toccato - la correzione riguarda ESCLUSIVAMENTE un prerequisito "
            "di abilitazione dell'EA (un master-switch on/off), mai discusso o incluso in nessuna fase "
            "precedente (7.8B-7.8F) per puro oversight, non per scelta. Analogo diretto al bug "
            "'Expert=Experts\\\\NEXUS_EA_v2' gia' scoperto e corretto in 7.8F: un difetto di "
            "configurazione tecnica scoperto SOLO eseguendo realmente il protocollo, non una scelta "
            "post-hoc per influenzare l'esito del segnale."
        ),
        "no_verdict_computed_on_this_run": True,
        "no_serious_validation_result_produced": True,
        "proposed_fix": {
            "action": "Aggiungere 'InpStrat_VolBreakoutConfirmed=true' alla sezione [TesterInputs] del "
                      "tester config - UNICO campo aggiunto, nessun altro valore modificato "
                      "(Expert/Symbol/Period/Model/FromDate/ToDate/Deposit/Currency/Leverage/"
                      "InpStrategySelector/InpProfileTF/InpUseStrategyProfiles/InpResearchUse* invariati).",
            "requires_second_run": True,
            "second_run_cost_estimate": "~2 ore reali (stesso ordine di grandezza del run appena "
                                        "completato, 801 giorni H4 Model=4 tick reali).",
        },
        "recommendation": "FERMARSI qui e attendere conferma esplicita prima di un secondo run - questa "
                          "correzione tocca il tester config gia' congelato/verificato attraverso 4 fasi "
                          "precedenti (7.8B-7.8F), e il principio di questo intero protocollo e' non "
                          "modificare mai silenziosamente una configurazione dopo aver visto un esito, "
                          "anche quando la modifica stessa e' innocua rispetto alla logica della "
                          "strategia.",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    out_path = os.path.join(PHASE78G_DIR, "volatility_breakout_zero_trade_root_cause_v1.json")
    save_json(out_path, doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(f"total_trades_observed={payload['observed_fact']['total_trades_in_official_report']}")
    print(f"history_quality={payload['observed_fact']['history_quality']}")
    print(f"root_cause={payload['root_cause']['missing_input']}={payload['root_cause']['default_value_line']}")
    return doc


if __name__ == "__main__":
    main()
