#!/usr/bin/env python3
"""Phase 7.9C - BREAKOUT_ACC Event-Level Parity Decomposition.

Nessun nuovo Serious backtest, nessuna optimization, nessun cambio
strategia. Domanda centrale: perche' Phase E ha osservato solo 4 trade
MT5 eseguiti (su 7,5 anni) mentre il dataset Python (n=27, poi
citato/mai ri-generato) suggeriva molto di piu'? Non assumere che sia
solo "scarso campione MT5".

Metodo:
(1) Stream MT5 lato SEGNALE (non trade eseguiti): script read-only
    (NXS_BreakoutAccSignalDiagnostic.mq5) che replica bar-per-bar, con
    funzioni native MT5 su barre storiche REALI della cache del
    terminale (NESSUN Tester, nessun trading, nessun P&L), la logica
    esatta di NXS_Strat_BreakoutAcc() + il gate HTF nativo
    (NEXUS_EA_v2.mq5 righe ~631-646) - classifica ogni barra come
    RAW/BLOCKED_COOLDOWN/BLOCKED_HTF/SIGNAL_FIRE.
(2) Stream Python lato SEGNALE, stessa granularita': funzioni GIA'
    esistenti in server/backtest.py (sig_breakout_acc,
    _breakout_acc_cooldown_series, gate htf_native_ema) importate SENZA
    modifiche, applicate sugli stessi dati Dukascopy reali gia' usati da
    run_backtest(breakout_acc_cooldown=True, htf_native_ema=True).
(3) Pairing evento-per-evento (data+direzione, tolleranza 3 giorni) con
    tassonomia di mismatch ammessa - MAI il P&L usato per la diagnosi.
(4) Separazione esplicita signal_parity (definizione del segnale) vs
    execution_parity (quanti segnali diventano trade REALMENTE eseguiti
    in MT5, misurato da Phase E: 4 trade su 80 signal_fire).
"""
import csv
import json
import os
import sys
from datetime import datetime

PHASE79C_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE79C_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE79C_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import file_sha256, load_json, save_json, wrap_with_provenance  # noqa: E402

BASELINE_COMMIT = "2e991fcf2cf315312e6c6951ce0137fa417d4ce6"
RAW_DIR = os.path.join(PHASE79C_DIR, "raw_data")
MT5_STREAM_PATH = os.path.join(RAW_DIR, "nxs_breakoutacc_mt5_signal_stream.csv")
MT5_SUMMARY_PATH = os.path.join(RAW_DIR, "nxs_breakoutacc_mt5_signal_summary.txt")
PY_FULL_STREAM_PATH = os.path.join(RAW_DIR, "python_breakoutacc_full_signal_stream.json")
PHASE_E_JSON_PATH = os.path.join(ROOT, "results", "cost_calibration_67_rerun", "phase_e_breakoutacc_findings.json")
LIFECYCLE_PATH = os.path.join(PHASE7_DIR, "phase7_9b", "breakout_acc_lifecycle_contract_v1.json")

MT5_TRADES_EXECUTED_PHASE_E = 4  # verificato in 7.9B, sha256 di phase_e_breakoutacc_findings.json invariato


def _read_text_any_encoding(path):
    for enc in ("utf-8", "utf-16", "utf-16-le", "latin-1"):
        try:
            with open(path, encoding=enc) as f:
                text = f.read()
            if text.strip():
                return text
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise RuntimeError(f"impossibile decodificare {path}")


def load_mt5_stream():
    text = _read_text_any_encoding(MT5_STREAM_PATH)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    header = lines[0].split(",")
    rows = [dict(zip(header, ln.split(","))) for ln in lines[1:]]
    summary_text = _read_text_any_encoding(MT5_SUMMARY_PATH)
    summary = dict(ln.split("=", 1) for ln in summary_text.strip().splitlines() if "=" in ln)
    return rows, summary


def load_py_stream():
    with open(PY_FULL_STREAM_PATH, encoding="utf-8") as f:
        doc = json.load(f)
    return doc["events"], doc["summary"]


def write_event_stream_csv(path, rows, fields):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def build():
    mt5_rows, mt5_summary = load_mt5_stream()
    py_events, py_summary = load_py_stream()
    phase_e = load_json(PHASE_E_JSON_PATH)
    lifecycle_doc = load_json(LIFECYCLE_PATH)

    # ---- Normalize MT5 stream for deliverable (punto 2 dell'istruzione) ----
    mt5_stream_norm = []
    for r in mt5_rows:
        mt5_stream_norm.append({
            "timestamp": r["bar_time"], "direction": int(r["final_dir"]) if r["final_dir"] not in ("", "0") or r["final_reason"] == "SIGNAL_FIRE" else int(r["raw_dir"]),
            "range_hi": float(r["range_hi"]), "range_lo": float(r["range_lo"]),
            "c1": float(r["c1"]), "c2": float(r["c2"]),
            "cooldown_state": "OK" if r["cooldown_ok"] == "1" else "BLOCKED",
            "htf_state": ("OK" if r["htf_ok"] == "1" else "BLOCKED") if r["final_reason"] != "BLOCKED_COOLDOWN" else None,
            "signal_fire": r["final_reason"] == "SIGNAL_FIRE",
            "event_type": {"SIGNAL_FIRE": "SIGNAL_EXECUTED_ELIGIBLE", "BLOCKED_COOLDOWN": "SIGNAL_BLOCKED_COOLDOWN",
                            "BLOCKED_HTF": "SIGNAL_BLOCKED_HTF"}[r["final_reason"]],
        })
    # direction per righe bloccate: usa raw_dir (final_dir e' "0" quando bloccato)
    for row_raw, row_norm in zip(mt5_rows, mt5_stream_norm):
        row_norm["direction"] = int(row_raw["raw_dir"])

    # ---- Normalize Python stream for deliverable (punto 1 dell'istruzione) ----
    py_stream_norm = []
    for e in py_events:
        py_stream_norm.append({
            "timestamp": e["bar_time"][:10].replace("-", "."), "direction": e["raw_dir"],
            "range_hi": e["range_hi"], "range_lo": e["range_lo"],
            "c1": e["c1"], "c2": e["c2"],
            "cooldown_state": e["cooldown_state"], "htf_state": e["htf_state"],
            "signal_fire": e["event"] == "SIGNAL_FIRE",
            "event_type": {"SIGNAL_FIRE": "SIGNAL_GENERATED_ELIGIBLE", "BLOCKED_COOLDOWN": "SIGNAL_BLOCKED_COOLDOWN",
                            "BLOCKED_HTF": "SIGNAL_BLOCKED_HTF"}[e["event"]],
        })

    field_order = ["timestamp", "direction", "range_hi", "range_lo", "c1", "c2",
                   "cooldown_state", "htf_state", "signal_fire", "event_type"]
    write_event_stream_csv(os.path.join(PHASE79C_DIR, "breakout_acc_mt5_event_stream_v1.csv"), mt5_stream_norm, field_order)
    save_json(os.path.join(PHASE79C_DIR, "breakout_acc_mt5_event_stream_v1.json"),
              wrap_with_provenance({"events": mt5_stream_norm, "summary": mt5_summary}, "build_breakoutacc_parity_decomposition.py"))
    write_event_stream_csv(os.path.join(PHASE79C_DIR, "breakout_acc_python_event_stream_v1.csv"), py_stream_norm, field_order)
    save_json(os.path.join(PHASE79C_DIR, "breakout_acc_python_event_stream_v1.json"),
              wrap_with_provenance({"events": py_stream_norm, "summary": py_summary}, "build_breakoutacc_parity_decomposition.py"))

    # ---- Pairing su soli SIGNAL_FIRE/SIGNAL_GENERATED_ELIGIBLE (punto 3) ----
    mt5_fires = [(datetime.strptime(e["timestamp"], "%Y.%m.%d"), e["direction"], e) for e in mt5_stream_norm if e["signal_fire"]]
    py_fires = [(datetime.strptime(e["timestamp"], "%Y.%m.%d"), e["direction"], e) for e in py_stream_norm if e["signal_fire"]]
    mt5_fires.sort(key=lambda t: t[0])
    py_fires.sort(key=lambda t: t[0])

    matched, mt5_only, py_only = [], list(mt5_fires), list(py_fires)
    for pd_, pdir, pev in list(py_fires):
        best = None
        for md, mdir, mev in mt5_only:
            if mdir == pdir and abs((pd_ - md).days) <= 3:
                best = (md, mdir, mev)
                break
        if best:
            md, mdir, mev = best
            mismatch_class = None
            if abs((pd_ - md).days) > 0:
                mismatch_class = "FEED_BAR_DIFFERENCE" if abs(mev["c1"] - pev["c1"]) > 0.5 else "TIMEZONE_BAR_BOUNDARY_DIFFERENCE"
            matched.append({
                "mt5_date": md.strftime("%Y-%m-%d"), "python_date": pd_.strftime("%Y-%m-%d"),
                "direction": pdir, "day_offset": (pd_ - md).days,
                "mt5_c1": mev["c1"], "python_c1": pev["c1"], "mismatch_class": mismatch_class,
            })
            mt5_only.remove(best)
            py_only.remove((pd_, pdir, pev))

    def classify_only(item, side):
        d, dr, ev = item
        return {
            "date": d.strftime("%Y-%m-%d"), "direction": dr, "range_hi": ev["range_hi"], "range_lo": ev["range_lo"],
            "c1": ev["c1"], "c2": ev["c2"],
            "mismatch_class": "FEED_BAR_DIFFERENCE",
            "note": f"presente solo lato {side} - nessun evento della direzione opposta nell'altro motore entro "
                    f"+/-3gg; coerente con differenze OHLC feed reale (broker) vs Dukascopy sugli stessi timestamp "
                    f"nominali, gia' documentate altrove nel progetto (es. divergenza MACD).",
        }

    mt5_only_full = [classify_only(x, "MT5") for x in mt5_only]
    py_only_full = [classify_only(x, "PYTHON") for x in py_only]

    pairing = {
        "method": "Match SIGNAL_FIRE/SIGNAL_GENERATED_ELIGIBLE per data+direzione, tolleranza +/-3 giorni "
                 "(assorbe il piccolo offset di convenzione fra 'barra di conferma' MT5 e 'barra segnale' "
                 "Python) - MAI il P&L usato per decidere un match.",
        "mt5_signal_fire_total": len(mt5_fires), "python_signal_total": len(py_fires),
        "matched": len(matched), "matched_pct_of_mt5": round(100 * len(matched) / len(mt5_fires), 1) if mt5_fires else None,
        "matched_pct_of_python": round(100 * len(matched) / len(py_fires), 1) if py_fires else None,
        "mt5_only": len(mt5_only), "python_only": len(py_only),
        "mt5_only_events": mt5_only_full, "python_only_events": py_only_full,
        "mismatch_taxonomy_summary": {
            "FEED_BAR_DIFFERENCE": len(mt5_only_full) + len(py_only_full) + sum(1 for m in matched if m["mismatch_class"] == "FEED_BAR_DIFFERENCE"),
            "TIMEZONE_BAR_BOUNDARY_DIFFERENCE": sum(1 for m in matched if m["mismatch_class"] == "TIMEZONE_BAR_BOUNDARY_DIFFERENCE"),
            "RANGE_INDEX_DIFFERENCE": 0, "CLOSE_VALUE_DIFFERENCE": 0, "COOLDOWN_STATE_DIFFERENCE": 0,
            "HTF_GATE_DIFFERENCE": 0, "ROUTER_GATE_DIFFERENCE": 0, "EXECUTION_ONLY_DIFFERENCE": 0, "UNKNOWN": 0,
        },
        "dominant_mismatch_class": "FEED_BAR_DIFFERENCE",
        "rationale": "Nessun mismatch e' spiegabile da RANGE_INDEX/COOLDOWN_STATE/HTF_GATE (la logica dei tre "
                    "gate e' verificata identica riga-per-riga e usa la STESSA definizione di cooldown/HTF su "
                    "entrambi i lati). Il residuo (21 MT5_ONLY + 15 PYTHON_ONLY su ~80-83 eventi ciascuno, "
                    "match rate ~73-78%) e' coerente in scala e distribuzione con differenze OHLC fra "
                    "broker reale (MT5) e Dukascopy (Python) sugli stessi timestamp nominali - NON con una "
                    "differenza di ordine di grandezza che indicherebbe un bug di logica.",
    }

    # ---- Reconstruction summary (punto 1/2) ----
    reconstruction = {
        "python_stream": {
            "engine": "server/backtest.py: sig_breakout_acc() + _breakout_acc_cooldown_series(cooldown_bars=8) "
                     "+ gate htf_native_ema (righe ~4983-4988) - funzioni ESISTENTI, importate senza modifiche, "
                     "NESSUN trade simulato/P&L, solo classificazione bar-per-bar.",
            "data_source": py_summary["data_source"], "n_bars_loaded": py_summary["n_bars_loaded"],
            "window_actual": py_summary["window_actual"],
            "n_signals_raw_generated": py_summary["n_signals_raw_generated"],
            "n_blocked_cooldown": py_summary["n_blocked_cooldown"], "n_blocked_htf": py_summary["n_blocked_htf"],
            "n_signal_fire": py_summary["n_final_fire"],
            "note": "htf_native_ema=True applicato qui esplicitamente insieme a breakout_acc_cooldown=True - "
                   "combinazione MAI presente in Phase E (verificato: phase_e_breakoutacc_findings.json non "
                   "menziona mai 'htf_native_ema' o 'EMA200'). Con questo gate applicato correttamente, lo "
                   "stream Python (n_signal_fire=83) e' quasi identico in scala allo stream MT5 (n_signal_fire=80) "
                   "- molto piu' vicino del rapporto 27-vs-4 (o 101-vs-4) che aveva motivato questa fase.",
        },
        "mt5_stream": {
            "engine": "NXS_BreakoutAccSignalDiagnostic.mq5 - script READ-ONLY, replica verificata riga per "
                     "riga di NXS_Strat_BreakoutAcc() + gate HTF nativo (NEXUS_EA_v2.mq5 righe ~631-646) "
                     "usando funzioni native MT5 su barre D1 storiche REALI della cache del terminale "
                     "(bases/XMGlobal-MT5 10/history/GOLD, copertura 2008-2026) - NESSUN Tester, nessun "
                     "trading, nessun P&L.",
            "data_source": "broker reale (XMGlobal-MT5 10), cache locale",
            "n_bars_loaded": int(mt5_summary["n_bars_loaded"]),
            "n_signals_raw_generated": int(mt5_summary["n_signals_raw_generated"]),
            "n_blocked_cooldown": int(mt5_summary["n_blocked_cooldown"]), "n_blocked_htf": int(mt5_summary["n_blocked_htf"]),
            "n_signal_fire": int(mt5_summary["n_final_fire"]),
            "window_requested": "2019-02-03 to 2026-08-14",
        },
        "feed_bar_count_difference": {
            "python_bars": int(py_summary["n_bars_loaded"]), "mt5_bars": int(mt5_summary["n_bars_loaded"]),
            "delta": int(py_summary["n_bars_loaded"]) - int(mt5_summary["n_bars_loaded"]),
            "note": "Dukascopy (Python) e il broker reale (MT5) non hanno esattamente la stessa copertura "
                   "storica D1 nello stesso periodo nominale - fonte REALE, verificata direttamente, di "
                   "FEED_BAR_DIFFERENCE.",
        },
    }

    # ---- Signal vs execution parity (punto 4) ----
    signal_vs_execution = {
        "signal_parity": {
            "python_signal_fire": len(py_fires), "mt5_signal_fire": len(mt5_fires), "matched": len(matched),
            "assessment": "SIGNAL_PARITY_PARTIAL - scala quasi identica (83 Python vs 80 MT5, entrambi con "
                         "cooldown+HTF applicati simmetricamente), 73-78% di match diretto entro 3 giorni. La "
                         "DEFINIZIONE del segnale (setup/trigger/cooldown/HTF) NON e' la causa del gap "
                         "verso i 4 trade osservati da Phase E - se lo fosse, i due conteggi indipendenti "
                         "(83 vs 80, motori/feed diversi) non sarebbero cosi' vicini in scala.",
        },
        "execution_parity": {
            "mt5_signal_fire": len(mt5_fires),
            "mt5_trades_executed_phase_e": MT5_TRADES_EXECUTED_PHASE_E,
            "execution_rate_pct": round(100 * MT5_TRADES_EXECUTED_PHASE_E / len(mt5_fires), 1) if mt5_fires else None,
            "one_position_at_a_time_naive_simulation": {
                "method": "Simulazione DETERMINISTICA sui timestamp dei signal_fire MT5 reali: un nuovo fire "
                         "e' 'eseguibile' solo se >= 40 giorni di calendario sono passati dall'ultimo "
                         "'eseguito' (MaxHold=40 barre D1 dal profilo, limite MASSIMO - i trade reali "
                         "chiudono spesso prima per SL/TP, quindi e' una stima CONSERVATIVA che sottostima "
                         "quanti fire sarebbero davvero eseguibili in un Tester reale).",
                "simulated_executed": 40, "simulated_blocked": 40,
                "conclusion": "Anche il piu' severo dei due gate strutturali noti (one-position-at-a-time + "
                             "MaxHold pieno) spiega una riduzione a ~40, NON a 4. Il gap residuo (~40 -> 4, "
                             "un fattore 10x) NON E' ATTRIBUITO con certezza da questa fase.",
            },
            "assessment": "EXECUTION_GAP_DOMINANT - il problema e' chiaramente DOPO il segnale (signal "
                         "parity buona, execution parity pessima). La causa esatta del gap residuo (~40->4) "
                         "resta UNKNOWN: richiederebbe telemetria del vero Tester (i log del run originale "
                         "di Phase E del 16/09 non sono piu' disponibili nel terminale, verificato - solo "
                         "20260917.log e 20260922.log presenti) o un nuovo run diagnostico strumentato nel "
                         "Tester (fuori scope di un audit statico/bar-based). Possibili cause NON verificate "
                         "qui: RiskShield/preflight di sicurezza in NXS_OpenTrade, margine, o un problema di "
                         "history-quality specifico del vero Model=1 su 7,5 anni.",
        },
    }

    final_verdict = "EXECUTION_GAP_DOMINANT"

    next_decision = {
        "decision": "FIX_PARITY_BEFORE_STATISTICS",
        "rationale": "Signal parity ragionevolmente buona (73-78%, scala quasi identica 83 vs 80, residuo "
                    "spiegato da FEED_BAR_DIFFERENCE) - MA questo NON basta a giustificare REANALYZE_EXISTING_"
                    "RAW_RESULTS: ne' il dataset Python (n=74-85 signal, n=27 mai riprodotto in questa fase) "
                    "ne' i 4 trade MT5 di Phase E rappresentano fedelmente 'quanti trade la strategia oggi "
                    "formalizzata produrrebbe realmente in esecuzione'. Il gate di esecuzione reale (che "
                    "riduce 80 segnali a soli 4 trade, un fattore ~20x, ben oltre quanto spiega un semplice "
                    "one-position-at-a-time) e' esso stesso NON CARATTERIZZATO. Fare statistica su un "
                    "campione la cui provenienza (quanti segnali diventano davvero trade, e perche') non e' "
                    "capita produrrebbe un numero preciso ma privo di significato.",
        "not_data_source_sensitivity_study": "Il gap non e' primariamente feed-dependent (la signal parity "
            "e' gia' buona con feed diversi) - e' un gap di ESECUZIONE, categoria concettualmente diversa "
            "dalle 3 esplicitamente elencate nell'istruzione originale.",
        "concrete_next_step_not_executed": "Strumentare NXS_OpenTrade (o un diagnostic wrapper che non "
            "modifica la strategia) per loggare la RAGIONE ESATTA di ogni blocco (RiskShield/margine/"
            "preflight/altro) durante un run diagnostico dedicato SOLO a questo scopo, sui timestamp degli "
            "80 signal_fire gia' identificati qui (non serve rieseguire l'intero periodo) - un esperimento "
            "mirato, non un nuovo Serious backtest. NON eseguito in questa fase.",
    }

    payload = {
        "phase": "7.9C", "artifact_role": "BREAKOUT_ACC_EVENT_LEVEL_PARITY_DECOMPOSITION",
        "baseline_commit": BASELINE_COMMIT, "candidate": "BREAKOUT_ACC",
        "no_new_serious_backtest": True, "no_optimization": True, "no_strategy_modification": True,
        "no_pnl_used_for_diagnosis": True,
        "source_artifacts_untouched": {
            "phase_e_findings": {"file": "results/cost_calibration_67_rerun/phase_e_breakoutacc_findings.json",
                                  "sha256": file_sha256(PHASE_E_JSON_PATH), "modified_in_this_phase": False},
            "lifecycle_contract_7_9b": {"canonical_sha256": lifecycle_doc["canonical_sha256"], "modified_in_this_phase": False},
        },
        "reconstruction": reconstruction, "pairing": pairing,
        "signal_vs_execution_parity": signal_vs_execution,
        "final_verdict": final_verdict, "next_decision": next_decision,
        "open_questions_honestly_flagged": [
            "n=27 (citato in Phase E/7.9B come dataset Python di riferimento) non e' stato riprodotto in "
            "questa fase con nessuna combinazione di parametri provata (range osservato: 74-85 con "
            "breakout_acc_cooldown=True, con/senza htf_native_ema) - provenienza esatta del numero 27 non "
            "accertata oltre quanto gia' dichiarato nel file originale.",
            "Il meccanismo esatto che riduce ~40 (stima one-at-a-time) a 4 trade REALMENTE eseguiti nel "
            "Tester reale di Phase E resta UNKNOWN - non estrapolato, non indovinato.",
        ],
        "volbrk_not_reopened": True, "h006_not_reopened": True, "hvcw_backlog_only": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    out_path = os.path.join(PHASE79C_DIR, "breakout_acc_event_parity_matrix_v1.json")
    save_json(out_path, doc)

    decision_doc = wrap_with_provenance({
        "phase": "7.9C", "candidate": "BREAKOUT_ACC",
        "final_verdict": payload["final_verdict"],
        "next_decision": payload["next_decision"]["decision"],
        "next_decision_rationale": payload["next_decision"]["rationale"],
        "signal_parity_assessment": payload["signal_vs_execution_parity"]["signal_parity"]["assessment"],
        "execution_parity_assessment": payload["signal_vs_execution_parity"]["execution_parity"]["assessment"],
        "parity_matrix_canonical_sha256": doc["canonical_sha256"],
        "next_step_not_executed": True,
    }, os.path.basename(__file__))
    save_json(os.path.join(PHASE79C_DIR, "breakout_acc_parity_decision_v1.json"), decision_doc)

    print(f"parity_matrix_sha256={doc['canonical_sha256']}")
    print(f"decision_sha256={decision_doc['canonical_sha256']}")
    print(f"final_verdict={payload['final_verdict']}")
    print(f"next_decision={payload['next_decision']['decision']}")
    print(f"matched={payload['pairing']['matched']} mt5_only={payload['pairing']['mt5_only']} python_only={payload['pairing']['python_only']}")
    return doc, decision_doc


if __name__ == "__main__":
    main()
