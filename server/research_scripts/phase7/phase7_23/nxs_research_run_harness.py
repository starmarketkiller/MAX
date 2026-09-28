#!/usr/bin/env python3
"""Phase 7.23 Fase A - Research Run Isolation harness.

Problema risolto: NEXUS_trades.csv e i certificati di validita' sono
scritti in directory CONDIVISE (Common/Files) che persistono fra
sessioni - scoperto in Phase 7.22 che questo puo' portare a confondere
dati di run precedenti con quelli di un nuovo run.

Soluzione: SOLO orchestrazione Python, ZERO modifiche a MQL5. L'EA
espone gia' due meccanismi non distruttivi per questo esatto scopo
(mai usati insieme finora in questo progetto):
  - InpResetTradesLogOnInit=true: archivia (rinomina con timestamp,
    MAI cancella) NEXUS_trades.csv esistente all'avvio, poi riparte
    vuoto - garantisce che il file post-run contenga SOLO i trade di
    QUESTO run.
  - InpBuildGitCommit=<sha>: inietta lo SHA git corrente nel
    certificato di validita' (default "UNKNOWN" se non impostato).

Il certificato non ha un meccanismo di reset equivalente (accumula con
suffissi _rNNN auto-incrementati) - la harness lo identifica per DELTA
(confronto pre/post-run della directory certificati), non per nome
fisso.

Nessuna logica di strategia toccata. Nessun artifact storico
cancellato - tutto cio' che viene "isolato" e' ARCHIVIATO (spostato in
una directory dedicata al run), mai eliminato.
"""
import hashlib
import json
import os
import shutil
import subprocess
import time
import uuid
from datetime import datetime, timezone

TERMINAL_DIR = r"C:\Users\User\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075"
COMMON_FILES_DIR = r"C:\Users\User\AppData\Roaming\MetaQuotes\Terminal\Common\Files"
CERT_DIR = os.path.join(COMMON_FILES_DIR, "NEXUS", "certificates")
TRADES_CSV_NAME = "NEXUS_trades.csv"
TERMINAL_EXE = r"C:\Program Files\MetaTrader 5\terminal64.exe"
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))


def current_git_sha(short=False):
    fmt = "%h" if short else "%H"
    out = subprocess.run(["git", "log", "-1", f"--format={fmt}"], cwd=REPO_ROOT,
                         capture_output=True, text=True)
    return out.stdout.strip() or "UNKNOWN"


def config_hash(ini_dict):
    """Hash deterministico della configurazione (non del run_id, che e'
    univoco per esecuzione - stesso principio di config_fingerprint nel
    certificato MQL5, calcolato pero' qui in modo indipendente per
    poterlo confrontare a posteriori)."""
    canonical = json.dumps(ini_dict, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def make_run_id(strategy_identity, period_start, period_end, cfg_hash):
    # timestamp a grana di secondo NON basta a garantire unicita' (due
    # chiamate nello stesso secondo, stessa config, produrrebbero lo
    # stesso run_id - trovato dal test di isolamento di questa stessa
    # fase) - aggiunto un suffisso random breve, sempre presente.
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    nonce = uuid.uuid4().hex[:8]
    return f"{strategy_identity}_{period_start}_{period_end}_{cfg_hash}_{ts}_{nonce}"


class RunIsolationError(Exception):
    pass


def snapshot_shared_state():
    """Inventario di NEXUS_trades.csv e dei certificati esistenti PRIMA
    del lancio - permette di sapere esplicitamente cosa gia' esiste."""
    trades_path = os.path.join(COMMON_FILES_DIR, TRADES_CSV_NAME)
    snap = {
        "trades_csv_exists": os.path.exists(trades_path),
        "trades_csv_size": os.path.getsize(trades_path) if os.path.exists(trades_path) else 0,
        "trades_csv_mtime": os.path.getmtime(trades_path) if os.path.exists(trades_path) else None,
        "existing_certificates": [],
    }
    if os.path.isdir(CERT_DIR):
        snap["existing_certificates"] = sorted(
            f for f in os.listdir(CERT_DIR) if f.endswith(".txt"))
    return snap


def build_ini(*, run_dir, strategy_identity, selector, symbol, period, chart_period,
             fixed_lot=0.01, leverage=None, extra_inputs=None):
    """Costruisce l'ini del Tester con InpResetTradesLogOnInit=true e
    InpBuildGitCommit=<sha corrente> - isolamento SENZA modificare MQL5.
    period = (from_date, to_date) come stringhe 'YYYY.MM.DD'."""
    from_date, to_date = period
    report_name = f"nxs_{strategy_identity.lower()}_{from_date.replace('.', '')}_{to_date.replace('.', '')}"

    tester_lines = [
        "[Tester]", "Expert=NEXUS_EA_v2", f"Symbol={symbol}", f"Period={chart_period}",
        "Optimization=0", "Model=4", f"FromDate={from_date}", f"ToDate={to_date}",
        "ForwardMode=0", "Deposit=10000", "Currency=USD",
    ]
    if leverage:
        tester_lines.append(f"Leverage={leverage}")
    tester_lines += ["ExecutionMode=0", "OptimizationCriterion=0", "Visual=0",
                     "ShutdownTerminal=1", "ReplaceReport=1", f"Report={report_name}"]

    inputs = {
        "InpStrategySelector": selector, "InpUseStrategyProfiles": "true",
        "InpResearchMode": "true", "InpResearchExitMode": 0,
        "InpResearchFixedLot": fixed_lot, "InpProfileMultiTF": "true",
        "InpResearchUseDPT": "false", "InpResearchUseRuin": "false",
        "InpResearchUseESL": "false", "InpResearchUseDailyDD": "false",
        "InpResearchUseTotalDD": "false",
        "InpResetTradesLogOnInit": "true",  # <-- isolamento: archivia il log esistente, riparte vuoto
        "InpBuildGitCommit": current_git_sha(),  # <-- provenance: SHA reale nel certificato
    }
    if extra_inputs:
        inputs.update(extra_inputs)

    cfg_for_hash = {"tester": tester_lines, "inputs": inputs}
    cfg_hash = config_hash(cfg_for_hash)
    run_id = make_run_id(strategy_identity, from_date, to_date, cfg_hash)

    lines = list(tester_lines) + ["[TesterInputs]"]
    for k, v in inputs.items():
        lines.append(f"{k}={v}")

    os.makedirs(run_dir, exist_ok=True)
    ini_path = os.path.join(run_dir, f"{run_id}.ini")
    with open(ini_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    manifest = {
        "run_id": run_id, "run_dir": run_dir, "ini_path": ini_path,
        "strategy_identity": strategy_identity, "selector": selector, "symbol": symbol,
        "period_from": from_date, "period_to": to_date, "chart_period": chart_period,
        "code_git_sha": inputs["InpBuildGitCommit"], "config_hash": cfg_hash,
        "config_fingerprint_inputs": inputs,
        "report_name": report_name,
        "start_time_utc": None, "end_time_utc": None, "status": "PREPARED",
        "pre_run_snapshot": snapshot_shared_state(),
        "trades_csv_dest": None, "certificate_dest": None,
        "reconciliation": None,
    }
    manifest_path = os.path.join(run_dir, f"{run_id}.manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=True)

    return manifest, manifest_path, ini_path


def launch(manifest, manifest_path):
    """Lancia il Tester. NON blocca - il chiamante e' responsabile del
    polling (stesso schema gia' usato nelle fasi precedenti, qui non
    reimplementato per non duplicare logica di attesa gia' matura)."""
    dest_ini = os.path.join(TERMINAL_DIR, os.path.basename(manifest["ini_path"]))
    shutil.copy(manifest["ini_path"], dest_ini)
    manifest["start_time_utc"] = datetime.now(timezone.utc).isoformat()
    manifest["status"] = "LAUNCHED"
    manifest["dest_ini"] = dest_ini
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=True)
    subprocess.Popen([TERMINAL_EXE, f"/config:{dest_ini}"])
    return manifest


def collect_after_run(manifest, manifest_path):
    """Da chiamare DOPO che il Tester ha terminato (verificato esternamente
    dal chiamante, es. via log 'successfully finished'). Copia (non
    sposta) NEXUS_trades.csv - post InpResetTradesLogOnInit contiene
    SOLO i trade di QUESTO run - e identifica il certificato per DELTA
    rispetto allo snapshot pre-run."""
    run_dir = manifest["run_dir"]
    trades_src = os.path.join(COMMON_FILES_DIR, TRADES_CSV_NAME)
    trades_dest = os.path.join(run_dir, f"{manifest['run_id']}.trades.csv")
    if os.path.exists(trades_src):
        shutil.copy(trades_src, trades_dest)
        manifest["trades_csv_dest"] = trades_dest
    else:
        manifest["trades_csv_dest"] = None

    pre_certs = set(manifest["pre_run_snapshot"]["existing_certificates"])
    post_certs = set(f for f in os.listdir(CERT_DIR) if f.endswith(".txt")) if os.path.isdir(CERT_DIR) else set()
    new_certs = sorted(post_certs - pre_certs)
    manifest["new_certificates_detected"] = new_certs
    if len(new_certs) == 1:
        cert_src = os.path.join(CERT_DIR, new_certs[0])
        cert_dest = os.path.join(run_dir, f"{manifest['run_id']}.certificate.txt")
        shutil.copy(cert_src, cert_dest)
        manifest["certificate_dest"] = cert_dest
    elif len(new_certs) == 0:
        manifest["certificate_dest"] = None
        manifest.setdefault("warnings", []).append(
            "nessun nuovo certificato rilevato per delta - il run potrebbe essere stato "
            "interrotto prima di OnDeinit, o il certificato non e' stato generato")
    else:
        manifest["certificate_dest"] = None
        manifest.setdefault("warnings", []).append(
            f"{len(new_certs)} nuovi certificati rilevati per delta (atteso 1) - "
            "ambiguita' non risolta automaticamente, riportata per revisione manuale")

    manifest["end_time_utc"] = datetime.now(timezone.utc).isoformat()
    manifest["status"] = "COLLECTED"
    manifest["reconciliation"] = reconcile(manifest)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=True)
    return manifest


def _detect_text_encoding(path):
    """NXS_LogTradeCSV apre il file con FILE_CSV (senza FILE_ANSI) -> MQL5
    scrive UTF-16LE con BOM per default. Rilevato per BOM, non assunto -
    trovato un bug reale in questa fase (la prima versione di questa
    funzione assumeva utf-8-sig ed è silenziosamente fallita, riportando
    n_trade_closes_in_csv=0 invece di 43 reali - corretto, verificato dal
    verificatore indipendente)."""
    with open(path, "rb") as f:
        head = f.read(4)
    if head[:2] == b"\xff\xfe":
        return "utf-16-le"
    if head[:2] == b"\xfe\xff":
        return "utf-16-be"
    if head[:3] == b"\xef\xbb\xbf":
        return "utf-8-sig"
    return "utf-8"


def _count_trade_closes(trades_csv_path, strategy_name):
    if not trades_csv_path or not os.path.exists(trades_csv_path):
        return None
    import csv
    cols = ["time", "action", "ticket", "strategy", "price", "lots", "sl", "tp",
           "score_or_pnl", "reason", "hold_sec", "r_multiple", "resolved_tf"]
    encoding = _detect_text_encoding(trades_csv_path)
    with open(trades_csv_path, encoding=encoding, errors="replace") as f:
        try:
            reader = csv.reader(f)
            rows = [dict(zip(cols, row)) for row in reader if row]
        except UnicodeDecodeError:
            return None
    return sum(1 for r in rows if r.get("strategy") == strategy_name and r.get("action") == "CLOSE")


def _parse_certificate_opened(cert_path):
    if not cert_path or not os.path.exists(cert_path):
        return None
    import re
    with open(cert_path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    m = re.search(r"OPENED=(\d+)", text)
    return int(m.group(1)) if m else None


def reconcile(manifest):
    """Riconcilia trade CSV e certificato usando lo STESSO run_id -
    nessun artifact di sessioni precedenti deve poter essere interpretato
    come parte di questo run (garantito dal reset + dalla identificazione
    per delta, non per nome fisso)."""
    n_closes = _count_trade_closes(manifest.get("trades_csv_dest"), manifest["strategy_identity"])
    n_opened_cert = _parse_certificate_opened(manifest.get("certificate_dest"))
    match = None
    if n_closes is not None and n_opened_cert is not None:
        match = (n_closes == n_opened_cert)
    return {
        "n_trade_closes_in_csv": n_closes,
        "n_opened_per_certificate": n_opened_cert,
        "match": match,
        "note": "None per un campo significa che il dato non era disponibile (run interrotto, "
               "certificato mancante/ambiguo, o CSV assente) - MAI trattato come 0 implicito.",
    }
