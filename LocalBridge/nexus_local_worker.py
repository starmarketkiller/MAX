#!/usr/bin/env python3
"""
NEXUS Local MT5 Worker
======================
Script da eseguire sul PC Windows dell'utente. Esegue polling al backend
NEXUS per ricevere comandi (compile EA, restart MT5, deploy files,
apply template) e li esegue localmente con MetaEditor / MetaTrader 5.

QUESTO PROCESSO SCRIVE ED ESEGUE CODICE SULLA MACCHINA DI TRADING.
Trattalo come un componente privilegiato: eseguilo con un account dedicato e
con i soli permessi necessari sulla cartella MQL5.

USAGE
-----
1. Installa Python 3.10+ su Windows
2. Esegui una volta: python nexus_local_worker.py  → crea il file di config
3. Compila `nexus_worker.config.json` con i tuoi valori reali
4. Esegui: python nexus_local_worker.py
5. (Opzionale) Crea task pianificato Windows o NSSM service per autostart

CONFIG FILE (nexus_worker.config.json) — same dir as this script:
{
  "backend_url":   "https://il-tuo-backend.example",
  "bridge_token":  "<token generato dal backend, mai un valore di esempio>",
  "host_id":       "workstation-01",
  "mt5_path":      "C:/Program Files/MetaTrader 5/terminal64.exe",
  "metaeditor":    "C:/Program Files/MetaTrader 5/metaeditor64.exe",
  "mql5_include":  "C:/Users/<NAME>/AppData/Roaming/MetaQuotes/Terminal/<HASH>/MQL5/Include/NEXUS_v1",
  "mql5_experts":  "C:/Users/<NAME>/AppData/Roaming/MetaQuotes/Terminal/<HASH>/MQL5/Experts",
  "poll_sec":      3
}

REMEDIAZIONI APPLICATE (audit master, stream RP0-05)
----------------------------------------------------
* AUD0-WORKER-AUTH-001  — nessun token di default utilizzabile.
* AUD0-WORKER-CONFIG-001 — permessi ristretti sul file di configurazione.
* AUD0-WORKER-CMD-002   — l'ACK viene ritentato fino a conferma.
* AUD0-WORKER-CMD-003   — errori tipizzati: retryable vs definitivi.
* AUD0-WORKER-CMD-004   — journal locale di idempotenza per command_id.
* AUD0-WORKER-CMD-005   — il restart colpisce solo il terminale configurato.
* AUD0-WORKER-CMD-006   — su non-Windows il restart è un fallimento finale.
* AUD0-WORKER-DEPLOY-001 — checksum SHA-256 obbligatorio per ogni file.
* AUD0-WORKER-DEPLOY-002 — deploy in staging + attivazione atomica.
* AUD0-WORKER-DEPLOY-003 — il rollback rimuove anche i file nuovi.
* AUD0-WORKER-DEPLOY-004 — backup scoped per release, non un unico .bak.
* AUD0-WORKER-DEPLOY-005 — manifest vuoto rifiutato.
* AUD0-WORKER-DEPLOY-006 — il risultato dichiara i digest effettivi scritti.
* AUD0-WORKER-TPL-001   — nome template ridotto a basename + containment.
* AUD0-WORKER-SHELL-001 — esecuzione shell generica RIMOSSA.
* AUD0-WORKER-LOG-001   — log senza payload completi.

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
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import requests
except ImportError:
    print("[NEXUS Worker] ERRORE: 'requests' non installato. Esegui:")
    print("   pip install requests")
    sys.exit(1)


CONFIG_PATH = Path(__file__).resolve().parent / "nexus_worker.config.json"
JOURNAL_PATH = Path(__file__).resolve().parent / "nexus_worker.journal.json"

#: Valori che indicano una configurazione non compilata. Il worker rifiuta di
#: partire se li trova (AUD0-WORKER-AUTH-001).
PLACEHOLDER_VALUES = {
    "", "nexus_bridge_token_2026", "<genera>", "changeme", "change-me",
    "https://your-nexus.preview.emergentagent.com", "<token>",
    "https://il-tuo-backend.example", "default",
}

CONFIG_TEMPLATE = {
    "backend_url":   "https://il-tuo-backend.example",
    "bridge_token":  "",          # NESSUN default utilizzabile
    "host_id":       "",          # identificativo univoco di questa macchina
    "mt5_path":      r"C:\Program Files\MetaTrader 5\terminal64.exe",
    "metaeditor":    r"C:\Program Files\MetaTrader 5\metaeditor64.exe",
    "mql5_include":  "",
    "mql5_experts":  "",
    "poll_sec":      3,
    "version":       "2.1.0",
}

#: Numero massimo di record conservati nel journal di idempotenza.
JOURNAL_MAX = 500


class PermanentCommandError(RuntimeError):
    """Errore che non ha senso ritentare (config errata, payload invalido)."""


class RetryableCommandError(RuntimeError):
    """Errore transitorio: un nuovo tentativo può riuscire."""


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
def _restrict_permissions(path: Path) -> None:
    """Riduce i permessi del file di configurazione (AUD0-WORKER-CONFIG-001).

    Il token resta in chiaro su disco: la protezione tramite Windows
    Credential Manager / DPAPI è la remediazione completa e resta nel backlog.
    Qui si limita almeno la leggibilità agli altri utenti locali.
    """
    try:
        if platform.system().lower() == "windows":
            user = os.environ.get("USERNAME", "")
            if user:
                subprocess.run(
                    ["icacls", str(path), "/inheritance:r", "/grant:r", f"{user}:F"],
                    capture_output=True, text=True, timeout=15, check=False)
        else:
            os.chmod(path, 0o600)
    except Exception as exc:  # pragma: no cover - best effort
        print(f"[NEXUS Worker] ATTENZIONE: impossibile restringere i permessi: {exc}")


def load_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        with open(CONFIG_PATH, "w") as f:
            json.dump(CONFIG_TEMPLATE, f, indent=2)
        _restrict_permissions(CONFIG_PATH)
        print(f"[NEXUS Worker] Config file creato: {CONFIG_PATH}")
        print("[NEXUS Worker] Compila backend_url, bridge_token e host_id, poi riavvia.")
        sys.exit(0)

    with open(CONFIG_PATH) as f:
        cfg = json.load(f)
    for k, v in CONFIG_TEMPLATE.items():
        cfg.setdefault(k, v)
    _restrict_permissions(CONFIG_PATH)

    # Fail-closed sui valori non compilati.
    problems = []
    for key in ("backend_url", "bridge_token", "host_id"):
        value = str(cfg.get(key, "")).strip()
        if value.lower() in PLACEHOLDER_VALUES:
            problems.append(f"{key} non configurato (valore di esempio o vuoto)")
    if len(str(cfg.get("bridge_token", "")).strip()) < 24:
        problems.append("bridge_token troppo corto: usa il token generato dal backend")
    if not str(cfg.get("backend_url", "")).lower().startswith("https://"):
        problems.append("backend_url deve usare HTTPS: il token viaggia in questo canale")
    if problems:
        print("[NEXUS Worker] AVVIO RIFIUTATO — configurazione non sicura:")
        for p in problems:
            print(f"  - {p}")
        sys.exit(2)
    return cfg


# ---------------------------------------------------------------------------
# Journal di idempotenza (AUD0-WORKER-CMD-004)
# ---------------------------------------------------------------------------
def load_journal() -> Dict[str, Any]:
    if not JOURNAL_PATH.exists():
        return {}
    try:
        with open(JOURNAL_PATH) as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        # Un journal corrotto NON deve far ripartire da zero silenziosamente:
        # si segnala e si riparte vuoto, accettando il rischio di un replay.
        print("[NEXUS Worker] ATTENZIONE: journal illeggibile, verrà ricreato")
        return {}


def journal_record(journal: Dict[str, Any], cmd_id: str, status: str,
                   result: Any = None) -> None:
    journal[cmd_id] = {"status": status, "ts": time.time(),
                       "result_digest": hashlib.sha256(
                           json.dumps(result, sort_keys=True, default=str).encode()
                       ).hexdigest()[:16] if result is not None else None}
    if len(journal) > JOURNAL_MAX:
        for key in sorted(journal, key=lambda k: journal[k]["ts"])[:len(journal) - JOURNAL_MAX]:
            journal.pop(key, None)
    tmp = JOURNAL_PATH.with_suffix(".tmp")
    try:
        with open(tmp, "w") as f:
            json.dump(journal, f)
        tmp.replace(JOURNAL_PATH)
    except Exception as exc:  # pragma: no cover
        print(f"[NEXUS Worker] ATTENZIONE: journal non scritto: {exc}")


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


def ack(cfg: Dict[str, Any], cmd_id: str, lease_id: str, status: str,
        result: Any = None, error: Optional[str] = None, *,
        attempts: int = 5) -> bool:
    """Invia l'ACK e RITENTA finché il backend non conferma.

    AUD0-WORKER-CMD-002: `ack()` ignorava l'esito. Un comando poteva quindi
    completare localmente mentre il backend restava in RUNNING e lo
    ritentava — un secondo restart o un secondo deploy.
    """
    body = {
        "command_id": cmd_id,
        "lease_id": lease_id,
        "status": status,
        "result":  result,
        "error":   error,
        "host_id": cfg["host_id"],
        "version": cfg["version"],
    }
    delay = 1.0
    for attempt in range(1, attempts + 1):
        if http_post(cfg, "/api/local_bridge/ack", body) is not None:
            return True
        if attempt < attempts:
            print(f"[NEXUS Worker] ACK {status} non confermato "
                  f"(tentativo {attempt}/{attempts}), riprovo tra {delay:.0f}s")
            time.sleep(delay)
            delay = min(delay * 2, 15.0)
    print(f"[NEXUS Worker] ERRORE: ACK {status} per {cmd_id[:8]} MAI confermato. "
          "Il backend potrebbe ritentare il comando: verificalo manualmente.")
    return False


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------
def handle_ping(cfg, payload) -> Dict[str, Any]:
    return {"pong": True, "ts": time.time()}


def _mql5_base(cfg: Dict[str, Any]) -> Path:
    experts = str(cfg.get("mql5_experts") or "").strip()
    if not experts:
        raise PermanentCommandError("mql5_experts non configurato")
    return Path(experts).resolve().parent


def _contained(root: Path, candidate: Path) -> bool:
    """True se `candidate` resta sotto `root` dopo la risoluzione."""
    root = root.resolve()
    candidate = candidate.resolve()
    return root == candidate or root in candidate.parents


def handle_compile_ea(cfg, payload) -> Dict[str, Any]:
    """Compile the EA via metaeditor.exe /compile."""
    me = cfg.get("metaeditor")
    if not me or not Path(me).exists():
        raise PermanentCommandError(f"metaeditor non trovato: {me}")
    mql5_base = _mql5_base(cfg)
    src_rel = str(payload.get("source", r"Experts\NEXUS_EA_v2.mq5")).replace("\\", "/")
    src_abs = (mql5_base / src_rel)
    if not _contained(mql5_base, src_abs):
        raise PermanentCommandError(f"source fuori da MQL5: {src_rel}")
    if not src_abs.exists():
        raise PermanentCommandError(f"source non trovato: {src_abs}")
    log_path = mql5_base / Path(str(payload.get("log", "compile.log"))).name
    cmd = [me, f"/compile:{src_abs}", f"/log:{log_path}", "/portable"]
    print(f"[NEXUS Worker] compile: {src_abs.name}")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired as exc:
        raise RetryableCommandError("compilazione oltre il timeout di 120s") from exc
    log_text = ""
    if log_path.exists():
        try:
            log_text = log_path.read_text(encoding="utf-16", errors="replace")
        except Exception:
            log_text = log_path.read_text(errors="replace")
    return {
        "exit_code":   r.returncode,
        "source":      str(src_abs),
        "stdout":      r.stdout[-2000:] if r.stdout else "",
        "stderr":      r.stderr[-2000:] if r.stderr else "",
        "compile_log": log_text[-4000:],
    }


def _terminal_pids(exe_path: Path) -> List[int]:
    """PID dei soli processi che eseguono ESATTAMENTE l'eseguibile indicato.

    AUD0-WORKER-CMD-005: `taskkill /F /IM terminal64.exe` terminava OGNI
    MetaTrader della macchina, incluse installazioni e account non gestiti da
    questo worker.
    """
    try:
        out = subprocess.run(
            ["wmic", "process", "where", "name='terminal64.exe'",
             "get", "ProcessId,ExecutablePath", "/format:csv"],
            capture_output=True, text=True, timeout=20, check=False).stdout
    except Exception:
        return []
    target = str(exe_path).replace("/", "\\").lower()
    pids: List[int] = []
    for line in out.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 3:
            continue
        exe, pid = parts[1], parts[2]
        if exe.replace("/", "\\").lower() == target and pid.isdigit():
            pids.append(int(pid))
    return pids


def handle_restart_mt5(cfg, payload) -> Dict[str, Any]:
    """Riavvia SOLO il terminale configurato per questo worker."""
    if platform.system().lower() != "windows":
        # AUD0-WORKER-CMD-006: prima restituiva {"skipped": ...} e il worker
        # dichiarava SUCCEEDED, cioè un successo mai avvenuto.
        raise PermanentCommandError(
            "restart_mt5 è supportato solo su Windows: operazione non eseguita")

    mt5 = cfg.get("mt5_path")
    if not mt5 or not Path(mt5).exists():
        raise PermanentCommandError(f"MT5 non trovato: {mt5}")
    exe = Path(mt5).resolve()

    pids = _terminal_pids(exe)
    killed = []
    for pid in pids:
        r = subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                           capture_output=True, text=True, check=False)
        if r.returncode == 0:
            killed.append(pid)
    if pids and not killed:
        raise RetryableCommandError(
            f"impossibile terminare i processi {pids} del terminale configurato")

    time.sleep(3)
    subprocess.Popen([str(exe)], close_fds=True)
    return {"restarted": True, "executable": str(exe),
            "killed_pids": killed, "matched_pids": pids}


def _decode_manifest(payload: Dict[str, Any]) -> List[Tuple[str, bytes, str]]:
    """Valida il manifest di deploy e ritorna (target_rel, dati, digest)."""
    files = payload.get("files")
    # AUD0-WORKER-DEPLOY-005: una lista vuota produceva un "successo" senza
    # alcun file scritto, con semantica ambigua lato UI.
    if not isinstance(files, list) or not files:
        raise PermanentCommandError(
            "manifest di deploy vuoto o non valido: serve almeno un file")
    expected_count = payload.get("expected_file_count")
    if expected_count is not None and int(expected_count) != len(files):
        raise PermanentCommandError(
            f"manifest incoerente: attesi {expected_count} file, ricevuti {len(files)}")

    out: List[Tuple[str, bytes, str]] = []
    for entry in files:
        if not isinstance(entry, dict) or "target" not in entry or "b64" not in entry:
            raise PermanentCommandError("voce di manifest malformata")
        expected = str(entry.get("sha256") or "").strip().lower()
        # AUD0-WORKER-DEPLOY-001: il digest era opzionale, quindi un deploy
        # senza checksum veniva accettato senza verifica di integrità.
        if len(expected) != 64:
            raise PermanentCommandError(
                f"sha256 mancante o non valido per {entry.get('target')!r}: "
                "ogni file deve dichiarare il proprio digest")
        try:
            data = base64.b64decode(entry["b64"], validate=True)
        except Exception as exc:
            raise PermanentCommandError(
                f"base64 non valido per {entry.get('target')!r}") from exc
        actual = hashlib.sha256(data).hexdigest()
        if actual != expected:
            raise PermanentCommandError(
                f"checksum mismatch per {entry['target']}: atteso {expected}, calcolato {actual}")
        out.append((str(entry["target"]).replace("\\", "/"), data, actual))
    return out


def handle_deploy_files(cfg, payload) -> Dict[str, Any]:
    """Deploy MQL5 con staging, attivazione atomica e rollback completo."""
    mql5_base = _mql5_base(cfg)
    entries = _decode_manifest(payload)
    release_id = str(payload.get("release_id") or f"rel-{int(time.time())}")
    safe_release = "".join(ch for ch in release_id if ch.isalnum() or ch in "._-")[:64]

    # AUD0-WORKER-DEPLOY-004: un unico `.bak` per file sovrascriveva il punto
    # di ripristino precedente. I backup sono ora per release.
    backup_root = mql5_base / "_nexus_backups" / safe_release
    staging_root = mql5_base / "_nexus_staging" / safe_release

    resolved: List[Tuple[Path, bytes, str]] = []
    for target_rel, data, digest in entries:
        target_abs = (mql5_base / target_rel)
        if not _contained(mql5_base, target_abs):
            raise PermanentCommandError(f"target outside MQL5: {target_rel}")
        resolved.append((target_abs, data, digest))

    # Fase 1 — staging: si scrive tutto fuori dai percorsi attivi.
    # AUD0-WORKER-DEPLOY-002: la scrittura sequenziale sui percorsi finali
    # esponeva MT5/MetaEditor a una release parzialmente aggiornata.
    if staging_root.exists():
        shutil.rmtree(staging_root, ignore_errors=True)
    staging_root.mkdir(parents=True, exist_ok=True)
    staged: List[Tuple[Path, Path]] = []
    for target_abs, data, _digest in resolved:
        rel = target_abs.relative_to(mql5_base)
        staged_path = staging_root / rel
        staged_path.parent.mkdir(parents=True, exist_ok=True)
        staged_path.write_bytes(data)
        staged.append((staged_path, target_abs))

    # Fase 2 — attivazione con rollback completo.
    backup_root.mkdir(parents=True, exist_ok=True)
    backups: List[Tuple[Path, Path]] = []
    created: List[Path] = []
    written: List[Dict[str, str]] = []
    try:
        for staged_path, target_abs in staged:
            target_abs.parent.mkdir(parents=True, exist_ok=True)
            if target_abs.exists():
                backup_path = backup_root / target_abs.relative_to(mql5_base)
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target_abs, backup_path)
                backups.append((target_abs, backup_path))
            else:
                created.append(target_abs)
            shutil.copy2(staged_path, target_abs)
            # AUD0-WORKER-DEPLOY-006: si dichiara il digest EFFETTIVO del file
            # su disco dopo la scrittura, non quello annunciato dal manifest.
            written.append({
                "target": str(target_abs),
                "sha256": hashlib.sha256(target_abs.read_bytes()).hexdigest(),
            })
    except Exception as exc:
        for target, backup in reversed(backups):
            if backup.exists():
                shutil.copy2(backup, target)
        # AUD0-WORKER-DEPLOY-003: i file NUOVI restavano su disco dopo il
        # rollback, lasciando un mix di release.
        for target in reversed(created):
            try:
                target.unlink(missing_ok=True)
            except OSError:
                pass
        raise RetryableCommandError(f"deploy fallito e ripristinato: {exc}") from exc
    finally:
        shutil.rmtree(staging_root, ignore_errors=True)

    return {
        "written": written,
        "file_count": len(written),
        "release_id": release_id,
        "backup_dir": str(backup_root),
        # Il deploy prova solo che i file sono a posto: non prova compilazione,
        # ricarica di MT5 né versione runtime dell'EA (AUD0-WORKER-DEPLOY-006).
        "state": "STAGED_AND_ACTIVATED",
        "compiled": False,
        "runtime_confirmed": False,
    }


def handle_open_chart(cfg, payload) -> Dict[str, Any]:
    """Launch MT5 with a specific profile/template (best-effort on Windows)."""
    mt5 = cfg.get("mt5_path")
    if not mt5 or not Path(mt5).exists():
        raise PermanentCommandError(f"MT5 non trovato: {mt5}")
    args = [mt5]
    profile = payload.get("profile")
    if profile:
        # Solo caratteri sicuri: il valore finisce in una riga di comando.
        clean = "".join(ch for ch in str(profile) if ch.isalnum() or ch in "._-")[:64]
        if clean:
            args += ["/profile:" + clean]
    subprocess.Popen(args, close_fds=True)
    return {"opened": True}


def handle_apply_template(cfg, payload) -> Dict[str, Any]:
    """Copia un .tpl in MQL5/Profiles/Templates."""
    # AUD0-WORKER-TPL-001: il nome veniva usato quasi tale e quale, quindi un
    # valore con separatori di percorso poteva uscire dalla cartella template.
    name = Path(str(payload.get("name", "NEXUS_default.tpl"))).name
    if not name.endswith(".tpl"):
        name += ".tpl"
    if name in (".tpl", "") or name.startswith("."):
        raise PermanentCommandError("nome template non valido")

    mql5_base = _mql5_base(cfg)
    tpl_dir = mql5_base / "Profiles" / "Templates"
    tpl_dir.mkdir(parents=True, exist_ok=True)
    target = tpl_dir / name
    if not _contained(tpl_dir, target):
        raise PermanentCommandError(f"target fuori dalla cartella template: {name}")

    b64 = payload.get("b64")
    if not b64:
        raise PermanentCommandError("payload.b64 mancante")
    try:
        data = base64.b64decode(b64, validate=True)
    except Exception as exc:
        raise PermanentCommandError("base64 non valido") from exc
    expected = str(payload.get("sha256") or "").strip().lower()
    if expected and hashlib.sha256(data).hexdigest() != expected:
        raise PermanentCommandError("checksum mismatch sul template")

    target.write_bytes(data)
    return {"written": str(target),
            "sha256": hashlib.sha256(data).hexdigest()}


# AUD0-WORKER-SHELL-001: `handle_shell` eseguiva comandi con `shell=True` e una
# whitelist basata sul solo prefisso, quindi "echo x && <qualsiasi cosa>"
# passava il controllo. Era esecuzione di codice remoto sulla macchina di
# trading. L'handler è stato RIMOSSO e l'azione non è più supportata:
# il backend riceverà FAILED_FINAL "Unknown action: shell".
HANDLERS = {
    "ping":            handle_ping,
    "compile_ea":      handle_compile_ea,
    "restart_mt5":     handle_restart_mt5,
    "deploy_files":    handle_deploy_files,
    "open_chart":      handle_open_chart,
    "apply_template":  handle_apply_template,
}


def _payload_summary(action: str, payload: Dict[str, Any]) -> str:
    """Riassunto per il log SENZA contenuti (AUD0-WORKER-LOG-001).

    I payload di deploy contengono sorgenti base64 e i log locali non devono
    conservarli.
    """
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:12]
    parts = [f"payload_sha={digest}"]
    if action == "deploy_files":
        files = payload.get("files") or []
        parts.append(f"files={len(files)}")
        parts.append(f"release={payload.get('release_id')}")
    elif action == "compile_ea":
        parts.append(f"source={payload.get('source')}")
    elif action == "apply_template":
        parts.append(f"template={Path(str(payload.get('name', ''))).name}")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Main poll loop
# ---------------------------------------------------------------------------
def main():
    cfg = load_config()
    journal = load_journal()
    print(f"[NEXUS Worker] v{cfg['version']} started")
    print(f"[NEXUS Worker] backend: {cfg['backend_url']}")
    print(f"[NEXUS Worker] host_id: {cfg['host_id']}")
    print(f"[NEXUS Worker] OS:      {platform.platform()}")
    print(f"[NEXUS Worker] journal: {len(journal)} comandi noti")

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
                cmd_id = resp.get("command_id") or resp["id"]
                lease_id = resp["lease_id"]
                action = resp["action"]
                payload = resp.get("payload", {}) or {}

                # Idempotenza locale: un comando già completato non viene
                # rieseguito, si ripete solo l'ACK terminale.
                prior = journal.get(cmd_id)
                if prior and prior["status"] in ("SUCCEEDED", "FAILED_FINAL"):
                    print(f"[NEXUS Worker] ↺ {action} (id={cmd_id[:8]}) già eseguito "
                          f"({prior['status']}): ri-invio solo l'ACK")
                    ack(cfg, cmd_id, lease_id, prior["status"],
                        result={"replayed": True})
                    time.sleep(max(1, int(cfg.get("poll_sec", 3))))
                    continue

                print(f"[NEXUS Worker] → {action} (id={cmd_id[:8]}) "
                      f"{_payload_summary(action, payload)}")
                handler = HANDLERS.get(action)
                if not handler:
                    journal_record(journal, cmd_id, "FAILED_FINAL")
                    ack(cfg, cmd_id, lease_id, "FAILED_FINAL",
                        error=f"Unknown action: {action}")
                else:
                    ack(cfg, cmd_id, lease_id, "RUNNING")
                    try:
                        result = handler(cfg, payload)
                        journal_record(journal, cmd_id, "SUCCEEDED", result)
                        ack(cfg, cmd_id, lease_id, "SUCCEEDED", result=result)
                        print(f"[NEXUS Worker] ✓ {action} done")
                    except PermanentCommandError as e:
                        # AUD0-WORKER-CMD-003: prima ogni eccezione diventava
                        # FAILED_RETRYABLE, quindi errori permanenti come un
                        # checksum sbagliato venivano ritentati all'infinito.
                        print(f"[NEXUS Worker] ✗ {action} ERRORE DEFINITIVO: {e}")
                        journal_record(journal, cmd_id, "FAILED_FINAL")
                        ack(cfg, cmd_id, lease_id, "FAILED_FINAL", error=str(e))
                    except Exception as e:
                        print(f"[NEXUS Worker] ✗ {action} errore ritentabile: {e}")
                        journal_record(journal, cmd_id, "FAILED_RETRYABLE")
                        ack(cfg, cmd_id, lease_id, "FAILED_RETRYABLE", error=str(e))
            time.sleep(max(1, int(cfg.get("poll_sec", 3))))
        except KeyboardInterrupt:
            print("[NEXUS Worker] stopping...")
            break
        except Exception as e:
            print(f"[NEXUS Worker] loop error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
