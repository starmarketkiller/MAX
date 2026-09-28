#!/usr/bin/env python3
"""Local Model Bake-Off V1 - Fase 9: probe minimo di tool-calling reale via
l'endpoint /api/chat di Ollama (non /api/generate - il tool-calling nativo
di Ollama richiede la chat API con un campo 'tools'). Un solo scenario
semplice: chiediamo di calcolare win_rate su una lista di trade, offrendo
UNA funzione-tool che lo fa - il modello deve invocarla con argomenti
strutturati corretti, non calcolarla lui stesso a testo libero.

Se il modello non supporta tool calling nativo (nessun tool_calls nella
risposta, o crash/errore), classificato TEXT_ONLY_OR_LIMITED_AGENT_USE per
quel modello - non forzato, per istruzione esplicita del task."""
import json
import os
import sys
import time

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

import requests  # noqa: E402

OLLAMA_CHAT_URL = "http://127.0.0.1:11434/api/chat"

TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "compute_win_rate",
        "description": "Calcola la percentuale di trade vincenti (net_pnl > 0) su una lista di trade.",
        "parameters": {
            "type": "object",
            "properties": {
                "trades": {
                    "type": "array",
                    "description": "Lista di trade, ognuno con un campo net_pnl numerico.",
                    "items": {"type": "object", "properties": {"net_pnl": {"type": "number"}}}
                }
            },
            "required": ["trades"]
        }
    }
}

MESSAGES = [
    {"role": "user", "content": (
        "Ho questi 4 trade: [{'net_pnl': 10}, {'net_pnl': -5}, {'net_pnl': 3}, "
        "{'net_pnl': -1}]. Usa lo strumento disponibile per calcolare il win rate. "
        "Non calcolarlo tu a mano, invoca lo strumento.")}
]


def probe_model(model, timeout=180):
    t0 = time.time()
    try:
        resp = requests.post(OLLAMA_CHAT_URL, json={
            "model": model, "messages": MESSAGES, "tools": [TOOL_DEF], "stream": False,
        }, timeout=timeout)
        wall = time.time() - t0
        data = resp.json()
    except Exception as e:  # noqa: BLE001
        return {"error": str(e), "wall_seconds": round(time.time() - t0, 2),
               "tool_call_emitted": False, "classification": "TEXT_ONLY_OR_LIMITED_AGENT_USE"}

    message = data.get("message", {})
    tool_calls = message.get("tool_calls") or []
    tool_call_ok = False
    tool_call_args_valid = False
    if tool_calls:
        tool_call_ok = True
        try:
            fn = tool_calls[0].get("function", {})
            args = fn.get("arguments", {})
            if isinstance(args, str):
                args = json.loads(args)
            trades = args.get("trades")
            tool_call_args_valid = (fn.get("name") == "compute_win_rate" and isinstance(trades, list)
                                    and len(trades) == 4)
        except Exception:  # noqa: BLE001
            tool_call_args_valid = False

    classification = ("TOOL_USE_CAPABLE" if tool_call_ok and tool_call_args_valid
                      else "TOOL_USE_UNRELIABLE" if tool_call_ok
                      else "TEXT_ONLY_OR_LIMITED_AGENT_USE")
    return {"wall_seconds": round(wall, 2), "raw_message_content": message.get("content", "")[:500],
           "tool_calls_raw": tool_calls, "tool_call_emitted": tool_call_ok,
           "tool_call_args_valid": tool_call_args_valid, "classification": classification}


def _unload_model(model):
    """Vedi build_bakeoff_benchmark.py._unload_other_models - stesso fix OOM
    scoperto in questa fase (2+ modelli residenti insieme esauriscono la RAM)."""
    try:
        requests.post("http://127.0.0.1:11434/api/generate",
                     json={"model": model, "keep_alive": 0}, timeout=15)
    except Exception:  # noqa: BLE001
        pass


def main():
    models = sys.argv[1:] or ["qwen2.5:3b-instruct", "qwen2.5:7b-instruct", "qwen3:4b",
                              "ministral-3:3b", "gemma3:4b"]
    results = {}
    for i, m in enumerate(models):
        if i > 0:
            _unload_model(models[i - 1])
        print(f"probing tool-calling: {m}...")
        results[m] = probe_model(m)
        print(f"  -> {results[m].get('classification')}, tool_call_emitted="
             f"{results[m].get('tool_call_emitted')}, wall={results[m].get('wall_seconds')}s")
    payload = {"tool_definition_used": TOOL_DEF, "results": results,
              "measurement_note": "Probe singolo per modello (1 scenario) - sufficiente per "
                                 "classificare capacita' di tool-calling nativo affidabile "
                                 "sì/no, non una misura esaustiva di ogni possibile schema di "
                                 "tool."}
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(ORCH_DIR, "toolcalling_probe_results_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path}")


if __name__ == "__main__":
    main()
