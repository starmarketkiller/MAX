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


def preflight_archive_trades_csv(run_dir):
    """Phase 7.35 — archive+remove Common/Files/NEXUS_trades.csv BEFORE Tester
    launch. Defense in depth when MQL5 FileMove fails (err=5020 observed on
    research PC): Python clears the shared log so the run cannot append onto
    a prior diagnostic. Never deletes without copying into run_dir first.
    Returns a small report dict (always JSON-serializable)."""
    os.makedirs(run_dir, exist_ok=True)
    src = os.path.join(COMMON_FILES_DIR, TRADES_CSV_NAME)
    report = {
        "preflight": "trades_csv_archive",
        "src_existed": os.path.exists(src),
        "archived_to": None,
        "cleared": False,
        "error": None,
    }
    if not os.path.exists(src):
        return report
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = os.path.join(run_dir, f"preflight_archive_{ts}_{TRADES_CSV_NAME}")
    try:
        shutil.copy2(src, dest)
        report["archived_to"] = dest
        os.remove(src)
        report["cleared"] = not os.path.exists(src)
        if not report["cleared"]:
            report["error"] = "copy_ok_but_source_still_exists"
    except OSError as e:
        report["error"] = str(e)
    return report


def launch(manifest, manifest_path):
    """Lancia il Tester. NON blocca - il chiamante e' responsabile del
    polling (stesso schema gia' usato nelle fasi precedenti, qui non
    reimplementato per non duplicare logica di attesa gia' matura)."""
    # Refresh snapshot + clear shared trades log before start (Phase 7.35).
    manifest["pre_run_snapshot"] = snapshot_shared_state()
    manifest["preflight_trades_archive"] = preflight_archive_trades_csv(manifest["run_dir"])
    if manifest["preflight_trades_archive"].get("error"):
        manifest.setdefault("warnings", []).append(
            "preflight_archive_incomplete: " + manifest["preflight_trades_archive"]["error"]
        )
    dest_ini = os.path.join(TERMINAL_DIR, os.path.basename(manifest["ini_path"]))
    shutil.copy(manifest["ini_path"], dest_ini)
    manifest["start_time_utc"] = datetime.now(timezone.utc).isoformat()
    manifest["status"] = "LAUNCHED"
    manifest["dest_ini"] = dest_ini
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=True)
    subprocess.Popen([TERMINAL_EXE, f"/config:{dest_ini}"])
    return manifest


def collect_after_run(manifest, manifest_path, *, strict_isolation=True):
    """Da chiamare DOPO che il Tester ha terminato (verificato esternamente
    dal chiamante, es. via log 'successfully finished'). Copia (non
    sposta) NEXUS_trades.csv - post InpResetTradesLogOnInit / preflight
    dovrebbe contenere SOLO i trade di QUESTO run - e identifica il
    certificato per DELTA rispetto allo snapshot pre-run.

    Phase 7.35: if certificate OPENED and CSV closes disagree, status becomes
    COLLECTED_ISOLATION_FAILED when strict_isolation=True (default)."""
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
    manifest["reconciliation"] = reconcile(manifest)
    isol_ok = manifest["reconciliation"].get("isolation_ok")
    if strict_isolation and isol_ok is False:
        manifest["status"] = "COLLECTED_ISOLATION_FAILED"
        manifest.setdefault("warnings", []).append(
            "isolation_failed: CSV close count != certificate OPENED "
            "(shared trades log likely contaminated; refuse promotion/analysis as clean)"
        )
    else:
        manifest["status"] = "COLLECTED"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=True)
    return manifest


def _detect_text_encoding(path):
    """NXS_LogTradeCSV apre il file con FILE_CSV (senza FILE_ANSI) -> MQL5
    scrive UTF-16LE con BOM per default. Rilevato per BOM, non assunto -
    trovato un bug reale in Phase 7.23 (la prima versione di questa
    funzione assumeva utf-8-sig ed è fallita silenziosamente, riportando
    n_trade_closes_in_csv=0 invece di 43 reali - corretto).

    Un SECONDO bug, piu' sottile, e' stato trovato in Phase 7.24: questa
    funzione restituiva 'utf-16-le'/'utf-16-be' invece del codec generico
    'utf-16' - il codec esplicito -le/-be NON rimuove il BOM dal testo
    decodificato (lo fa solo 'utf-16', che lo usa per determinare
    l'endianness e poi lo scarta), lasciando un carattere U+FEFF invisibile
    incollato al primo campo della prima riga del file. Quando quel campo
    era un timestamp usato per un confronto/ordinamento su stringhe (come
    in build_liq_sweep_diagnostic_run.py), U+FEFF (65279) ordina DOPO
    qualunque cifra ASCII, quindi il primo OPEN cronologico finiva in
    fondo alla lista ordinata invece che in testa - causa esatta del
    residuo 42 vs 41 eventi appaiati scoperto in Phase 7.24 (43 open/42
    close reali, ma un solo appaiamento perso per corruzione dell'ordine)."""
    with open(path, "rb") as f:
        head = f.read(4)
    if head[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return "utf-16"
    if head[:3] == b"\xef\xbb\xbf":
        return "utf-8-sig"
    return "utf-8"


def _iter_trade_rows(trades_csv_path):
    if not trades_csv_path or not os.path.exists(trades_csv_path):
        return None
    import csv
    cols = ["time", "action", "ticket", "strategy", "price", "lots", "sl", "tp",
           "score_or_pnl", "reason", "hold_sec", "r_multiple", "resolved_tf"]
    encoding = _detect_text_encoding(trades_csv_path)
    with open(trades_csv_path, encoding=encoding, errors="replace") as f:
        try:
            reader = csv.reader(f)
            return [dict(zip(cols, row)) for row in reader if row]
        except UnicodeDecodeError:
            return None


def _count_trade_closes(trades_csv_path, strategy_name, *, period_from=None, period_to=None):
    """Count CLOSE rows for strategy. Optional period_from/to (YYYY.MM.DD)
    filters by OPEN time of the paired episode when both OPEN+CLOSE present
    in order; if only CLOSE rows, filters by CLOSE time. Phase 7.35."""
    rows = _iter_trade_rows(trades_csv_path)
    if rows is None:
        return None
    if period_from is None and period_to is None:
        return sum(1 for r in rows if r.get("strategy") == strategy_name and r.get("action") == "CLOSE")

    # Pair OPEN→CLOSE FIFO for strategy; count closes whose OPEN is in window.
    from datetime import datetime as _dt
    start = _dt.strptime(period_from, "%Y.%m.%d") if period_from else None
    end = _dt.strptime(period_to, "%Y.%m.%d") if period_to else None
    # inclusive end-of-day
    if end is not None:
        end = end.replace(hour=23, minute=59, second=59)

    opens = []
    n = 0
    for r in rows:
        if r.get("strategy") != strategy_name:
            continue
        t_raw = (r.get("time") or "").lstrip("\ufeff")
        try:
            t = _dt.strptime(t_raw, "%Y.%m.%d %H:%M:%S")
        except ValueError:
            continue
        if r.get("action") == "OPEN":
            opens.append(t)
        elif r.get("action") == "CLOSE":
            ot = opens.pop(0) if opens else t
            if start is not None and ot < start:
                continue
            if end is not None and ot > end:
                continue
            n += 1
    return n


def _parse_certificate_opened(cert_path):
    if not cert_path or not os.path.exists(cert_path):
        return None
    import re
    with open(cert_path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    m = re.search(r"OPENED=(\d+)", text)
    return int(m.group(1)) if m else None


def reconcile(manifest):
    """Riconcilia trade CSV e certificato. Phase 7.35 also reports
    window-filtered CSV closes (period_from/to) and isolation_ok.

    isolation_ok is True only when raw CSV closes == certificate OPENED.
    Window-filtered equality alone is NOT enough for isolation_ok (that
    pattern is what hid FileMove-5020 contamination in Phase 7.34)."""
    n_closes = _count_trade_closes(
        manifest.get("trades_csv_dest"), manifest["strategy_identity"]
    )
    n_closes_window = _count_trade_closes(
        manifest.get("trades_csv_dest"),
        manifest["strategy_identity"],
        period_from=manifest.get("period_from"),
        period_to=manifest.get("period_to"),
    )
    n_opened_cert = _parse_certificate_opened(manifest.get("certificate_dest"))
    match = None
    if n_closes is not None and n_opened_cert is not None:
        match = (n_closes == n_opened_cert)
    window_match = None
    if n_closes_window is not None and n_opened_cert is not None:
        window_match = (n_closes_window == n_opened_cert)
    isolation_ok = match  # strict: raw CSV must equal certificate
    return {
        "n_trade_closes_in_csv": n_closes,
        "n_trade_closes_in_csv_in_window": n_closes_window,
        "n_opened_per_certificate": n_opened_cert,
        "match": match,
        "window_match": window_match,
        "isolation_ok": isolation_ok,
        "note": (
            "isolation_ok requires raw CSV closes == certificate OPENED. "
            "window_match alone is insufficient (Phase 7.34 contamination lesson). "
            "None means data unavailable — never treated as implicit 0."
        ),
    }
