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

STATIC_DIR = Path(__file__).resolve().parent / "static"

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
