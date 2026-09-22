#!/usr/bin/env python3
"""Phase 7.8I - Technical preflight (punto 7): un mini-run BREVE (1 mese,
2024.06.01->2024.07.01, dentro la FRESH window) con il config di ricerca
completo, PRIMA di spendere ~2 ore sul run completo. Verifica SOLO fatti
tecnici (nuovo EX5 caricato, Research Mode riconosciuto, preflight
passato, la funzione strategia realmente raggiunta) - il risultato di
mercato di questo mini-run NON e' usato come evidenza scientifica.
"""
import os
import re
import sys

PHASE78I_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE78I_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import file_sha256, load_json, save_json, wrap_with_provenance  # noqa: E402

TERM_DATA = r"C:\Users\User\AppData\Roaming\MetaQuotes\Terminal\7F8EC41F011085EB9C65165AE426B5A6"
COMMON_FILES = r"C:\Users\User\AppData\Roaming\MetaQuotes\Terminal\Common\Files"
CONFIG_DOC_PATH = os.path.join(PHASE78I_DIR, "volatility_breakout_research_config_v1.json")


def extract_after(label, text):
    idx = text.find(label)
    if idx < 0:
        return None
    m = re.search(r"<b>(.*?)</b>", text[idx: idx + 300])
    return m.group(1).strip() if m else None


def build():
    report_path = os.path.join(TERM_DATA, "volbrk_preflight_run3.htm")
    with open(report_path, encoding="utf-16", errors="ignore") as f:
        report_text = f.read()
    total_trades = extract_after("Operazioni di Trading Totali", report_text)
    history_quality = extract_after("dello Storico", report_text)

    trades_csv_path = os.path.join(COMMON_FILES, "NEXUS_trades.csv")
    with open(trades_csv_path, encoding="utf-16") as f:
        trades_raw = f.read()
    strategy_name_in_trade_log = "VOLATILITY_BREAKOUT_CONFIRMED" in trades_raw
    reason_confirmed_present = "VolBreakout_confirmed" in trades_raw

    journal_path = os.path.join(TERM_DATA, "Tester", "logs", "20260922.log")
    with open(journal_path, encoding="utf-16-le", errors="ignore") as f:
        journal = f.read()
    idx = journal.rfind("[RESEARCH][INIT]")
    init_line = journal[idx: idx + 260] if idx >= 0 else None
    fatal_count = journal.count("[RESEARCH][FATAL]")

    config_doc = load_json(CONFIG_DOC_PATH)
    new_ex5_sha256_expected = config_doc["payload"]["recompile_evidence"]["new_ex5_sha256"]
    ex5_path = os.path.join(TERM_DATA, "MQL5", "Experts", "NEXUS_EA_v2.ex5")
    ex5_sha256_now = file_sha256(ex5_path)

    checks = {
        "new_ex5_actually_loaded": ex5_sha256_now == new_ex5_sha256_expected,
        # [RESEARCH][INIT] e' stampato SOLO se NXS_IsResearchMode()==true (NXS_ResearchMode.mqh:114,
        # "if(!NXS_IsResearchMode()) return;") - la sua stessa esistenza E' la prova diretta che
        # InpResearchMode e' stato riconosciuto true dal binario in esecuzione, non un testo da cercare
        # dentro la riga stessa (che non ripete il nome del parametro).
        "research_mode_recognized": init_line is not None,
        "strat_volbreakout_flag_recognized": strategy_name_in_trade_log,
        "selector_56_recognized": "selector=56" in init_line if init_line else False,
        "research_preflight_passed_no_fatal": fatal_count == 0,
        "strategy_router_reached_volbrk_code_path": strategy_name_in_trade_log and reason_confirmed_present,
        "history_quality_100pct": history_quality == "100% ticks reali",
    }
    all_passed = all(checks.values())

    payload = {
        "phase": "7.8I",
        "artifact_role": "TECHNICAL_EXECUTION_PREFLIGHT",
        "candidate_id": "VOLATILITY_BREAKOUT_CONFIRMED",
        "scope_note": "Mini-run BREVE (1 mese) - verifica SOLO fatti tecnici, NON un risultato di mercato "
                      "e NON usato come evidenza scientifica per il verdetto preregistrato.",
        "preflight_window": {"from": "2024.06.01", "to": "2024.07.01"},
        "observed": {
            "total_trades_in_preflight_report": total_trades,
            "history_quality": history_quality,
            "research_init_line_from_journal": init_line,
            "fatal_research_errors_count": fatal_count,
        },
        "checks": checks,
        "verdict": "TECHNICAL_EXECUTION_PREFLIGHT_PASS" if all_passed else "TECHNICAL_EXECUTION_PREFLIGHT_BLOCK",
        "note_on_selector_name_fallback": "Il log [RESEARCH][INIT] stampa 'strategy=selector_56' (fallback "
            "di NXS_ResearchSelectorName, che non mappa ancora il case 56) - non trattato come fallimento: "
            "i trade REALI nel log CSV mostrano esplicitamente strategy=VOLATILITY_BREAKOUT_CONFIRMED "
            "(impostato direttamente nella funzione segnale, non tramite quella lookup) e "
            "reason=VolBreakout_confirmed, provando che il vero codice della strategia e' stato raggiunto.",
        "not_used_as_scientific_evidence": True,
        "not_the_full_serious_validation": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    out_path = os.path.join(PHASE78I_DIR, "volatility_breakout_technical_preflight_v1.json")
    save_json(out_path, doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(f"verdict={payload['verdict']}")
    for k, v in payload["checks"].items():
        print(f"  check[{k}]={v}")
    return doc


if __name__ == "__main__":
    main()
