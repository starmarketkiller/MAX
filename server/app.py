#!/usr/bin/env python3
"""
NEXUS self-hosted backend
=========================
Sostituisce completamente il backend cloud che prima girava su Emergent.
Espone tutti gli endpoint che l'Expert Advisor MQL5 e il LocalBridge worker
si aspettano, piu' gli endpoint della dashboard web (protetti da login JWT).

Avvio (sviluppo):
    pip install -r requirements.txt
    uvicorn app:app --host 0.0.0.0 --port 8001 --reload

Avvio (Docker): vedi docker-compose.yml nella root del progetto.

Autenticazione:
  - EA / worker  -> header  X-Nexus-Token: <NEXUS_BRIDGE_TOKEN>
  - Dashboard    -> header  Authorization: Bearer <jwt>  (ottenuto da /api/auth/login)
"""
from __future__ import annotations

import os
import json
import time
import sqlite3
import hashlib
import secrets
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

import jwt
from fastapi import FastAPI, Request, Header, HTTPException, Depends
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
BRIDGE_TOKEN   = os.environ.get("NEXUS_BRIDGE_TOKEN", "NEXUS_BRIDGE_TOKEN_2026")
ADMIN_USER     = os.environ.get("NEXUS_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("NEXUS_ADMIN_PASSWORD", "admin")
JWT_SECRET     = os.environ.get("NEXUS_JWT_SECRET", "change-me-" + secrets.token_hex(8))
JWT_HOURS      = int(os.environ.get("NEXUS_JWT_HOURS", "720"))
DB_PATH        = os.environ.get("NEXUS_DB_PATH", str(Path(__file__).resolve().parent / "nexus.db"))
TG_BOT_TOKEN   = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TG_CHAT_ID     = os.environ.get("TELEGRAM_CHAT_ID", "")
LICENSE_MODE   = os.environ.get("NEXUS_LICENSE_MODE", "open")  # open | strict

# AI Coach (API Claude). La chiave va impostata su Render come ANTHROPIC_API_KEY.
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
COACH_MODEL       = os.environ.get("NEXUS_COACH_MODEL", "claude-opus-4-8")

STATIC_DIR = Path(__file__).resolve().parent / "static"
WORKER_FILE = Path(__file__).resolve().parent / "nexus_local_worker.py"

# Elenco strategie note (dal contratto EA). Usato da backtest/strategies.
STRAT_LIST = [
    "ADX_RSI", "BOLLINGER", "MACD", "SAR", "TSI", "BJORGUM", "LIQ_SWEEP",
    "FVG_CONT", "BREAKOUT_ACC", "LONDON_BO", "EMA_PULLBACK", "BB_SQUEEZE",
    "ICHIMOKU", "RSI_DIV", "ORDER_BLOCK", "STRUCT_REACT", "MALAYSIAN_SNR",
    "CISD", "SMC_OB", "SMC_FVG", "SMC_BOS", "SMC_CHOCH",
]

# Strategy chain default config (replica del CHANGELOG v2.0.13)
DEFAULT_CHAIN_CONFIG = {
    "enable_continuation": True,
    "enable_smart_reverse": True,
    "continuation_window_sec": 1800,
    "continuation_lot_mult": 0.6,
    "max_continuations": 3,
    "reverse_min_reaction": 75,
    "reverse_close_threshold_strong": 55,
    "bridges": {
        "ADX_RSI": ["EMA_PULLBACK", "BREAKOUT_ACC"],
        "BREAKOUT_ACC": ["EMA_PULLBACK"],
        "EMA_PULLBACK": ["ADX_RSI"],
    },
}

# Runtime settings default (chiavi lette da NXS_RuntimeSettings.mqh)
DEFAULT_SETTINGS = {
    "RiskPercent": 1.0,
    "MaxLot": 5.0,
    "MaxTradesPerDay": 30,
    "MaxConcurrent": 3,
    "MaxDailyDDPct": 5.0,
    "MinEntryScore": 70,
    "AsianScoreMin": 72.0,
    "LondonScoreMin": 68.0,
    "OverlapScoreMin": 66.0,
    "NYScoreMin": 68.0,
    "AfterNYScoreMin": 74.0,
    "UseNewsFilter": True,
    "UseHTFBias": True,
    "UseVelocityGate": True,
}

# --------------------------------------------------------------------------- #
# Database
# --------------------------------------------------------------------------- #
def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    return c


def init_db() -> None:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS ea_status (
                key        TEXT PRIMARY KEY,          -- "<magic>:<symbol>"
                magic      INTEGER,
                symbol     TEXT,
                payload    TEXT,
                updated_at REAL
            );
            CREATE TABLE IF NOT EXISTS ea_commands (
                id         TEXT PRIMARY KEY,
                action     TEXT,
                payload    TEXT,
                created_at REAL,
                consumed   INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS trades (
                ticket     INTEGER PRIMARY KEY,
                symbol     TEXT,
                strategy   TEXT,
                side       TEXT,
                lots       REAL,
                open_price REAL,
                close_price REAL,
                pnl        REAL,
                open_time  TEXT,
                close_time TEXT,
                reason     TEXT,
                raw        TEXT,
                synced_at  REAL
            );
            CREATE TABLE IF NOT EXISTS strategy_stats (
                symbol     TEXT PRIMARY KEY,
                payload    TEXT,
                updated_at REAL
            );
            CREATE TABLE IF NOT EXISTS shadow_trades (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                payload    TEXT,
                created_at REAL
            );
            CREATE TABLE IF NOT EXISTS trade_reasons (
                symbol     TEXT PRIMARY KEY,
                payload    TEXT,
                updated_at REAL
            );
            CREATE TABLE IF NOT EXISTS visual_objects (
                symbol     TEXT PRIMARY KEY,
                payload    TEXT,
                updated_at REAL
            );
            CREATE TABLE IF NOT EXISTS kv (
                key        TEXT PRIMARY KEY,
                value      TEXT
            );
            CREATE TABLE IF NOT EXISTS licenses (
                key        TEXT PRIMARY KEY,
                account    INTEGER,
                trial      INTEGER DEFAULT 0,
                expires_at INTEGER DEFAULT 0,
                note       TEXT
            );
            CREATE TABLE IF NOT EXISTS bridge_hosts (
                host_id    TEXT PRIMARY KEY,
                version    TEXT,
                os         TEXT,
                meta       TEXT,
                last_seen  REAL
            );
            CREATE TABLE IF NOT EXISTS bridge_commands (
                id         TEXT PRIMARY KEY,
                host_id    TEXT,
                action     TEXT,
                payload    TEXT,
                status     TEXT DEFAULT 'pending',   -- pending|done|error
                result     TEXT,
                error      TEXT,
                created_at REAL,
                done_at    REAL
            );
            CREATE TABLE IF NOT EXISTS notifications (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                text       TEXT,
                delivered  INTEGER DEFAULT 0,
                created_at REAL
            );
            CREATE TABLE IF NOT EXISTS coach_memory (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                text       TEXT,
                created_at REAL
            );
            CREATE TABLE IF NOT EXISTS coach_notifications (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                text       TEXT,
                read       INTEGER DEFAULT 0,
                created_at REAL
            );
            CREATE TABLE IF NOT EXISTS journal_meta (
                ticket     INTEGER PRIMARY KEY,
                tags       TEXT,
                rating     INTEGER,
                note       TEXT,
                updated_at REAL
            );
            """
        )
        # seed kv defaults
        _kv_set_if_absent(c, "settings", json.dumps(DEFAULT_SETTINGS))
        _kv_set_if_absent(c, "chain_config", json.dumps(DEFAULT_CHAIN_CONFIG))
        _kv_set_if_absent(c, "locked_profiles", json.dumps({}))


def _kv_set_if_absent(c: sqlite3.Connection, key: str, value: str) -> None:
    row = c.execute("SELECT 1 FROM kv WHERE key=?", (key,)).fetchone()
    if not row:
        c.execute("INSERT INTO kv(key, value) VALUES(?,?)", (key, value))


def kv_get(key: str, default: Any = None) -> Any:
    with _conn() as c:
        row = c.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
    return json.loads(row["value"]) if row else default


def kv_set(key: str, value: Any) -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO kv(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, json.dumps(value)),
        )


def now() -> float:
    return time.time()


def iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
def check_token(x_nexus_token: Optional[str]) -> None:
    """Auth per EA e worker."""
    if not x_nexus_token or not secrets.compare_digest(x_nexus_token, BRIDGE_TOKEN):
        raise HTTPException(status_code=401, detail="invalid X-Nexus-Token")


def make_jwt(user: str) -> str:
    payload = {
        "sub": user,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def require_user(authorization: Optional[str] = Header(None)) -> str:
    """Auth per la dashboard (JWT Bearer)."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return data["sub"]
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="invalid or expired token")


# --------------------------------------------------------------------------- #
# App
# --------------------------------------------------------------------------- #
app = FastAPI(title="NEXUS self-hosted backend", version="2.0.13")


@app.on_event("startup")
def _startup() -> None:
    init_db()
    print(f"[NEXUS] backend up — db={DB_PATH} license_mode={LICENSE_MODE}")
    print(f"[NEXUS] dashboard user='{ADMIN_USER}'  bridge token set={'yes' if BRIDGE_TOKEN else 'no'}")


@app.get("/api/health")
def health():
    return {"ok": True, "service": "nexus-backend", "version": app.version, "ts": iso()}


# ======================= DASHBOARD AUTH ==================================== #
@app.post("/api/auth/login")
async def login(request: Request):
    body = await request.json()
    user = (body.get("username") or "").strip()
    pw = body.get("password") or ""
    ok = secrets.compare_digest(user, ADMIN_USER) and secrets.compare_digest(pw, ADMIN_PASSWORD)
    if not ok:
        raise HTTPException(status_code=401, detail="credenziali non valide")
    return {"token": make_jwt(user), "user": user}


@app.get("/api/auth/me")
def me(user: str = Depends(require_user)):
    return {"user": user}


# ======================= EA: PUSH / COMMAND =============================== #
@app.post("/api/ea/push")
async def ea_push(request: Request, x_nexus_token: Optional[str] = Header(None)):
    check_token(x_nexus_token)
    data = await request.json()
    magic = data.get("magic", 0)
    symbol = data.get("symbol", "?")
    key = f"{magic}:{symbol}"
    with _conn() as c:
        c.execute(
            "INSERT INTO ea_status(key,magic,symbol,payload,updated_at) VALUES(?,?,?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at, "
            "magic=excluded.magic, symbol=excluded.symbol",
            (key, magic, symbol, json.dumps(data), now()),
        )
    return {"ok": True}


@app.get("/api/ea/command")
def ea_command(x_nexus_token: Optional[str] = Header(None)):
    """L'EA fa polling qui. Restituiamo il comando piu' vecchio non consumato."""
    check_token(x_nexus_token)
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM ea_commands WHERE consumed=0 ORDER BY created_at ASC LIMIT 1"
        ).fetchone()
        if not row:
            return {"action": None}
        c.execute("UPDATE ea_commands SET consumed=1 WHERE id=?", (row["id"],))
    out = {"action": row["action"]}
    if row["payload"]:
        try:
            out.update(json.loads(row["payload"]))
        except Exception:
            pass
    return out


# ======================= EA: SETTINGS / LOCKED PROFILE =================== #
@app.get("/api/ea/settings")
def ea_settings(x_nexus_token: Optional[str] = Header(None)):
    check_token(x_nexus_token)
    return kv_get("settings", DEFAULT_SETTINGS)


@app.get("/api/ea/locked_profile")
def ea_locked_profile(symbol: str = "", x_nexus_token: Optional[str] = Header(None)):
    check_token(x_nexus_token)
    profiles = kv_get("locked_profiles", {})
    prof = profiles.get(symbol) or profiles.get("*")
    if not prof:
        return {"locked": False}
    return prof


# ======================= EA: STATS / HISTORY / DIAGNOSTICS =============== #
@app.post("/api/ea/strategy_stats")
async def ea_strategy_stats(request: Request, x_nexus_token: Optional[str] = Header(None)):
    check_token(x_nexus_token)
    data = await request.json()
    symbol = data.get("symbol", "?")
    with _conn() as c:
        c.execute(
            "INSERT INTO strategy_stats(symbol,payload,updated_at) VALUES(?,?,?) "
            "ON CONFLICT(symbol) DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at",
            (symbol, json.dumps(data), now()),
        )
    return {"ok": True}


@app.post("/api/ea/trade_history_sync")
async def ea_trade_history_sync(request: Request, x_nexus_token: Optional[str] = Header(None)):
    check_token(x_nexus_token)
    data = await request.json()
    trades = data.get("trades") if isinstance(data, dict) else data
    if not isinstance(trades, list):
        trades = [data]
    n = 0
    with _conn() as c:
        for t in trades:
            if not isinstance(t, dict):
                continue
            ticket = t.get("ticket") or t.get("deal") or t.get("id")
            if ticket is None:
                continue
            c.execute(
                "INSERT INTO trades(ticket,symbol,strategy,side,lots,open_price,close_price,"
                "pnl,open_time,close_time,reason,raw,synced_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(ticket) DO UPDATE SET symbol=excluded.symbol, strategy=excluded.strategy, "
                "side=excluded.side, lots=excluded.lots, open_price=excluded.open_price, "
                "close_price=excluded.close_price, pnl=excluded.pnl, open_time=excluded.open_time, "
                "close_time=excluded.close_time, reason=excluded.reason, raw=excluded.raw, "
                "synced_at=excluded.synced_at",
                (
                    int(ticket), t.get("symbol"), t.get("strategy"), t.get("side") or t.get("type"),
                    t.get("lots") or t.get("volume"), t.get("open_price") or t.get("openPrice"),
                    t.get("close_price") or t.get("closePrice"), t.get("pnl") or t.get("profit"),
                    t.get("open_time") or t.get("openTime"), t.get("close_time") or t.get("closeTime"),
                    t.get("reason"), json.dumps(t), now(),
                ),
            )
            n += 1
    return {"ok": True, "stored": n}


@app.post("/api/ea/trade_reason")
async def ea_trade_reason(request: Request, x_nexus_token: Optional[str] = Header(None)):
    check_token(x_nexus_token)
    data = await request.json()
    symbol = data.get("symbol", "?")
    with _conn() as c:
        c.execute(
            "INSERT INTO trade_reasons(symbol,payload,updated_at) VALUES(?,?,?) "
            "ON CONFLICT(symbol) DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at",
            (symbol, json.dumps(data), now()),
        )
    return {"ok": True}


@app.post("/api/ea/shadow_trades")
async def ea_shadow_trades(request: Request, x_nexus_token: Optional[str] = Header(None)):
    check_token(x_nexus_token)
    data = await request.json()
    with _conn() as c:
        c.execute(
            "INSERT INTO shadow_trades(payload,created_at) VALUES(?,?)",
            (json.dumps(data), now()),
        )
    return {"ok": True}


@app.post("/api/ea/visual_objects")
async def ea_visual_objects(request: Request, x_nexus_token: Optional[str] = Header(None)):
    check_token(x_nexus_token)
    data = await request.json()
    symbol = data.get("symbol", "?")
    with _conn() as c:
        c.execute(
            "INSERT INTO visual_objects(symbol,payload,updated_at) VALUES(?,?,?) "
            "ON CONFLICT(symbol) DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at",
            (symbol, json.dumps(data), now()),
        )
    return {"ok": True}


@app.get("/api/ea/visual_objects")
def ea_visual_objects_get(symbol: str = "", x_nexus_token: Optional[str] = Header(None)):
    check_token(x_nexus_token)
    with _conn() as c:
        row = c.execute("SELECT payload FROM visual_objects WHERE symbol=?", (symbol,)).fetchone()
    return json.loads(row["payload"]) if row else {"objects": []}


# ======================= LICENSE ========================================= #
@app.post("/api/license/verify")
async def license_verify(request: Request, x_nexus_token: Optional[str] = Header(None)):
    check_token(x_nexus_token)
    data = await request.json()
    key = data.get("key", "")
    account = data.get("account", 0)
    if LICENSE_MODE == "open":
        return {"valid": True, "trial": False, "expires_at": 0, "reason": "open-mode"}
    with _conn() as c:
        row = c.execute("SELECT * FROM licenses WHERE key=?", (key,)).fetchone()
    if not row:
        return {"valid": False, "trial": False, "expires_at": 0, "reason": "unknown-key"}
    if row["account"] and account and int(row["account"]) != int(account):
        return {"valid": False, "trial": False, "expires_at": 0, "reason": "account-mismatch"}
    exp = int(row["expires_at"] or 0)
    if exp and now() > exp:
        return {"valid": False, "trial": False, "expires_at": exp, "reason": "expired"}
    return {"valid": True, "trial": bool(row["trial"]), "expires_at": exp, "reason": "ok"}


# ======================= NOTIFY (Telegram) =============================== #
def _send_telegram(text: str) -> bool:
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        return False
    try:
        url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
        body = urllib.parse.urlencode({"chat_id": TG_CHAT_ID, "text": text}).encode()
        req = urllib.request.Request(url, data=body)
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status == 200
    except Exception as e:
        print(f"[NEXUS] telegram send failed: {e}")
        return False


@app.post("/api/notify/telegram")
async def notify_telegram(request: Request, x_nexus_token: Optional[str] = Header(None)):
    check_token(x_nexus_token)
    data = await request.json()
    text = data.get("text") or data.get("message") or json.dumps(data)
    delivered = _send_telegram(text)
    with _conn() as c:
        c.execute(
            "INSERT INTO notifications(text,delivered,created_at) VALUES(?,?,?)",
            (text, 1 if delivered else 0, now()),
        )
    return {"ok": True, "delivered": delivered}


# ======================= STRATEGY CHAIN ================================== #
@app.get("/api/strategy_chain/config_for_ea")
def chain_config_for_ea(x_nexus_token: Optional[str] = Header(None)):
    check_token(x_nexus_token)
    return kv_get("chain_config", DEFAULT_CHAIN_CONFIG)


@app.get("/api/strategy_chain/config")
def chain_config_get(user: str = Depends(require_user)):
    return kv_get("chain_config", DEFAULT_CHAIN_CONFIG)


@app.put("/api/strategy_chain/config")
async def chain_config_put(request: Request, user: str = Depends(require_user)):
    data = await request.json()
    kv_set("chain_config", data)
    return {"ok": True, "config": data}


# ======================= LOCAL BRIDGE (worker) =========================== #
@app.post("/api/local_bridge/heartbeat")
async def lb_heartbeat(request: Request, x_nexus_token: Optional[str] = Header(None)):
    check_token(x_nexus_token)
    data = await request.json()
    host = data.get("host_id", "default")
    with _conn() as c:
        c.execute(
            "INSERT INTO bridge_hosts(host_id,version,os,meta,last_seen) VALUES(?,?,?,?,?) "
            "ON CONFLICT(host_id) DO UPDATE SET version=excluded.version, os=excluded.os, "
            "meta=excluded.meta, last_seen=excluded.last_seen",
            (host, data.get("version"), data.get("os"), json.dumps(data), now()),
        )
    return {"ok": True}


@app.get("/api/local_bridge/poll")
def lb_poll(host_id: str = "default", x_nexus_token: Optional[str] = Header(None)):
    check_token(x_nexus_token)
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM bridge_commands WHERE host_id=? AND status='pending' "
            "ORDER BY created_at ASC LIMIT 1",
            (host_id,),
        ).fetchone()
        if not row:
            return {"action": None}
        c.execute("UPDATE bridge_commands SET status='sent' WHERE id=?", (row["id"],))
    return {
        "id": row["id"],
        "action": row["action"],
        "payload": json.loads(row["payload"]) if row["payload"] else {},
    }


@app.post("/api/local_bridge/ack")
async def lb_ack(request: Request, x_nexus_token: Optional[str] = Header(None)):
    check_token(x_nexus_token)
    data = await request.json()
    cmd_id = data.get("id")
    with _conn() as c:
        c.execute(
            "UPDATE bridge_commands SET status=?, result=?, error=?, done_at=? WHERE id=?",
            (
                "done" if data.get("ok") else "error",
                json.dumps(data.get("result")),
                data.get("error"),
                now(),
                cmd_id,
            ),
        )
    return {"ok": True}


@app.post("/api/local_bridge/enqueue")
async def lb_enqueue(request: Request, user: str = Depends(require_user)):
    data = await request.json()
    cmd_id = secrets.token_hex(8)
    with _conn() as c:
        c.execute(
            "INSERT INTO bridge_commands(id,host_id,action,payload,status,created_at) "
            "VALUES(?,?,?,?, 'pending', ?)",
            (cmd_id, data.get("host_id", "default"), data.get("action"),
             json.dumps(data.get("payload", {})), now()),
        )
    return {"ok": True, "id": cmd_id}


@app.get("/api/local_bridge/status")
def lb_status(user: str = Depends(require_user)):
    with _conn() as c:
        hosts = [dict(r) for r in c.execute("SELECT * FROM bridge_hosts ORDER BY last_seen DESC")]
        cmds = [dict(r) for r in c.execute(
            "SELECT id,host_id,action,status,error,created_at,done_at "
            "FROM bridge_commands ORDER BY created_at DESC LIMIT 30")]
    t = now()
    for h in hosts:
        h["online"] = (t - (h.get("last_seen") or 0)) < 90
    return {"hosts": hosts, "commands": cmds}


# ======================= DASHBOARD READ/WRITE (JWT) ====================== #
@app.get("/api/dashboard/overview")
def dash_overview(user: str = Depends(require_user)):
    t = now()
    with _conn() as c:
        eas = []
        for r in c.execute("SELECT * FROM ea_status ORDER BY updated_at DESC"):
            p = json.loads(r["payload"])
            p["_online"] = (t - r["updated_at"]) < 30
            p["_updated_ago"] = round(t - r["updated_at"], 1)
            eas.append(p)
        pending = c.execute("SELECT COUNT(*) n FROM ea_commands WHERE consumed=0").fetchone()["n"]
        hosts = [dict(r) for r in c.execute("SELECT host_id,version,last_seen FROM bridge_hosts")]
    for h in hosts:
        h["online"] = (t - (h.get("last_seen") or 0)) < 90
    return {"eas": eas, "pending_commands": pending, "bridge_hosts": hosts, "ts": iso()}


@app.post("/api/dashboard/command")
async def dash_command(request: Request, user: str = Depends(require_user)):
    """La dashboard accoda un comando per l'EA (pause/resume/close_all/...)."""
    data = await request.json()
    action = data.get("action")
    allowed = {"pause", "resume", "close_all", "close_position",
               "partial_close", "reset_anti_revenge", "reset_daily"}
    if action not in allowed:
        raise HTTPException(status_code=400, detail=f"action non valida (ammesse: {sorted(allowed)})")
    payload = {k: v for k, v in data.items() if k != "action"}
    cmd_id = secrets.token_hex(8)
    with _conn() as c:
        c.execute(
            "INSERT INTO ea_commands(id,action,payload,created_at,consumed) VALUES(?,?,?,?,0)",
            (cmd_id, action, json.dumps(payload), now()),
        )
    return {"ok": True, "id": cmd_id, "action": action}


@app.get("/api/dashboard/journal")
def dash_journal(limit: int = 200, user: str = Depends(require_user)):
    with _conn() as c:
        rows = [dict(r) for r in c.execute(
            "SELECT ticket,symbol,strategy,side,lots,open_price,close_price,pnl,"
            "open_time,close_time,reason FROM trades ORDER BY synced_at DESC LIMIT ?",
            (limit,))]
        agg = c.execute(
            "SELECT COUNT(*) n, COALESCE(SUM(pnl),0) total, "
            "SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END) wins, "
            "SUM(CASE WHEN pnl<0 THEN 1 ELSE 0 END) losses FROM trades").fetchone()
    return {"trades": rows, "summary": dict(agg)}


@app.get("/api/dashboard/strategy_stats")
def dash_strategy_stats(user: str = Depends(require_user)):
    with _conn() as c:
        rows = [dict(r) for r in c.execute("SELECT * FROM strategy_stats")]
    out = []
    for r in rows:
        out.append({"symbol": r["symbol"], "updated_at": r["updated_at"],
                    "data": json.loads(r["payload"])})
    return {"stats": out}


@app.get("/api/dashboard/shadow_trades")
def dash_shadow(limit: int = 100, user: str = Depends(require_user)):
    with _conn() as c:
        rows = [json.loads(r["payload"]) for r in c.execute(
            "SELECT payload FROM shadow_trades ORDER BY created_at DESC LIMIT ?", (limit,))]
    return {"shadow_trades": rows}


@app.get("/api/dashboard/trade_reasons")
def dash_reasons(user: str = Depends(require_user)):
    with _conn() as c:
        rows = [json.loads(r["payload"]) for r in c.execute("SELECT payload FROM trade_reasons")]
    return {"trade_reasons": rows}


@app.get("/api/dashboard/notifications")
def dash_notifications(limit: int = 50, user: str = Depends(require_user)):
    with _conn() as c:
        rows = [dict(r) for r in c.execute(
            "SELECT id,text,delivered,created_at FROM notifications ORDER BY created_at DESC LIMIT ?",
            (limit,))]
    return {"notifications": rows}


@app.get("/api/dashboard/settings")
def dash_settings_get(user: str = Depends(require_user)):
    return kv_get("settings", DEFAULT_SETTINGS)


@app.put("/api/dashboard/settings")
async def dash_settings_put(request: Request, user: str = Depends(require_user)):
    data = await request.json()
    kv_set("settings", data)
    return {"ok": True, "settings": data}


@app.get("/api/dashboard/locked_profiles")
def dash_locked_get(user: str = Depends(require_user)):
    return kv_get("locked_profiles", {})


@app.put("/api/dashboard/locked_profiles")
async def dash_locked_put(request: Request, user: str = Depends(require_user)):
    data = await request.json()
    kv_set("locked_profiles", data)
    return {"ok": True, "locked_profiles": data}


# ======================= HELPERS (frontend React) ======================= #
def _ea_rows():
    """Tutti gli EA con flag online, ordinati per ultimo aggiornamento."""
    t = now()
    out = []
    with _conn() as c:
        for r in c.execute("SELECT * FROM ea_status ORDER BY updated_at DESC"):
            p = json.loads(r["payload"])
            p["_online"] = (t - r["updated_at"]) < 30
            p["_updated_ago"] = round(t - r["updated_at"], 1)
            out.append(p)
    return out


def _primary_ea():
    rows = _ea_rows()
    primary = next((e for e in rows if e.get("_online")), rows[0] if rows else None)
    return primary, rows


def _trades_with_meta(limit=1000):
    with _conn() as c:
        rows = [dict(r) for r in c.execute(
            "SELECT * FROM trades ORDER BY synced_at DESC LIMIT ?", (limit,))]
        meta = {m["ticket"]: dict(m) for m in c.execute("SELECT * FROM journal_meta")}
    out = []
    for r in rows:
        m = meta.get(r["ticket"], {})
        out.append({
            "ticket": r["ticket"], "symbol": r["symbol"], "strategy": r["strategy"],
            "side": r["side"], "lots": r["lots"], "openPrice": r["open_price"],
            "closePrice": r["close_price"], "pnl": r["pnl"], "openTime": r["open_time"],
            "closeTime": r["close_time"], "reason": r["reason"],
            "journal_tags": (json.loads(m["tags"]) if m.get("tags") else []),
            "journal_rating": m.get("rating"),
            "journal_note": m.get("note"),
        })
    return out


def _enqueue_ea_command(action, payload=None):
    cmd_id = secrets.token_hex(8)
    with _conn() as c:
        c.execute(
            "INSERT INTO ea_commands(id,action,payload,created_at,consumed) VALUES(?,?,?,?,0)",
            (cmd_id, action, json.dumps(payload or {}), now()),
        )
    return cmd_id


def _anthropic_chat(system: str, messages: list, max_tokens: int = 1024):
    """Chiama la Messages API di Anthropic via stdlib. Ritorna (testo, errore)."""
    if not ANTHROPIC_API_KEY:
        return None, "ANTHROPIC_API_KEY non configurata sul backend (impostala su Render)."
    body = json.dumps({
        "model": COACH_MODEL, "max_tokens": max_tokens,
        "system": system, "messages": messages,
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body,
        headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read())
        text = "".join(p.get("text", "") for p in data.get("content", []) if p.get("type") == "text")
        return text, None
    except urllib.error.HTTPError as e:
        return None, f"Anthropic HTTP {e.code}: {e.read().decode(errors='replace')[:300]}"
    except Exception as e:
        return None, str(e)


# ======================= EA STATUS / HEALTH (JWT) ======================= #
@app.get("/api/ea/status")
def ea_status_dash(user: str = Depends(require_user)):
    primary, rows = _primary_ea()
    if not primary:
        return {"online": False, "connected": False, "eas": [], "demo": False}
    return {"online": bool(primary.get("_online")), "connected": True, "eas": rows, **primary}


@app.get("/api/ea/health")
def ea_health_dash(user: str = Depends(require_user)):
    primary, rows = _primary_ea()
    if not primary:
        return {"online": False, "ea_count": 0, "demo": False}
    return {
        "online": bool(primary.get("_online")),
        "ea_count": len(rows),
        "last_update_sec": primary.get("_updated_ago"),
        "version": primary.get("version"),
        "symbol": primary.get("symbol"),
        "account": primary.get("magic"),
        "balance": primary.get("balance"),
        "equity": primary.get("equity"),
    }


@app.post("/api/ea/command")
async def ea_command_post(request: Request, user: str = Depends(require_user)):
    """Dashboard React accoda un comando per l'EA (POST, JWT)."""
    data = await request.json()
    action = data.get("action") or data.get("command")
    allowed = {"pause", "resume", "close_all", "close_position",
               "partial_close", "reset_anti_revenge", "reset_daily"}
    if action not in allowed:
        raise HTTPException(status_code=400, detail=f"action non valida (ammesse: {sorted(allowed)})")
    payload = {k: v for k, v in data.items() if k not in ("action", "command")}
    cmd_id = _enqueue_ea_command(action, payload)
    return {"ok": True, "id": cmd_id, "action": action}


# ======================= SETTINGS / STRATEGIES (JWT) ==================== #
@app.get("/api/settings")
def settings_get(user: str = Depends(require_user)):
    return kv_get("settings", DEFAULT_SETTINGS)


@app.put("/api/settings")
@app.post("/api/settings")
async def settings_save(request: Request, user: str = Depends(require_user)):
    data = await request.json()
    kv_set("settings", data)
    return {"ok": True, "settings": data}


@app.get("/api/strategies")
def strategies_get(user: str = Depends(require_user)):
    primary, _ = _primary_ea()
    enabled_map = (primary or {}).get("strategies", {}) or {}
    override = kv_get("strategies_override", {})
    # stats per-strategia (se presenti)
    stats = {}
    with _conn() as c:
        for r in c.execute("SELECT payload FROM strategy_stats"):
            for s in (json.loads(r["payload"]).get("strategies") or []):
                stats[s.get("name")] = s
    out = []
    for name in STRAT_LIST:
        en = override.get(name, enabled_map.get(name))
        st = stats.get(name, {})
        out.append({
            "name": name, "id": name,
            "enabled": (bool(en) if en is not None else None),
            "called": st.get("called"), "signals": st.get("signals"),
            "executed": st.get("executed"), "wins": st.get("wins"),
            "losses": st.get("losses"), "health": st.get("health"),
        })
    return {"strategies": out, "demo": not bool(enabled_map or stats)}


@app.post("/api/strategies")
@app.put("/api/strategies")
async def strategies_save(request: Request, user: str = Depends(require_user)):
    data = await request.json()
    override = data.get("strategies") if isinstance(data, dict) else data
    if isinstance(override, list):
        override = {s["name"]: s.get("enabled") for s in override if "name" in s}
    kv_set("strategies_override", override or {})
    return {"ok": True, "strategies_override": override}


# ======================= ANALYTICS (JWT) =============================== #
@app.get("/api/analytics/trades")
def analytics_trades(limit: int = 500, user: str = Depends(require_user)):
    trades = _trades_with_meta(limit)
    return {"trades": trades, "count": len(trades), "demo": len(trades) == 0}


@app.get("/api/analytics/summary")
def analytics_summary(user: str = Depends(require_user)):
    trades = _trades_with_meta(100000)
    if not trades:
        return {"demo": True, "trades": 0, "net_pnl": 0, "win_rate": 0,
                "profit_factor": 0, "wins": 0, "losses": 0}
    wins = [t for t in trades if (t["pnl"] or 0) > 0]
    losses = [t for t in trades if (t["pnl"] or 0) < 0]
    gross_win = sum(t["pnl"] for t in wins)
    gross_loss = abs(sum(t["pnl"] for t in losses))
    return {
        "demo": False, "trades": len(trades),
        "net_pnl": round(sum(t["pnl"] or 0 for t in trades), 2),
        "wins": len(wins), "losses": len(losses),
        "win_rate": round(len(wins) / len(trades) * 100, 1),
        "profit_factor": round(gross_win / gross_loss, 2) if gross_loss else None,
        "avg_win": round(gross_win / len(wins), 2) if wins else 0,
        "avg_loss": round(-gross_loss / len(losses), 2) if losses else 0,
    }


@app.get("/api/analytics/by_reason")
def analytics_by_reason(user: str = Depends(require_user)):
    trades = _trades_with_meta(100000)
    groups = {}
    for t in trades:
        k = t.get("reason") or "—"
        g = groups.setdefault(k, {"reason": k, "count": 0, "pnl": 0.0, "wins": 0})
        g["count"] += 1
        g["pnl"] += (t["pnl"] or 0)
        if (t["pnl"] or 0) > 0:
            g["wins"] += 1
    for g in groups.values():
        g["pnl"] = round(g["pnl"], 2)
        g["win_rate"] = round(g["wins"] / g["count"] * 100, 1) if g["count"] else 0
    return {"by_reason": list(groups.values()), "demo": len(trades) == 0}


@app.post("/api/analytics/whatif")
async def analytics_whatif(request: Request, user: str = Depends(require_user)):
    """Ricalcola il P&L escludendo una strategia o un motivo."""
    body = await request.json()
    excl_strat = set(body.get("exclude_strategies") or [])
    excl_reason = set(body.get("exclude_reasons") or [])
    trades = _trades_with_meta(100000)
    kept = [t for t in trades
            if t.get("strategy") not in excl_strat and t.get("reason") not in excl_reason]
    base = round(sum(t["pnl"] or 0 for t in trades), 2)
    new = round(sum(t["pnl"] or 0 for t in kept), 2)
    return {"demo": len(trades) == 0, "baseline_pnl": base, "whatif_pnl": new,
            "delta": round(new - base, 2), "trades_kept": len(kept), "trades_total": len(trades)}


# ======================= JOURNAL TAGS (JWT) ============================ #
PRESET_TAGS = ["good-entry", "fomo", "news-spike", "revenge", "perfect-exit",
               "early-exit", "late-entry", "model-A", "model-B"]


@app.get("/api/journal/tags")
def journal_tags(user: str = Depends(require_user)):
    used = set()
    with _conn() as c:
        for r in c.execute("SELECT tags FROM journal_meta WHERE tags IS NOT NULL"):
            try:
                used.update(json.loads(r["tags"]))
            except Exception:
                pass
    return {"preset": PRESET_TAGS, "used": sorted(used)}


@app.post("/api/trades/{ticket}/tag")
async def trade_tag(ticket: int, request: Request, user: str = Depends(require_user)):
    body = await request.json()
    tags = body.get("tags")
    if isinstance(tags, str):
        tags = [tags]
    with _conn() as c:
        c.execute(
            "INSERT INTO journal_meta(ticket,tags,rating,note,updated_at) VALUES(?,?,?,?,?) "
            "ON CONFLICT(ticket) DO UPDATE SET "
            "tags=COALESCE(excluded.tags,journal_meta.tags), "
            "rating=COALESCE(excluded.rating,journal_meta.rating), "
            "note=COALESCE(excluded.note,journal_meta.note), updated_at=excluded.updated_at",
            (ticket, json.dumps(tags) if tags is not None else None,
             body.get("rating"), body.get("note"), now()),
        )
    return {"ok": True, "ticket": ticket}


# ======================= LICENSE CRUD (JWT) ============================ #
@app.get("/api/license/list")
def license_list(user: str = Depends(require_user)):
    with _conn() as c:
        rows = [dict(r) for r in c.execute("SELECT * FROM licenses ORDER BY key")]
    return {"licenses": rows, "mode": LICENSE_MODE}


@app.post("/api/license/create")
async def license_create(request: Request, user: str = Depends(require_user)):
    body = await request.json()
    key = body.get("key") or ("NXS-" + secrets.token_hex(6).upper())
    with _conn() as c:
        c.execute(
            "INSERT INTO licenses(key,account,trial,expires_at,note) VALUES(?,?,?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET account=excluded.account, trial=excluded.trial, "
            "expires_at=excluded.expires_at, note=excluded.note",
            (key, body.get("account", 0), 1 if body.get("trial") else 0,
             int(body.get("expires_at", 0) or 0), body.get("note")),
        )
    return {"ok": True, "key": key}


@app.patch("/api/license/{key}")
async def license_update(key: str, request: Request, user: str = Depends(require_user)):
    body = await request.json()
    fields, vals = [], []
    for col in ("account", "trial", "expires_at", "note"):
        if col in body:
            fields.append(f"{col}=?")
            vals.append(body[col])
    if not fields:
        return {"ok": True, "unchanged": True}
    vals.append(key)
    with _conn() as c:
        c.execute(f"UPDATE licenses SET {', '.join(fields)} WHERE key=?", vals)
    return {"ok": True, "key": key}


@app.delete("/api/license/{key}")
def license_delete(key: str, user: str = Depends(require_user)):
    with _conn() as c:
        c.execute("DELETE FROM licenses WHERE key=?", (key,))
    return {"ok": True, "deleted": key}


# ======================= BACKTEST (JWT, demo) ========================== #
def _demo_equity(points=60, start=10000, drift=35):
    eq, cur = [], start
    for i in range(points):
        cur += drift + ((i * 37) % 90) - 45
        eq.append(round(cur, 2))
    return eq


@app.post("/api/backtest/run")
async def backtest_run(request: Request, user: str = Depends(require_user)):
    body = await request.json()
    eq = _demo_equity()
    return {"demo": True, "params": body, "equity_curve": eq,
            "net_pnl": round(eq[-1] - eq[0], 2), "trades": 142,
            "win_rate": 64.1, "profit_factor": 1.78, "max_dd_pct": 8.4,
            "note": "Motore di backtest non ancora implementato — dati dimostrativi."}


@app.post("/api/backtest/optimize")
async def backtest_optimize(request: Request, user: str = Depends(require_user)):
    body = await request.json()
    grid = [{"MinScore": ms, "AtrSLMult": round(sl, 1),
             "pf": round(1.2 + (ms % 7) * 0.07 + sl * 0.05, 2),
             "net_pnl": 800 + (ms * 13) % 1400}
            for ms in range(60, 81, 5) for sl in (1.0, 1.2, 1.5)]
    grid.sort(key=lambda r: r["pf"], reverse=True)
    return {"demo": True, "params": body, "results": grid, "best": grid[0]}


@app.get("/api/backtest/management_report")
def backtest_mgmt(user: str = Depends(require_user)):
    return {"demo": True, "rows": [
        {"metric": "Profit Factor", "value": 1.78},
        {"metric": "Sharpe", "value": 1.42},
        {"metric": "Max Drawdown %", "value": 8.4},
        {"metric": "Recovery Factor", "value": 3.1},
        {"metric": "Expectancy (R)", "value": 0.34},
    ]}


@app.get("/api/backtest/multi_tf_report")
def backtest_mtf(user: str = Depends(require_user)):
    return {"demo": True, "timeframes": [
        {"tf": "M5", "pf": 1.41, "trades": 380, "win_rate": 58.2},
        {"tf": "M15", "pf": 1.78, "trades": 142, "win_rate": 64.1},
        {"tf": "H1", "pf": 2.05, "trades": 61, "win_rate": 67.0},
    ]}


@app.get("/api/backtest/locked_profile/all")
def backtest_locked_all(user: str = Depends(require_user)):
    profiles = kv_get("locked_profiles", {})
    return {"locked_profiles": profiles, "demo": not bool(profiles)}


# ======================= CALENDAR (JWT, demo) ========================== #
@app.get("/api/calendar")
def calendar(user: str = Depends(require_user)):
    base = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    events = [
        {"time": (base + timedelta(hours=2)).isoformat(), "currency": "USD",
         "impact": "high", "event": "Core CPI m/m"},
        {"time": (base + timedelta(hours=5)).isoformat(), "currency": "EUR",
         "impact": "medium", "event": "ECB President Speech"},
        {"time": (base + timedelta(hours=26)).isoformat(), "currency": "USD",
         "impact": "high", "event": "Non-Farm Payrolls"},
    ]
    return {"events": events, "demo": True,
            "note": "Calendario dimostrativo — collegare un feed news reale in seguito."}


# ======================= DOWNLOADS ===================================== #
@app.get("/api/downloads/local_worker")
def download_worker(user: str = Depends(require_user)):
    if WORKER_FILE.exists():
        return FileResponse(str(WORKER_FILE), media_type="text/x-python",
                            filename="nexus_local_worker.py")
    raise HTTPException(status_code=404, detail="worker non incluso in questa build")


# ======================= AI COACH (JWT) ================================ #
def _coach_system(primary, context, memory):
    lines = [
        "Sei il Trading Coach del sistema NEXUS EA (Expert Advisor MetaTrader 5).",
        "Aiuti l'utente ad analizzare i trade, capire le strategie, regolare i parametri "
        "di rischio e proporre azioni concrete. Rispondi in italiano, conciso e operativo.",
        "Non promettere profitti; ricorda i rischi quando rilevante.",
    ]
    if primary:
        lines.append(
            f"STATO EA: symbol={primary.get('symbol')} online={primary.get('_online')} "
            f"balance={primary.get('balance')} equity={primary.get('equity')} "
            f"floatPnL={primary.get('floatPnL')} dailyPnL={primary.get('dailyPnL')} "
            f"drawdown%={primary.get('drawdownPct')} paused={primary.get('eaPaused')} "
            f"tradesToday={primary.get('tradesToday')} regime={primary.get('regime')} "
            f"session={primary.get('session')} htfBias={primary.get('htfBias')}.")
    else:
        lines.append("STATO EA: nessun EA collegato in questo momento.")
    if context:
        lines.append("CONTEXT extra dal frontend: " + json.dumps(context)[:1500])
    if memory:
        lines.append("MEMORIA PERSISTENTE (note utente):\n- " + "\n- ".join(memory[:20]))
    lines.append("Se suggerisci un'azione applicabile dall'EA (pause, resume, close_all, "
                 "reset_anti_revenge, reset_daily), indicala chiaramente così l'utente può confermarla.")
    return "\n".join(lines)


@app.post("/api/coach/chat")
async def coach_chat(request: Request, user: str = Depends(require_user)):
    body = await request.json()
    msgs = body.get("messages") or []
    context = body.get("context") or {}
    norm = [{"role": ("assistant" if m.get("role") == "assistant" else "user"),
             "content": str(m.get("content", ""))} for m in msgs if m.get("content")]
    if not norm:
        raise HTTPException(status_code=400, detail="messages vuoto")
    primary, _ = _primary_ea()
    with _conn() as c:
        memory = [r["text"] for r in c.execute("SELECT text FROM coach_memory ORDER BY created_at DESC LIMIT 20")]
    system = _coach_system(primary, context, memory)
    text, err = _anthropic_chat(system, norm)
    if err:
        return {"reply": f"⚠️ Coach non disponibile: {err}", "demo": True, "error": err}
    return {"reply": text, "demo": False, "model": COACH_MODEL}


@app.get("/api/coach/proactive_alerts")
def coach_alerts(user: str = Depends(require_user)):
    """Alert deterministici dallo stato EA (no AI)."""
    primary, _ = _primary_ea()
    alerts = []
    if not primary:
        return {"alerts": [], "demo": False}
    dd = primary.get("drawdownPct") or 0
    if dd >= 4:
        alerts.append({"level": "high", "code": "drawdown",
                       "text": f"Drawdown giornaliero elevato ({dd:.1f}%). Valuta la pausa."})
    if primary.get("consecLosses", 0) >= 3:
        alerts.append({"level": "medium", "code": "anti_revenge",
                       "text": f"{primary.get('consecLosses')} perdite consecutive: anti-revenge potrebbe attivarsi."})
    if primary.get("newsBlock"):
        alerts.append({"level": "medium", "code": "news",
                       "text": "Blocco news attivo: news ad alto impatto imminente."})
    if primary.get("eaPaused"):
        alerts.append({"level": "low", "code": "paused", "text": "L'EA è in pausa."})
    if not primary.get("_online"):
        alerts.append({"level": "high", "code": "offline", "text": "EA offline: nessun dato recente."})
    return {"alerts": alerts, "demo": False}


@app.post("/api/coach/apply_action")
async def coach_apply(request: Request, user: str = Depends(require_user)):
    body = await request.json()
    action = body.get("action")
    allowed = {"pause", "resume", "close_all", "reset_anti_revenge", "reset_daily"}
    if action not in allowed:
        raise HTTPException(status_code=400, detail=f"azione non applicabile: {action}")
    cmd_id = _enqueue_ea_command(action, body.get("payload"))
    with _conn() as c:
        c.execute("INSERT INTO coach_notifications(text,read,created_at) VALUES(?,0,?)",
                  (f"Azione applicata dal Coach: {action}", now()))
    return {"ok": True, "id": cmd_id, "action": action}


@app.get("/api/coach/memory")
def coach_memory_get(user: str = Depends(require_user)):
    with _conn() as c:
        rows = [dict(r) for r in c.execute(
            "SELECT id,text,created_at FROM coach_memory ORDER BY created_at DESC")]
    return {"memory": rows}


@app.post("/api/coach/memory")
async def coach_memory_add(request: Request, user: str = Depends(require_user)):
    body = await request.json()
    text = (body.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text vuoto")
    with _conn() as c:
        cur = c.execute("INSERT INTO coach_memory(text,created_at) VALUES(?,?)", (text, now()))
        mid = cur.lastrowid
    return {"ok": True, "id": mid}


@app.delete("/api/coach/memory/{mid}")
def coach_memory_del(mid: int, user: str = Depends(require_user)):
    with _conn() as c:
        c.execute("DELETE FROM coach_memory WHERE id=?", (mid,))
    return {"ok": True, "deleted": mid}


@app.get("/api/coach/notifications")
def coach_notifications(user: str = Depends(require_user)):
    with _conn() as c:
        unread = c.execute("SELECT COUNT(*) n FROM coach_notifications WHERE read=0").fetchone()["n"]
        rows = [dict(r) for r in c.execute(
            "SELECT id,text,read,created_at FROM coach_notifications ORDER BY created_at DESC LIMIT 30")]
    return {"unread": unread, "notifications": rows}


@app.post("/api/coach/notifications/read")
def coach_notifications_read(user: str = Depends(require_user)):
    with _conn() as c:
        c.execute("UPDATE coach_notifications SET read=1 WHERE read=0")
    return {"ok": True}


# ======================= STATIC SITE ===================================== #
# Sito multi-pagina (index/login/dashboard/performance/prezzi/faq/strategia).
# Montato su "/" DOPO le route /api: html=True serve index.html sulla root e
# i singoli .html sui rispettivi path. Le route API sopra hanno la precedenza.
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="site")
else:
    @app.get("/")
    def _no_site():
        return JSONResponse({"service": "nexus-backend", "site": "static/ mancante"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8001")))
