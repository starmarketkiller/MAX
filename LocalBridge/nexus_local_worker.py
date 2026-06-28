#!/usr/bin/env python3
"""
NEXUS Local MT5 Worker
======================
Script da eseguire sul PC Windows dell'utente. Esegue polling al backend
NEXUS cloud per ricevere comandi (compile EA, restart MT5, deploy files,
apply template) e li esegue localmente con MetaEditor / MetaTrader 5.

USAGE
-----
1. Installa Python 3.10+ su Windows
2. Configura `nexus_worker.config.json` (vedi sotto)
3. Esegui: python nexus_local_worker.py
4. (Opzionale) Crea task pianificato Windows o NSSM service per autostart

CONFIG FILE (nexus_worker.config.json) — same dir as this script:
{
  "backend_url":   "https://YOUR-NEXUS.preview.emergentagent.com",
  "bridge_token":  "NEXUS_BRIDGE_TOKEN_2026",
  "host_id":       "default",
  "mt5_path":      "C:/Program Files/MetaTrader 5/terminal64.exe",
  "metaeditor":    "C:/Program Files/MetaTrader 5/metaeditor64.exe",
  "mql5_include":  "C:/Users/<NAME>/AppData/Roaming/MetaQuotes/Terminal/<HASH>/MQL5/Include/NEXUS_v1",
  "mql5_experts":  "C:/Users/<NAME>/AppData/Roaming/MetaQuotes/Terminal/<HASH>/MQL5/Experts",
  "poll_sec":      3
}

DEPENDENCIES: only Python stdlib + 'requests' (pip install requests)
"""
from __future__ import annotations
import os
import sys
import json
import time
import shutil
import platform
import subprocess
import base64
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import requests
except ImportError:
    print("[NEXUS Worker] ERRORE: 'requests' non installato. Esegui:")
    print("   pip install requests")
    sys.exit(1)


CONFIG_PATH = Path(__file__).resolve().parent / "nexus_worker.config.json"
DEFAULT_CONFIG = {
    "backend_url":   "https://YOUR-NEXUS.preview.emergentagent.com",
    "bridge_token":  "NEXUS_BRIDGE_TOKEN_2026",
    "host_id":       "default",
    "mt5_path":      r"C:\Program Files\MetaTrader 5\terminal64.exe",
    "metaeditor":    r"C:\Program Files\MetaTrader 5\metaeditor64.exe",
    "mql5_include":  "",
    "mql5_experts":  "",
    "poll_sec":      3,
    "version":       "1.0.0",
}


def load_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        with open(CONFIG_PATH, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        print(f"[NEXUS Worker] Config file creato: {CONFIG_PATH}")
        print(f"[NEXUS Worker] Modifica i valori e riavvia.")
        sys.exit(0)
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)
    # fill missing with defaults
    for k, v in DEFAULT_CONFIG.items():
        cfg.setdefault(k, v)
    return cfg


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
def http_post(cfg: Dict[str, Any], path: str, body: Dict[str, Any]) -> Optional[Dict]:
    try:
        r = requests.post(
            f"{cfg['backend_url'].rstrip('/')}{path}",
            json=body,
            headers={"X-Nexus-Token": cfg["bridge_token"],
                     "Content-Type": "application/json"},
            timeout=15,
        )
        return r.json() if r.ok else None
    except Exception as e:
        print(f"[NEXUS Worker] HTTP POST {path} failed: {e}")
        return None


def http_get(cfg: Dict[str, Any], path: str, params: Optional[Dict] = None) -> Optional[Dict]:
    try:
        r = requests.get(
            f"{cfg['backend_url'].rstrip('/')}{path}",
            params=params or {},
            headers={"X-Nexus-Token": cfg["bridge_token"]},
            timeout=10,
        )
        return r.json() if r.ok else None
    except Exception as e:
        print(f"[NEXUS Worker] HTTP GET {path} failed: {e}")
        return None


def send_heartbeat(cfg: Dict[str, Any]):
    http_post(cfg, "/api/local_bridge/heartbeat", {
        "host_id":     cfg["host_id"],
        "version":     cfg["version"],
        "mt5_path":    cfg.get("mt5_path", ""),
        "metaeditor":  cfg.get("metaeditor", ""),
        "os":          platform.platform(),
    })


def ack(cfg: Dict[str, Any], cmd_id: str, ok: bool, result: Any = None, error: Optional[str] = None):
    http_post(cfg, "/api/local_bridge/ack", {
        "id":      cmd_id,
        "ok":      ok,
        "result":  result,
        "error":   error,
        "host_id": cfg["host_id"],
        "version": cfg["version"],
    })


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------
def handle_ping(cfg, payload) -> Dict[str, Any]:
    return {"pong": True, "ts": time.time()}


def handle_compile_ea(cfg, payload) -> Dict[str, Any]:
    """Compile the EA via metaeditor.exe /compile.

    payload (opzionale):
      {"source": "Experts/NEXUS_EA_v2.mq5",
       "log": "compile.log"}
    """
    me = cfg.get("metaeditor")
    if not me or not Path(me).exists():
        raise RuntimeError(f"metaeditor non trovato: {me}")
    src_rel = payload.get("source", r"Experts\NEXUS_EA_v2.mq5")
    # Determine the MQL5 base = parent of "Experts"
    experts_dir = Path(cfg["mql5_experts"])
    mql5_base = experts_dir.parent  # MQL5/
    src_abs = mql5_base / src_rel
    if not src_abs.exists():
        raise RuntimeError(f"source non trovato: {src_abs}")
    log_path = mql5_base / payload.get("log", "compile.log")
    cmd = [me, f"/compile:{src_abs}", f"/log:{log_path}", "/portable"]
    print(f"[NEXUS Worker] Running: {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    log_text = ""
    if log_path.exists():
        try:
            log_text = log_path.read_text(encoding="utf-16", errors="replace")
        except Exception:
            log_text = log_path.read_text(errors="replace")
    return {
        "exit_code":   r.returncode,
        "stdout":      r.stdout[-2000:] if r.stdout else "",
        "stderr":      r.stderr[-2000:] if r.stderr else "",
        "compile_log": log_text[-4000:],
    }


def handle_restart_mt5(cfg, payload) -> Dict[str, Any]:
    """Kill terminal64.exe and relaunch it."""
    if platform.system().lower() != "windows":
        return {"skipped": "only on Windows"}
    # taskkill
    subprocess.run(["taskkill", "/F", "/IM", "terminal64.exe"],
                    capture_output=True, text=True)
    time.sleep(3)
    mt5 = cfg.get("mt5_path")
    if not mt5 or not Path(mt5).exists():
        raise RuntimeError(f"MT5 non trovato: {mt5}")
    subprocess.Popen([mt5], close_fds=True)
    return {"restarted": True}


def handle_deploy_files(cfg, payload) -> Dict[str, Any]:
    """Deploy MQL5 files received via base64.

    payload:
    {
      "files": [
        {"target": "Include/NEXUS_v1/NXS_Inputs.mqh", "b64": "..."},
        {"target": "Experts/NEXUS_EA_v2.mq5",        "b64": "..."}
      ]
    }
    """
    experts_dir = Path(cfg["mql5_experts"])
    mql5_base = experts_dir.parent
    written = []
    for f in payload.get("files", []):
        target_rel = f["target"].replace("\\", "/")
        target_abs = mql5_base / target_rel
        target_abs.parent.mkdir(parents=True, exist_ok=True)
        data = base64.b64decode(f["b64"])
        # backup existing
        if target_abs.exists():
            backup = target_abs.with_suffix(target_abs.suffix + ".bak")
            shutil.copy2(target_abs, backup)
        target_abs.write_bytes(data)
        written.append(str(target_abs))
    return {"written": written}


def handle_open_chart(cfg, payload) -> Dict[str, Any]:
    """Launch MT5 with a specific profile/template (best-effort on Windows)."""
    mt5 = cfg.get("mt5_path")
    if not mt5 or not Path(mt5).exists():
        raise RuntimeError(f"MT5 non trovato: {mt5}")
    args = [mt5]
    profile = payload.get("profile")
    if profile:
        args += ["/profile:" + profile]
    subprocess.Popen(args, close_fds=True)
    return {"opened": True}


def handle_apply_template(cfg, payload) -> Dict[str, Any]:
    """Copy a .tpl into MQL5/Profiles/Templates (so user can apply manually).
    payload: {"name": "NEXUS_default.tpl", "b64": "..."}
    """
    name = payload.get("name", "NEXUS_default.tpl")
    if not name.endswith(".tpl"):
        name += ".tpl"
    experts_dir = Path(cfg["mql5_experts"])
    mql5_base = experts_dir.parent
    tpl_dir = mql5_base / "Profiles" / "Templates"
    tpl_dir.mkdir(parents=True, exist_ok=True)
    data = base64.b64decode(payload["b64"])
    target = tpl_dir / name
    target.write_bytes(data)
    return {"written": str(target)}


def handle_shell(cfg, payload) -> Dict[str, Any]:
    """Run a whitelisted shell command (restricted)."""
    cmd = payload.get("cmd", "")
    # Whitelist: only allow safe diagnostic commands
    allowed = ("dir", "ipconfig", "tasklist", "where", "echo")
    if not any(cmd.lower().startswith(a) for a in allowed):
        return {"error": "Command not whitelisted",
                 "allowed_prefixes": list(allowed)}
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    return {"exit_code": r.returncode,
            "stdout": r.stdout[-2000:], "stderr": r.stderr[-2000:]}


HANDLERS = {
    "ping":            handle_ping,
    "compile_ea":      handle_compile_ea,
    "restart_mt5":     handle_restart_mt5,
    "deploy_files":    handle_deploy_files,
    "open_chart":      handle_open_chart,
    "apply_template":  handle_apply_template,
    "shell":           handle_shell,
}


# ---------------------------------------------------------------------------
# Main poll loop
# ---------------------------------------------------------------------------
def main():
    cfg = load_config()
    print(f"[NEXUS Worker] v{cfg['version']} started")
    print(f"[NEXUS Worker] backend: {cfg['backend_url']}")
    print(f"[NEXUS Worker] host_id: {cfg['host_id']}")
    print(f"[NEXUS Worker] OS:      {platform.platform()}")

    send_heartbeat(cfg)
    last_heartbeat = time.time()

    while True:
        try:
            # Heartbeat ogni 30s
            if time.time() - last_heartbeat > 30:
                send_heartbeat(cfg)
                last_heartbeat = time.time()

            resp = http_get(cfg, "/api/local_bridge/poll",
                             {"host_id": cfg["host_id"]})
            if resp and resp.get("action"):
                cmd_id = resp["id"]
                action = resp["action"]
                payload = resp.get("payload", {}) or {}
                print(f"[NEXUS Worker] → {action} (id={cmd_id[:8]}) payload={payload}")
                handler = HANDLERS.get(action)
                if not handler:
                    ack(cfg, cmd_id, False, error=f"Unknown action: {action}")
                else:
                    try:
                        result = handler(cfg, payload)
                        ack(cfg, cmd_id, True, result=result)
                        print(f"[NEXUS Worker] ✓ {action} done")
                    except Exception as e:
                        print(f"[NEXUS Worker] ✗ {action} ERROR: {e}")
                        ack(cfg, cmd_id, False, error=str(e))
            time.sleep(max(1, int(cfg.get("poll_sec", 3))))
        except KeyboardInterrupt:
            print("[NEXUS Worker] stopping...")
            break
        except Exception as e:
            print(f"[NEXUS Worker] loop error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
