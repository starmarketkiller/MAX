#!/usr/bin/env python3
"""Local Model Bake-Off V1 - Fase 13: pilot REALE con il modello scelto dal
bake-off (ministral-3:3b), sullo stesso task originale (backfill
temporal_concentration + exit_efficiency per BREAKOUT_ACC e ORDER_BLOCK).

Differenze deliberate rispetto al pilot v1 (fase precedente, fallito 4/4):
1. NESSUN file di riferimento di stile nel prompt (causa nota di copia
   letterale di identificatori dal progetto invece di astrazione allo
   schema dato esplicito - lezione della fase precedente).
2. Harness deterministico di import/invocazione fornito DALL'HARNESS, non
   richiesto al modello (gia' validato nei task E1/E2 del bake-off).
3. exit_efficiency definito qui con una formula esplicita e verificabile:
   frazione della distanza entry->TP effettivamente catturata da
   entry->exit (segno dipendente dalla direzione) - un proxy quantitativo
   comparabile (non identico) alla nota qualitativa gia' scritta per
   LIQ_SWEEP nella Cross-Strategy Synthesis (Phase 7.26).

Regola del task: Claude fa SOLO i passi deterministici (caricare/normalizzare
i dati, costruire il prompt, chiamare il modello, eseguire in sandbox,
verificare indipendentemente) - MAI la logica di aggregazione al posto del
worker. Max 1 retry delimitato per fallimento, poi escalation, mai loop."""
import json
import os
import subprocess
import sys
import time

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))
PHASE721_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_21")
PHASE722_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_22")
PILOT_SANDBOX_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_28")

sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

import requests  # noqa: E402

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "ministral-3:3b"


def _dt(s):
    from datetime import datetime
    return datetime.strptime(s, "%Y.%m.%d %H:%M:%S")


def _load_breakout_acc_events():
    sys.path.insert(0, PHASE721_DIR)
    from nxs_breakoutacc_dataset_loader import load_opened_events, net_pnl  # noqa: E402
    events = load_opened_events()
    out = []
    for e in events:
        out.append({"entry_time": e["entry_fill_time"], "net_pnl": net_pnl(e),
                   "entry_price": e["entry_fill_price"], "exit_price": e["exit_fill_price"],
                   "entry_tp": e["entry_tp"], "direction": e["direction"]})
    return out


def _load_order_block_events():
    with open(os.path.join(PHASE722_DIR, "canonical_economic_dataset_v1.json"), encoding="utf-8") as f:
        payload = json.load(f)["payload"]
    out = []
    for e in payload["events"]:
        out.append({"entry_time": e["entry_time"], "net_pnl": e["net_pnl"],
                   "entry_price": e["entry_price"], "exit_price": e["exit_price"],
                   "entry_tp": e["entry_tp"], "direction": e["direction"]})
    return out


def _build_prompt_temporal(strategy_name, events):
    events_json = json.dumps([{"entry_time": e["entry_time"], "net_pnl": e["net_pnl"]}
                              for e in events], ensure_ascii=False)
    return f"""Scrivi SOLO una funzione Python (nessuna spiegazione, nessun markdown fence):

def compute_temporal_concentration(events):

Specifica ESATTA:
- events e' una lista di dict con chiavi 'entry_time' (stringa 'YYYY.MM.DD HH:MM:SS')
  e 'net_pnl' (float) - SOLO queste due chiavi, accedi ad esse come chiavi dict
  (es. e['entry_time']), NON come funzioni.
- Raggruppa gli eventi per ANNO (i primi 4 caratteri di entry_time).
- Ritorna un dict Python con, per ogni anno (come stringa), un dict con
  'n_trades' (int), 'net_pnl_sum' (float), 'win_rate' (float, frazione di
  eventi con net_pnl > 0 in quell'anno).
- Aggiungi anche due chiavi top-level: 'years_with_positive_net' (quanti anni
  hanno net_pnl_sum > 0) e 'years_total_with_at_least_1_trade' (numero di anni
  totali presenti).
- Non importare nulla: usa solo dict/list/string built-in di Python
  (per l'anno usa entry_time[:4], NON datetime).

Dati di input reali su cui verra' poi chiamata la funzione (strategia: {strategy_name}, {len(events)} eventi):
{events_json[:3000]}"""


def _build_prompt_exit_efficiency(strategy_name, events):
    events_json = json.dumps([{"entry_price": e["entry_price"], "exit_price": e["exit_price"],
                              "entry_tp": e["entry_tp"], "direction": e["direction"]}
                             for e in events], ensure_ascii=False)
    return f"""Scrivi SOLO una funzione Python (nessuna spiegazione, nessun markdown fence):

def compute_exit_efficiency(events):

Specifica ESATTA:
- events e' una lista di dict con chiavi 'entry_price' (float), 'exit_price'
  (float), 'entry_tp' (float, take-profit teorico), 'direction' (stringa
  'BUY' o 'SELL') - accedi ad esse come chiavi dict, NON come funzioni.
- Per ogni evento calcola quanta parte della distanza teorica fino al
  take-profit e' stata REALMENTE catturata dall'uscita effettiva:
  - se direction=='BUY': captured = exit_price - entry_price;
    available = entry_tp - entry_price
  - se direction=='SELL': captured = entry_price - exit_price;
    available = entry_price - entry_tp
  - ratio = captured / available (salta l'evento, non includerlo nella
    media, se available == 0)
- Ritorna un dict Python con: 'mean_exit_efficiency_ratio' (float, media dei
  ratio calcolati), 'n_events_used' (int, quanti eventi hanno contribuito
  alla media), 'n_events_skipped_zero_available' (int).
- Non importare nulla: usa solo built-in di Python.

Dati di input reali su cui verra' poi chiamata la funzione (strategia: {strategy_name}, {len(events)} eventi):
{events_json[:3000]}"""


def _extract_code(text, marker):
    text = text.strip()
    if "```" in text:
        parts = text.split("```")
        for p in parts:
            if marker in p:
                return p.replace("python", "", 1).strip() if p.strip().startswith("python") else p.strip()
    return text


def _call_model(prompt, timeout=180):
    t0 = time.time()
    try:
        resp = requests.post(OLLAMA_URL, json={"model": MODEL, "prompt": prompt, "stream": False,
                                              "options": {"num_ctx": 8192}}, timeout=timeout)
        data = resp.json()
        return data.get("response", ""), round(time.time() - t0, 2)
    except Exception as e:  # noqa: BLE001 - un timeout/errore di rete e' un fallimento del
        # tentativo (eleggibile per il retry delimitato), non un crash dello script - stesso
        # principio del bug harness gia' corretto nel pilot v1 della fase precedente.
        return f"[HARNESS_ERROR: {e}]", round(time.time() - t0, 2)


def _reference_temporal_concentration(events):
    by_year = {}
    for e in events:
        y = e["entry_time"][:4]
        by_year.setdefault(y, []).append(e["net_pnl"])
    per_year = {y: {"n_trades": len(v), "net_pnl_sum": sum(v),
                   "win_rate": sum(1 for p in v if p > 0) / len(v)}
               for y, v in by_year.items()}
    out = dict(per_year)
    out["years_with_positive_net"] = sum(1 for v in per_year.values() if v["net_pnl_sum"] > 0)
    out["years_total_with_at_least_1_trade"] = len(per_year)
    return out


def _reference_exit_efficiency(events):
    ratios = []
    skipped = 0
    for e in events:
        if e["direction"] == "BUY":
            captured = e["exit_price"] - e["entry_price"]
            available = e["entry_tp"] - e["entry_price"]
        else:
            captured = e["entry_price"] - e["exit_price"]
            available = e["entry_price"] - e["entry_tp"]
        if available == 0:
            skipped += 1
            continue
        ratios.append(captured / available)
    return {"mean_exit_efficiency_ratio": sum(ratios) / len(ratios) if ratios else None,
           "n_events_used": len(ratios), "n_events_skipped_zero_available": skipped}


def _run_in_sandbox(fname, code, marker, invocation_events, invocation_fn_call):
    os.makedirs(PILOT_SANDBOX_DIR, exist_ok=True)
    path = os.path.join(PILOT_SANDBOX_DIR, fname)
    invocation = f"\nevents = {json.dumps(invocation_events)}\nprint(json.dumps({invocation_fn_call}))\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write("import json\n\n" + code + invocation)
    try:
        r = subprocess.run([sys.executable, path], capture_output=True, text=True, timeout=60,
                          cwd=PILOT_SANDBOX_DIR)
    except subprocess.TimeoutExpired:
        return {"returncode": None, "stdout": "", "stderr": "TIMEOUT esecuzione sandbox (60s)"}
    return {"returncode": r.returncode, "stdout": r.stdout[-2000:], "stderr": r.stderr[-2000:]}


def _attempt_task(task_label, strategy_name, events, prompt_builder, marker, fn_call_template,
                  reference_fn, retry_allowed=True):
    prompt = prompt_builder(strategy_name, events)
    raw_response, wall = _call_model(prompt)
    code = _extract_code(raw_response, marker)
    fname = f"_pilot_v2_{MODEL.replace(':', '-')}_{strategy_name.lower()}_{task_label}.py"
    exec_result = _run_in_sandbox(fname, code, marker, events, fn_call_template)
    expected = reference_fn(events)
    parsed = None
    matches = False
    if exec_result["returncode"] == 0:
        try:
            parsed = json.loads(exec_result["stdout"].strip().splitlines()[-1])
            matches = parsed == expected
        except (json.JSONDecodeError, IndexError):
            pass
    attempt = {"wall_seconds": wall, "raw_model_response": raw_response, "extracted_code": code,
              "execution": exec_result, "parsed_output": parsed, "expected_output": expected,
              "matches_independent_verification": matches,
              "pilot_task_passed": exec_result["returncode"] == 0 and matches}
    if attempt["pilot_task_passed"] or not retry_allowed:
        attempt["retry_used"] = False
        return attempt
    print(f"    [{task_label}/{strategy_name}] primo tentativo fallito, 1 RETRY delimitato (stesso "
         "task, nessuna modifica di scope, per Routing Policy)...")
    retry_attempt = _attempt_task(task_label, strategy_name, events, prompt_builder, marker,
                                  fn_call_template, reference_fn, retry_allowed=False)
    retry_attempt["retry_used"] = True
    retry_attempt["first_attempt"] = attempt
    return retry_attempt


def run_pilot():
    breakout_events = _load_breakout_acc_events()
    order_block_events = _load_order_block_events()
    result = {"model": MODEL, "sandbox_dir": PILOT_SANDBOX_DIR, "attempts": {}}

    for strategy_name, events in (("BREAKOUT_ACC", breakout_events), ("ORDER_BLOCK", order_block_events)):
        print(f"  Pilot v2: {strategy_name} - temporal_concentration...")
        temporal = _attempt_task(
            "temporal", strategy_name, events, _build_prompt_temporal,
            "def compute_temporal_concentration", "compute_temporal_concentration(events)",
            _reference_temporal_concentration)
        print(f"    -> passed={temporal['pilot_task_passed']}")

        print(f"  Pilot v2: {strategy_name} - exit_efficiency...")
        exit_eff = _attempt_task(
            "exitfx", strategy_name, events, _build_prompt_exit_efficiency,
            "def compute_exit_efficiency", "compute_exit_efficiency(events)",
            _reference_exit_efficiency)
        print(f"    -> passed={exit_eff['pilot_task_passed']}")

        result["attempts"][strategy_name] = {"temporal_concentration": temporal,
                                            "exit_efficiency": exit_eff}

    result["overall_pilot_passed"] = all(
        a["temporal_concentration"]["pilot_task_passed"] and a["exit_efficiency"]["pilot_task_passed"]
        for a in result["attempts"].values())
    return result


def main():
    payload = run_pilot()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(ORCH_DIR, "pilot_run_v2_result_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path}")
    print(f"overall_pilot_passed: {payload['overall_pilot_passed']}")


if __name__ == "__main__":
    main()
