#!/usr/bin/env python3
"""Orchestrator V1 - Local Runtime Setup, punto H/I: primo pilot REALE.
Claude (questo script, TIER 0) fa SOLO i passi deterministici: legge i
dati di input, costruisce il prompt, chiama il modello locale, salva
il suo output, lo esegue in sandbox, verifica il risultato. Il LAVORO
di scrittura del codice e' del modello locale (TIER 2) - se fallisce,
questo script lo DOCUMENTA, non lo corregge silenziosamente al posto
del worker (regola esplicita del task)."""
import json
import os
import subprocess
import sys
import time

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))
PHASE721_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_21")
PHASE722_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_22")
PHASE725_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_25")
PILOT_SANDBOX_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_28")

sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

import requests  # noqa: E402

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"


def _dt(s):
    from datetime import datetime
    return datetime.strptime(s, "%Y.%m.%d %H:%M:%S")


def _load_breakout_acc_events():
    sys.path.insert(0, PHASE721_DIR)
    from nxs_breakoutacc_dataset_loader import load_opened_events, net_pnl  # noqa: E402
    events = load_opened_events()
    return [{"entry_time": e["entry_fill_time"], "net_pnl": net_pnl(e)} for e in events]


def _load_order_block_events():
    with open(os.path.join(PHASE722_DIR, "canonical_economic_dataset_v1.json"), encoding="utf-8") as f:
        payload = json.load(f)["payload"]
    return [{"entry_time": e["entry_time"], "net_pnl": e["net_pnl"]} for e in payload["events"]]


def _reference_pattern_source():
    with open(os.path.join(PHASE725_DIR, "build_liq_sweep_temporal_robustness.py"), encoding="utf-8") as f:
        return f.read()


def _build_prompt(strategy_name, events):
    ref = _reference_pattern_source()
    events_json = json.dumps(events, ensure_ascii=False)
    return f"""Scrivi SOLO codice Python (nessuna spiegazione prima o dopo, nessun markdown fence),
una singola funzione chiamata `compute_temporal_concentration(events)` che:
- riceve una lista di dict con chiavi 'entry_time' (formato 'YYYY.MM.DD HH:MM:SS') e 'net_pnl' (float)
- raggruppa gli eventi per ANNO (dal campo entry_time)
- ritorna un dict Python con, per ogni anno (come stringa), un dict con 'n_trades', 'net_pnl_sum',
  'win_rate' (frazione di eventi con net_pnl > 0)
- ritorna anche una chiave top-level 'years_with_positive_net' (conteggio anni con net_pnl_sum > 0)
  e 'years_total_with_at_least_1_trade'

Ecco un ESEMPIO di uno stile di codice gia' usato in questo progetto per lo stesso tipo di calcolo
(riferimento di stile, NON copiarlo interamente - qui serve solo la funzione richiesta sopra):

```python
{ref[:2000]}
```

Dati di input reali su cui la funzione DEVE poi essere chiamata (strategia: {strategy_name}):
{events_json[:3000]}

Scrivi SOLO la funzione Python `compute_temporal_concentration`, poi una riga che la chiama sui
dati sopra e stampa il risultato con `print(json.dumps(risultato))`. Nessun altro testo."""


def _extract_code(text):
    text = text.strip()
    if "```" in text:
        parts = text.split("```")
        for p in parts:
            if "def compute_temporal_concentration" in p:
                return p.replace("python", "", 1).strip() if p.strip().startswith("python") else p.strip()
    return text


def _call_model(model, prompt, num_ctx=8192, timeout=600):
    t0 = time.time()
    resp = requests.post(OLLAMA_URL, json={"model": model, "prompt": prompt, "stream": False,
                                          "options": {"num_ctx": num_ctx}}, timeout=timeout)
    data = resp.json()
    return data.get("response", ""), round(time.time() - t0, 2)


def run_pilot(model="qwen2.5:7b-instruct"):
    os.makedirs(PILOT_SANDBOX_DIR, exist_ok=True)

    breakout_events = _load_breakout_acc_events()
    order_block_events = _load_order_block_events()

    result = {"model": model, "sandbox_dir": PILOT_SANDBOX_DIR, "attempts": {}}

    for strategy_name, events in (("BREAKOUT_ACC", breakout_events), ("ORDER_BLOCK", order_block_events)):
        prompt = _build_prompt(strategy_name, events)
        raw_response, wall_seconds = _call_model(model, prompt)
        code = _extract_code(raw_response)

        # Boilerplate DETERMINISTICO (TIER 0 - orchestrazione, non logica scientifica):
        # import di utilita' + l'invocazione/stampa - la responsabilita' del worker locale resta
        # SOLO la funzione compute_temporal_concentration, non l'impalcatura attorno.
        events_literal = json.dumps(events)
        harness_boilerplate = (
            "import json\n"
            "from datetime import datetime\n"
            "from collections import defaultdict\n\n"
            "def _dt(s):\n"
            "    return datetime.strptime(s, '%Y.%m.%d %H:%M:%S')\n\n"
        )
        invocation = (f"\n\nevents = {events_literal}\n"
                     "print(json.dumps(compute_temporal_concentration(events)))\n")

        code_path = os.path.join(PILOT_SANDBOX_DIR, f"_pilot_generated_{strategy_name.lower()}.py")
        with open(code_path, "w", encoding="utf-8") as f:
            f.write(harness_boilerplate + code + invocation)

        exec_result = subprocess.run([sys.executable, code_path], capture_output=True, text=True,
                                     timeout=60, cwd=PILOT_SANDBOX_DIR)

        parsed_output = None
        parse_error = None
        if exec_result.returncode == 0:
            try:
                parsed_output = json.loads(exec_result.stdout.strip().splitlines()[-1])
            except (json.JSONDecodeError, IndexError) as e:
                parse_error = str(e)

        # verifica indipendente: ricalcolo IO stesso il risultato atteso, confronto.
        expected = _reference_compute(events)
        matches_expected = parsed_output == expected if parsed_output is not None else False

        result["attempts"][strategy_name] = {
            "wall_seconds": wall_seconds, "code_path": code_path,
            "raw_model_response": raw_response, "extracted_code": code,
            "execution_returncode": exec_result.returncode,
            "execution_stdout": exec_result.stdout[-2000:],
            "execution_stderr": exec_result.stderr[-2000:],
            "parsed_output": parsed_output, "parse_error": parse_error,
            "expected_output_computed_independently_by_claude": expected,
            "matches_independent_verification": matches_expected,
            "pilot_task_passed": exec_result.returncode == 0 and matches_expected,
        }

    result["overall_pilot_passed"] = all(a["pilot_task_passed"] for a in result["attempts"].values())
    return result


def _reference_compute(events):
    """Calcolo di riferimento INDIPENDENTE (stesso identico schema atteso dal modello) -
    usato per verificare il codice generato dal worker, non per sostituirlo."""
    from collections import defaultdict
    by_year = defaultdict(list)
    for e in events:
        year = str(_dt(e["entry_time"]).year)
        by_year[year].append(e["net_pnl"])
    per_year = {y: {"n_trades": len(v), "net_pnl_sum": sum(v),
                   "win_rate": sum(1 for p in v if p > 0) / len(v)}
               for y, v in by_year.items()}
    years_positive = sum(1 for v in per_year.values() if v["net_pnl_sum"] > 0)
    out = dict(per_year)
    out["years_with_positive_net"] = years_positive
    out["years_total_with_at_least_1_trade"] = len(per_year)
    return out


def main():
    model = sys.argv[1] if len(sys.argv) > 1 else "qwen2.5:7b-instruct"
    payload = run_pilot(model)
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(ORCH_DIR, "pilot_run_result_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path}")
    print(f"  overall_pilot_passed: {payload['overall_pilot_passed']}")
    for strat, a in payload["attempts"].items():
        print(f"  {strat}: passed={a['pilot_task_passed']} returncode={a['execution_returncode']} "
             f"matches_verification={a['matches_independent_verification']}")


if __name__ == "__main__":
    main()
