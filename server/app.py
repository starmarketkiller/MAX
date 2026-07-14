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
import backtest
import bt_verdict
from fastapi import FastAPI, Request, Header, HTTPException, Depends, Response, Cookie
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
COOKIE_SECURE  = os.environ.get("NEXUS_COOKIE_SECURE", "true").lower() == "true"
SESSION_COOKIE = "nexus_session"
DB_PATH        = os.environ.get("NEXUS_DB_PATH", str(Path(__file__).resolve().parent / "nexus.db"))
TG_BOT_TOKEN   = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TG_CHAT_ID     = os.environ.get("TELEGRAM_CHAT_ID", "")
LICENSE_MODE   = os.environ.get("NEXUS_LICENSE_MODE", "open")  # open | strict

# AI Coach (API Claude). La chiave va impostata su Render come ANTHROPIC_API_KEY.
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
COACH_MODEL       = os.environ.get("NEXUS_COACH_MODEL", "claude-opus-4-8")

STATIC_DIR = Path(__file__).resolve().parent / "static"
WORKER_FILE = Path(__file__).resolve().parent / "nexus_local_worker.py"
SEED_FILE = Path(__file__).resolve().parent / "seed_results.json"
SEED_LIBRARY_FILE = Path(__file__).resolve().parent / "seed_library.json"
SEED_RECIPE_FILE = Path(__file__).resolve().parent / "seed_recipe.json"

# Elenco strategie note (dal contratto EA). Usato da backtest/strategies.
# Le 36 strategie reali dell'EA (estratte dai sorgenti MQL5).
STRAT_LIST = backtest.STRAT_NAMES_36

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
    # Stop/target/trailing (default reali dell'EA, NXS_Inputs.mqh)
    "ATR_SL_Mult": 2.0,
    "ATR_TP_Mult": 2.6,
    "BE_TriggerATR": 1.0,
    "TrailActivateATR": 1.5,
    "TrailDistanceATR": 1.0,
    # SL/TP proporzionati al timeframe di origine del segnale (v2.0.21)
    "TF_SLTP_H1": 2.0,
    "TF_SLTP_H4": 3.5,
    "TF_SLTP_D1": 5.0,
    # Sessioni
    "AsianScoreMin": 72.0,
    "LondonScoreMin": 68.0,
    "OverlapScoreMin": 66.0,
    "NYScoreMin": 68.0,
    "AfterNYScoreMin": 74.0,
    # Anti-revenge / struttura
    "AntiRevengeLosses": 3,
    "AntiRevengeMin": 60,
    "SwingWing": 3,
    "OBDisplacement": 1.5,
    "FVGMinBody": 0.5,
    "ReactionTol": 0.3,
    # Protezioni equity/tempo
    "ESL_IsPercent": True,
    "ESL_Value": 5.0,
    "DPT_IsPercent": True,
    "DPT_Value": 3.0,
    "MaxHoldHours": 4,
    "MaxLossPosPct": 2.0,
    "AutoCloseMin": 15,
    "MarketCloseGMT": 21,
    # Confluenza / cap / cooldown
    "ConfluenceBonus2": 10,
    "ConfluenceBonus3": 20,
    "ConfluenceBonus4": 30,
    "ADXRsiScoreCap": 70,
    "MaxConsecPerStrategy": 3,
    "StrategyCooldownMin": 30,
    # Spread / volatilità
    "MaxSpreadAtrPct": 8.0,
    "MaxSpreadPoints": 0,
    "LowVolAtrPct": 0.15,
    "HighVolAtrPct": 0.6,
    # Gate booleani
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


def require_user(authorization: Optional[str] = Header(None),
                 nexus_session: Optional[str] = Cookie(None)) -> str:
    """Auth dashboard: accetta cookie httpOnly (React) OPPURE Bearer (sito statico)."""
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    elif nexus_session:
        token = nexus_session
    if not token:
        raise HTTPException(status_code=401, detail="not authenticated")
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return data["sub"]
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="invalid or expired token")


# --------------------------------------------------------------------------- #
# App
# --------------------------------------------------------------------------- #
app = FastAPI(title="NEXUS self-hosted backend", version="4.3.0-4d-parallax-impact-fx")


def _seed_strategy_results() -> None:
    """Importa i risultati reali del backtest (server/seed_results.json) come
    strategy library + locked profile di default. Idempotente (hash del file)."""
    if not SEED_FILE.exists():
        return
    try:
        raw = SEED_FILE.read_bytes()
        data = json.loads(raw)
    except Exception as e:
        print(f"[NEXUS] seed parse failed: {e}")
        return
    marker = hashlib.sha256(raw).hexdigest()[:16]
    if kv_get("seed_version") == marker:
        return  # già importato questa versione
    results = data.get("results", [])
    lib = [{
        "name": r["strategy"], "strategy": r["strategy"], "symbol": "",
        "timeframe": r.get("timeframe", "D1"), "management": r.get("management"),
        "trades": r.get("trades"), "win_rate": r.get("win_rate"),
        "profit_factor": r.get("profit_factor"), "sharpe": r.get("sharpe"),
        "max_dd": r.get("max_dd"), "net": r.get("net"),
        "evaluated": r.get("evaluated", True), "params": r.get("params", {}),
    } for r in results if r.get("strategy")]
    kv_set("strategy_results", lib)
    # locked profile di default "*" = miglior Sharpe tra le strategie valutate
    evaluated = [r for r in lib if r.get("evaluated")]
    best = max(evaluated, key=lambda r: (r.get("sharpe") or -9)) if evaluated else None
    if best:
        profiles = kv_get("locked_profiles", {})
        profiles.setdefault("*", {
            "locked": True, "label": f"{best['strategy']} · {best.get('management')}",
            "saved_at": iso(), "strategy": best["strategy"], "management": best.get("management"),
            "metrics": {"sharpe": best.get("sharpe"), "profit_factor": best.get("profit_factor"),
                        "win_rate": best.get("win_rate"), "max_dd": best.get("max_dd")},
            "params": best.get("params", {}),
        })
        kv_set("locked_profiles", profiles)
    kv_set("seed_version", marker)
    print(f"[NEXUS] seeded {len(lib)} strategy results — default lock = {best and best['strategy']}")


def _seed_backtest_library() -> None:
    """Carica la libreria sweep (seed_library.json) — 36 strat × coppia × gestione."""
    if not SEED_LIBRARY_FILE.exists():
        return
    try:
        raw = SEED_LIBRARY_FILE.read_bytes()
        data = json.loads(raw)
    except Exception as e:
        print(f"[NEXUS] seed_library parse failed: {e}")
        return
    marker = hashlib.sha256(raw).hexdigest()[:16]
    if kv_get("library_version") == marker:
        return
    rows = data.get("rows", [])
    kv_set("backtest_library", rows)
    kv_set("library_version", marker)
    print(f"[NEXUS] seeded backtest library — {len(rows)} rows (sweep)")


def _seed_recipe() -> None:
    """Carica la ricetta per-strategia (seed_recipe.json = best_per_strategy dal
    motore): 29 strategie ognuna coi SUOI parametri/gate/verdetto migliori.
    Serve alla Strategy Library per mostrare TUTTE le strategie con i dati reali."""
    if not SEED_RECIPE_FILE.exists():
        return
    try:
        raw = SEED_RECIPE_FILE.read_bytes()
        data = json.loads(raw)
    except Exception as e:
        print(f"[NEXUS] seed_recipe parse failed: {e}")
        return
    marker = hashlib.sha256(raw).hexdigest()[:16]
    if kv_get("recipe_version") == marker:
        return
    kv_set("strategy_recipe", data)
    kv_set("recipe_version", marker)
    print(f"[NEXUS] seeded strategy recipe — {len(data.get('table', []))} strategie")


def _recipe_library_rows(symbol=""):
    """Converte la ricetta per-strategia (strategy_recipe) in righe Library."""
    rec = kv_get("strategy_recipe", {}) or {}
    table = rec.get("table") or []
    rsym = rec.get("symbol", "XAUUSD")
    gtf = str(rec.get("timeframe", "D1")).lower()
    gtf = "1d" if gtf in ("d1", "1d", "") else gtf
    if symbol and symbol != rsym:
        return []
    rows = []
    for r in table:
        # multi-TF: ogni strategia porta il SUO timeframe migliore (campo 'tf').
        tf = str(r.get("tf", gtf)).lower()
        tf = "1d" if tf in ("d1", "1d", "") else tf
        variant = "baseline"
        if r.get("trailing_atr"):
            variant = f"trail_{r.get('trailing_atr')}atr"
        elif r.get("breakeven_r"):
            variant = f"be_{r.get('breakeven_r')}R"
        rows.append({
            "strategy": r.get("strategy"), "symbol": rsym, "timeframe": tf,
            "variant": variant,
            "atr_sl_mult": r.get("atr_sl"), "atr_tp_mult": r.get("atr_tp"),
            "overrides": {
                "htf_filter": r.get("htf_filter"), "breakeven_r": r.get("breakeven_r"),
                "trailing_atr": r.get("trailing_atr"), "verdict": r.get("verdict"),
                "expectancy_r": r.get("exp"), "robust": r.get("robust"),
                "risk_pct": r.get("risk_pct"), "best_tf": r.get("tf"),
            },
            "metrics": {
                "n_trades": r.get("trades"), "win_rate_pct": r.get("wr"),
                "profit_factor": r.get("pf"), "sharpe": r.get("robust"),
                "max_dd_pct": r.get("dd"), "total_return_pct": r.get("net"),
            },
        })
    return rows


@app.on_event("startup")
def _startup() -> None:
    init_db()
    _seed_strategy_results()
    _seed_backtest_library()
    _seed_recipe()
    print(f"[NEXUS] backend up — db={DB_PATH} license_mode={LICENSE_MODE}")
    print(f"[NEXUS] dashboard user='{ADMIN_USER}'  bridge token set={'yes' if BRIDGE_TOKEN else 'no'}")


@app.get("/api/health")
def health():
    # coach_configured è non-segreto: dice solo SE la chiave è presente, non il valore.
    return {"ok": True, "service": "nexus-backend", "version": app.version, "ts": iso(),
            "coach_configured": bool(ANTHROPIC_API_KEY), "coach_model": COACH_MODEL}


# ======================= DASHBOARD AUTH ==================================== #
def _user_obj():
    return {"email": ADMIN_USER, "name": ADMIN_USER, "role": "admin"}


@app.post("/api/auth/login")
async def login(request: Request, response: Response):
    body = await request.json()
    ident = (body.get("email") or body.get("username") or "").strip()
    pw = body.get("password") or ""
    ok = secrets.compare_digest(ident, ADMIN_USER) and secrets.compare_digest(pw, ADMIN_PASSWORD)
    if not ok:
        raise HTTPException(status_code=401, detail="credenziali non valide")
    token = make_jwt(ADMIN_USER)
    # Cookie httpOnly per il frontend React (withCredentials).
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax",
                        secure=COOKIE_SECURE, max_age=JWT_HOURS * 3600, path="/")
    # token nel body per retrocompatibilità col sito statico (Bearer).
    return {"ok": True, "user": _user_obj(), "token": token}


@app.post("/api/auth/logout")
def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}


@app.get("/api/auth/me")
def me(user: str = Depends(require_user)):
    # auth.jsx fa setUser(data): ritorniamo direttamente l'oggetto utente.
    return _user_obj()


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
    # serie equity per il grafico live (/ea/history) — cap a 300 punti
    try:
        hist = kv_get("equity_history", [])
        hist.append({"ts": iso(), "equity": data.get("equity"),
                     "balance": data.get("balance"), "floatPnL": data.get("floatPnL")})
        kv_set("equity_history", hist[-300:])
    except Exception:
        pass
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
    out = {**DEFAULT_SETTINGS, **(kv_get("settings", {}) or {})}
    # Strategie disattivate dalla pagina "Strategie" della dashboard: l'EA le
    # legge in runtime (poll ogni 15s) e blocca l'apertura di nuovi trade per
    # queste strategie senza bisogno di riavvio/ricompilazione del profilo.
    # Sorgente primaria: settings.strategies ({NOME: bool}); fallback legacy:
    # strategies_override. Un nome è "disabilitato" se il valore è esplicito False.
    disabled = []
    strat_map = out.get("strategies") or {}
    for name, en in strat_map.items():
        if en is not None and not en:
            disabled.append(name)
    override = kv_get("strategies_override", {}) or {}
    for name, en in override.items():
        if en is not None and not en and name not in disabled:
            disabled.append(name)
    out["strategies_disabled"] = disabled
    # Moltiplicatori di rischio per-strategia (loop di ottimizzazione live):
    # l'EA li applica al lotto in fase di apertura, per strategia.
    try:
        out["strategy_risk"] = _strategy_risk_map()
    except Exception:
        out["strategy_risk"] = {}
    return out


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


def _normalize_time(s):
    """Normalize EA-supplied timestamps to ISO-8601 so the frontend's
    `new Date(...)` always parses them. Older EA builds sent MT5's native
    "YYYY.MM.DD HH:MM:SS" format, which JS does not reliably parse and
    renders as "Invalid Date" — this heals both old and new rows on next
    write. Leaves the value untouched if it doesn't match a known format."""
    if not s:
        return s
    s = str(s).strip()
    for fmt in ("%Y.%m.%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).isoformat()
        except ValueError:
            continue
    return s


def _upsert_trade(c, t, symbol_fallback=None):
    """Upsert di un trade nella tabella `trades` (letta da Journal/Analytics).
    COALESCE protegge i campi ricchi (symbol/strategy/open_*/close_time) quando
    arriva un aggiornamento parziale (es. un push senza timestamp)."""
    ticket = t.get("ticket") or t.get("deal") or t.get("id")
    if ticket is None:
        return False
    symbol = t.get("symbol")
    if not symbol or symbol == "?":
        symbol = symbol_fallback
    open_price = t.get("open_price") or t.get("openPrice")
    open_time = _normalize_time(t.get("open_time") or t.get("openTime"))
    close_time = _normalize_time(t.get("close_time") or t.get("closeTime"))
    c.execute(
        "INSERT INTO trades(ticket,symbol,strategy,side,lots,open_price,close_price,"
        "pnl,open_time,close_time,reason,raw,synced_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?) "
        "ON CONFLICT(ticket) DO UPDATE SET "
        "symbol=COALESCE(excluded.symbol, trades.symbol), "
        "strategy=COALESCE(NULLIF(NULLIF(excluded.strategy, ''), 'UNKNOWN'), trades.strategy), "
        "side=excluded.side, lots=excluded.lots, "
        "open_price=CASE WHEN COALESCE(excluded.open_price,0)>0 THEN excluded.open_price ELSE trades.open_price END, "
        "close_price=excluded.close_price, pnl=excluded.pnl, "
        "open_time=COALESCE(excluded.open_time, trades.open_time), "
        "close_time=COALESCE(excluded.close_time, trades.close_time), "
        "reason=excluded.reason, raw=excluded.raw, "
        "synced_at=excluded.synced_at",
        (
            int(ticket), symbol, t.get("strategy"), t.get("side") or t.get("type"),
            t.get("lots") or t.get("volume"), open_price,
            t.get("close_price") or t.get("closePrice"), t.get("pnl") or t.get("profit"),
            open_time, close_time,
            t.get("reason"), json.dumps(t), now(),
        ),
    )
    return True


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
            if isinstance(t, dict) and _upsert_trade(c, t):
                n += 1
    return {"ok": True, "stored": n}


@app.post("/api/ea/trade_reason")
async def ea_trade_reason(request: Request, x_nexus_token: Optional[str] = Header(None)):
    check_token(x_nexus_token)
    data = await request.json()
    symbol = data.get("symbol") or "?"
    with _conn() as c:
        # Se il simbolo non è nel payload (il push di chiusura live non lo manda),
        # ricavalo dall'ultimo stato EA con lo stesso magic.
        if symbol == "?" and data.get("magic") is not None:
            row = c.execute(
                "SELECT symbol FROM ea_status WHERE magic=? ORDER BY updated_at DESC LIMIT 1",
                (data.get("magic"),)).fetchone()
            if row and row["symbol"]:
                symbol = row["symbol"]
        c.execute(
            "INSERT INTO trade_reasons(symbol,payload,updated_at) VALUES(?,?,?) "
            "ON CONFLICT(symbol) DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at",
            (symbol, json.dumps(data), now()),
        )
        # FIX catena dati: popola anche la tabella `trades` (letta da Journal/
        # Analytics) così i trade chiusi live compaiono subito, senza attendere
        # il sync allo startup dell'EA.
        if data.get("ticket") is not None:
            try:
                _upsert_trade(c, data, symbol_fallback=(None if symbol == "?" else symbol))
            except Exception as e:
                print(f"[NEXUS] trade_reason->trades upsert failed: {e}")
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
               "partial_close", "reset_anti_revenge", "reset_daily", "resync_trades",
               "reset_protections"}
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
            "open_time,close_time,reason FROM trades ORDER BY "
            "COALESCE(NULLIF(REPLACE(REPLACE(close_time,'.','-'),' ','T'),''), "
            "NULLIF(REPLACE(REPLACE(open_time,'.','-'),' ','T'),''), '0000-00-00') DESC, "
            "synced_at DESC LIMIT ?",
            (limit,))]
        agg = c.execute(
            "SELECT COUNT(*) n, COALESCE(SUM(pnl),0) total, "
            "SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END) wins, "
            "SUM(CASE WHEN pnl<0 THEN 1 ELSE 0 END) losses FROM trades").fetchone()
    # Sana i timestamp legacy (formato punto MT5) ad ogni lettura, cosi' le
    # date compaiono corrette nel Journal anche senza aspettare un resync.
    for r in rows:
        r["open_time"] = _normalize_time(r["open_time"])
        r["close_time"] = _normalize_time(r["close_time"])
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
            "SELECT * FROM trades ORDER BY "
            "COALESCE(NULLIF(REPLACE(REPLACE(close_time,'.','-'),' ','T'),''), "
            "NULLIF(REPLACE(REPLACE(open_time,'.','-'),' ','T'),''), '0000-00-00') DESC, "
            "synced_at DESC LIMIT ?", (limit,))]
        meta = {m["ticket"]: dict(m) for m in c.execute("SELECT * FROM journal_meta")}
    out = []
    for r in rows:
        m = meta.get(r["ticket"], {})
        out.append({
            "ticket": r["ticket"], "symbol": r["symbol"], "strategy": r["strategy"],
            "side": r["side"], "lots": r["lots"], "openPrice": r["open_price"],
            "closePrice": r["close_price"], "pnl": r["pnl"],
            "openTime": _normalize_time(r["open_time"]),
            "closeTime": _normalize_time(r["close_time"]), "reason": r["reason"],
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


def _profit_factor(limit=200):
    """Profit factor sugli ultimi trade sincronizzati. None se non ci sono dati."""
    with _conn() as c:
        rows = [r["pnl"] for r in c.execute(
            "SELECT pnl FROM trades ORDER BY synced_at DESC LIMIT ?", (limit,))
            if r["pnl"] is not None]
    if not rows:
        return None, 0
    gain = sum(p for p in rows if p > 0)
    loss = abs(sum(p for p in rows if p < 0))
    if loss <= 0:
        return (None if gain <= 0 else 99.0), len(rows)
    return round(gain / loss, 2), len(rows)


def _compute_ea_health(primary):
    """Health composito dell'EA da bridge, protezioni, drawdown, attività,
    revenge, news, volatilità e profit factor. Ritorna score/level/checks/anomaly."""
    online = bool(primary.get("_online"))
    ago = primary.get("_updated_ago")
    dd = float(primary.get("drawdownPct") or 0)
    paused = bool(primary.get("eaPaused"))
    losses = int(primary.get("consecLosses") or 0)
    news = bool(primary.get("newsBlock"))
    vol = (primary.get("volRegime") or "").lower()
    esl = bool(primary.get("eslHit"))
    dpt = bool(primary.get("dptHit"))
    pun = bool(primary.get("pausedUntilNextOpen"))
    pf, pf_n = _profit_factor()

    checks = []
    anomaly = []

    def add(key, label, weight, ok, detail):
        checks.append({"key": key, "label": label, "weight": weight, "ok": ok, "detail": detail})

    # 1. Bridge — freschezza dati
    add("bridge", "Bridge / connessione", 20, (True if online else False),
        (f"aggiornato {ago}s fa" if online else "EA offline (nessun push <30s)"))
    if not online:
        anomaly.append({"code": "bridge_offline", "msg": "EA offline: nessun aggiornamento ricevuto negli ultimi 30s."})

    # 2. Drawdown giornaliero
    dd_ok = dd < 5.0
    add("drawdown", "Drawdown giornaliero", 15, (dd_ok if online else None),
        f"DD oggi {dd:.2f}%")
    if online and dd >= 5.0:
        anomaly.append({"code": "high_drawdown", "msg": f"Drawdown giornaliero elevato: {dd:.2f}%."})

    # 3. Protezioni di rischio
    prot_ok = not (esl or dpt or pun)
    prot_det = "nessuna protezione attiva" if prot_ok else ", ".join(
        [n for n, v in (("ESL", esl), ("DPT", dpt), ("pausa fino a open", pun)) if v])
    add("protections", "Protezioni di rischio", 15, (prot_ok if online else None), prot_det)
    if online and not prot_ok:
        anomaly.append({"code": "protection_hit", "msg": f"Protezione attiva: {prot_det}."})

    # 4. Attività (EA non in pausa)
    act_ok = not paused
    add("activity", "Attività EA", 10, (act_ok if online else None),
        ("operativo, " + str(primary.get("tradesToday") or 0) + " trade oggi") if act_ok else "EA in pausa")

    # 5. Revenge / loss streak
    rev_ok = losses < 3
    add("revenge", "Anti-revenge", 10, (rev_ok if online else None),
        f"{losses} perdite consecutive")
    if online and losses >= 4:
        anomaly.append({"code": "loss_streak", "msg": f"Serie di {losses} perdite consecutive."})

    # 6. News
    add("news", "Filtro news", 10, (True if online else None),
        "blocco news attivo" if news else "nessun evento bloccante")

    # 7. Volatilità
    vol_ok = vol not in ("extreme", "high")
    add("vol", "Regime volatilità", 10, (vol_ok if (online and vol) else None),
        f"regime {vol or 'n/d'}")

    # 8. Profit factor
    pf_ok = (pf is not None and pf >= 1.0)
    add("pf", "Profit factor", 10, (pf_ok if pf is not None else None),
        (f"PF {pf} su {pf_n} trade" if pf is not None else "dati insufficienti"))
    if pf is not None and pf < 0.8 and pf_n >= 10:
        anomaly.append({"code": "low_pf", "msg": f"Profit factor basso: {pf} su {pf_n} trade."})

    scored = [c for c in checks if c["ok"] is not None]
    wsum = sum(c["weight"] for c in scored) or 1
    wok = sum(c["weight"] for c in scored if c["ok"])
    score = round(wok / wsum * 100)
    if not online:
        score = min(score, 20)
    level = ("excellent" if score >= 85 else "good" if score >= 70
             else "warning" if score >= 50 else "critical")
    return score, level, checks, anomaly


@app.get("/api/ea/health")
def ea_health_dash(user: str = Depends(require_user)):
    primary, rows = _primary_ea()
    if not primary:
        return {"online": False, "ea_count": 0, "demo": True, "score": 0,
                "level": "critical", "checks": [], "anomaly": [
                    {"code": "no_ea", "msg": "Nessun EA collegato: avvia l'EA con WebSync attivo."}]}
    score, level, checks, anomaly = _compute_ea_health(primary)
    return {
        "online": bool(primary.get("_online")),
        "ea_count": len(rows),
        "last_update_sec": primary.get("_updated_ago"),
        "version": primary.get("version"),
        "symbol": primary.get("symbol"),
        "account": primary.get("magic"),
        "balance": primary.get("balance"),
        "equity": primary.get("equity"),
        "score": score,
        "level": level,
        "checks": checks,
        "anomaly": anomaly,
    }


@app.post("/api/ea/command")
async def ea_command_post(request: Request, user: str = Depends(require_user)):
    """Dashboard React accoda un comando per l'EA (POST, JWT)."""
    data = await request.json()
    action = data.get("action") or data.get("command")
    allowed = {"pause", "resume", "close_all", "close_position",
               "partial_close", "reset_anti_revenge", "reset_daily", "resync_trades",
               "reset_protections"}
    if action not in allowed:
        raise HTTPException(status_code=400, detail=f"action non valida (ammesse: {sorted(allowed)})")
    payload = {k: v for k, v in data.items() if k not in ("action", "command")}
    cmd_id = _enqueue_ea_command(action, payload)
    return {"ok": True, "id": cmd_id, "action": action}


# ======================= SETTINGS / STRATEGIES (JWT) ==================== #
@app.get("/api/settings")
def settings_get(user: str = Depends(require_user)):
    # Merge sui default: le installazioni esistenti hanno un blob parziale;
    # così ogni campo della pagina Settings mostra sempre un valore reale.
    return {**DEFAULT_SETTINGS, **(kv_get("settings", {}) or {})}


@app.put("/api/settings")
@app.post("/api/settings")
async def settings_save(request: Request, user: str = Depends(require_user)):
    data = await request.json()
    # I componenti della dashboard inviano patch parziali (es. solo "strategies"
    # dalla pagina Strategie, o solo i parametri di rischio): facciamo merge sul
    # blob esistente per non azzerare le altre impostazioni lette dall'EA.
    merged = dict(kv_get("settings", DEFAULT_SETTINGS) or {})
    if isinstance(data, dict):
        merged.update(data)
    else:
        merged = data
    kv_set("settings", merged)
    return {"ok": True, "settings": merged}


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


# ============== OTTIMIZZAZIONE LIVE PER-STRATEGIA (loop demo) ============ #
# Aggrega i risultati reali per nome strategia (l'EA li sincronizza via
# /api/ea/trade_history_sync) e calcola un moltiplicatore di rischio
# per-strategia: DD basso + redditizia -> lotto maggiore; in perdita -> ridotto.
DEFAULT_STRAT_RISK_CFG = {
    "enabled": False,       # auto-scaling OFF di default (sicurezza: agisce sul lotto reale)
    "min_trades": 15,       # trade minimi prima di scalare
    "target_dd_pct": 10.0,  # budget di drawdown per strategia
    "max_mult": 3.0,        # cap massimo moltiplicatore lotto
    "min_mult": 0.3,        # minimo per strategie deboli (riduce, non azzera)
    "min_pf": 1.1,          # profit factor minimo per scalare in su
}


def _strat_risk_cfg():
    cfg = dict(DEFAULT_STRAT_RISK_CFG)
    cfg.update(kv_get("strategy_risk_config", {}) or {})
    return cfg


def _account_balance():
    primary, _ = _primary_ea()
    try:
        b = float((primary or {}).get("balance") or 0)
    except Exception:
        b = 0
    return b if b > 0 else 10000.0


def _strategy_leaderboard():
    """Metriche realizzate per strategia + moltiplicatore di rischio effettivo."""
    cfg = _strat_risk_cfg()
    manual = kv_get("strategy_risk_manual", {}) or {}
    balance = _account_balance()
    with _conn() as c:
        rows = [dict(r) for r in c.execute(
            "SELECT strategy, pnl, close_time, open_time FROM trades "
            "WHERE strategy IS NOT NULL AND pnl IS NOT NULL "
            "ORDER BY COALESCE(close_time, open_time) ASC")]
    by = {}
    for r in rows:
        by.setdefault(r["strategy"], []).append(float(r["pnl"]))

    out = []
    for name, pnls in by.items():
        n = len(pnls)
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        gw, gl = sum(wins), abs(sum(losses))
        net = sum(pnls)
        pf = (round(gw / gl, 2) if gl > 0 else (99.0 if gw > 0 else 0.0))
        wr = round(len(wins) / n * 100, 1) if n else 0.0
        # drawdown realizzato sulla curva cumulata, in % del saldo conto
        cum, peak, maxdd = 0.0, 0.0, 0.0
        for p in pnls:
            cum += p
            peak = max(peak, cum)
            maxdd = max(maxdd, peak - cum)
        dd_pct = round(maxdd / balance * 100, 2) if balance > 0 else 0.0

        # moltiplicatore suggerito dall'auto-scaler
        if n < cfg["min_trades"]:
            suggested = 1.0
            reason = f"dati insufficienti ({n}/{cfg['min_trades']})"
        elif pf < 1.0 or net <= 0:
            suggested = round(cfg["min_mult"], 2)
            reason = "strategia in perdita: rischio ridotto"
        elif pf < cfg["min_pf"]:
            suggested = 1.0
            reason = f"PF {pf} sotto soglia: lotto invariato"
        else:
            raw = cfg["target_dd_pct"] / max(dd_pct, 0.5)
            suggested = round(min(cfg["max_mult"], max(1.0, raw)), 2)
            reason = f"DD {dd_pct}% basso: lotto verso target {cfg['target_dd_pct']}%"

        man = manual.get(name)
        if man is not None:
            try:
                effective = round(float(man), 2)
                source = "manuale"
            except Exception:
                effective, source = suggested, "auto"
        elif cfg["enabled"]:
            effective = suggested
            source = "auto"
        else:
            effective = 1.0
            source = "off"
        effective = max(0.0, min(cfg["max_mult"], effective))

        out.append({
            "name": name, "trades": n, "win_rate": wr, "profit_factor": pf,
            "net": round(net, 2), "max_dd_pct": dd_pct,
            "avg_trade": round(net / n, 2) if n else 0.0,
            "suggested_mult": suggested, "effective_mult": effective,
            "risk_source": source, "reason": reason,
        })
    out.sort(key=lambda r: (r["profit_factor"], r["net"]), reverse=True)
    return out, cfg, balance


def _strategy_risk_map():
    """Mappa NOME->moltiplicatore da inviare all'EA (solo valori != 1.0)."""
    board, cfg, _ = _strategy_leaderboard()
    return {r["name"]: r["effective_mult"] for r in board
            if abs(r["effective_mult"] - 1.0) > 1e-6}


@app.get("/api/strategies/leaderboard")
def strategies_leaderboard(user: str = Depends(require_user)):
    board, cfg, balance = _strategy_leaderboard()
    return {"strategies": board, "config": cfg, "balance": balance,
            "demo": len(board) == 0}


@app.get("/api/analytics/strategy_performance")
def analytics_strategy_performance(user: str = Depends(require_user)):
    """Diagnostica per-strategia dai TRADE REALI dell'EA (tabella trades),
    non da CSV di backtest. Usato da Strat Diag. Include split BUY/SELL,
    miglior/peggior trade, expectancy e verdetto."""
    with _conn() as c:
        rows = [dict(r) for r in c.execute(
            "SELECT strategy, side, pnl, close_time, open_time FROM trades "
            "WHERE strategy IS NOT NULL AND pnl IS NOT NULL")]
    by = {}
    for r in rows:
        by.setdefault(r["strategy"], []).append(r)
    out = []
    for name, trs in by.items():
        pnls = [float(t["pnl"]) for t in trs]
        n = len(pnls)
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        gw, gl = sum(wins), abs(sum(losses))
        net = sum(pnls)
        pf = round(gw / gl, 2) if gl > 0 else (99.0 if gw > 0 else 0.0)
        wr = round(len(wins) / n * 100, 1) if n else 0.0
        avg_win = round(gw / len(wins), 2) if wins else 0.0
        avg_loss = round(-gl / len(losses), 2) if losses else 0.0
        expectancy = round(net / n, 2) if n else 0.0
        buys = [t for t in trs if (t["side"] or "").upper() == "BUY"]
        sells = [t for t in trs if (t["side"] or "").upper() == "SELL"]
        # verdetto sintetico per la diagnostica
        if n < 5:
            verdict = "poco_dato"
        elif pf < 0.8:
            verdict = "critica"      # perde soldi
        elif pf < 1.1:
            verdict = "debole"       # marginale
        elif pf < 1.5:
            verdict = "ok"
        else:
            verdict = "forte"
        out.append({
            "name": name, "trades": n, "win_rate": wr, "profit_factor": pf,
            "net": round(net, 2), "avg_win": avg_win, "avg_loss": avg_loss,
            "expectancy": expectancy, "best": round(max(pnls), 2),
            "worst": round(min(pnls), 2),
            "buys": len(buys), "sells": len(sells),
            "buy_net": round(sum(float(t["pnl"]) for t in buys), 2),
            "sell_net": round(sum(float(t["pnl"]) for t in sells), 2),
            "verdict": verdict,
        })
    out.sort(key=lambda r: r["net"], reverse=True)
    total = round(sum(r["net"] for r in out), 2)
    return {"strategies": out, "total_net": total, "total_trades": len(rows),
            "demo": len(out) == 0}


@app.post("/api/strategies/risk_config")
async def strategies_risk_config(request: Request, user: str = Depends(require_user)):
    data = await request.json()
    cfg = _strat_risk_cfg()
    for k in ("enabled", "min_trades", "target_dd_pct", "max_mult", "min_mult", "min_pf"):
        if k in data:
            cfg[k] = data[k]
    # clamp di sicurezza
    cfg["max_mult"] = max(1.0, min(10.0, float(cfg["max_mult"])))
    cfg["min_mult"] = max(0.0, min(1.0, float(cfg["min_mult"])))
    cfg["min_trades"] = max(1, int(cfg["min_trades"]))
    kv_set("strategy_risk_config", cfg)
    return {"ok": True, "config": cfg}


@app.post("/api/strategies/risk_manual")
async def strategies_risk_manual(request: Request, user: str = Depends(require_user)):
    """Override manuale del moltiplicatore. Valore null per rimuovere l'override."""
    data = await request.json()
    manual = kv_get("strategy_risk_manual", {}) or {}
    overrides = data.get("overrides", data) if isinstance(data, dict) else {}
    for name, mult in (overrides or {}).items():
        if mult is None:
            manual.pop(name, None)
        else:
            manual[name] = max(0.0, min(10.0, float(mult)))
    kv_set("strategy_risk_manual", manual)
    return {"ok": True, "manual": manual}


@app.get("/api/strategies/{name}/overview")
def strategy_overview(name: str, user: str = Depends(require_user)):
    """Vista unica per strategia: stato live, metriche reali + rischio,
    miglior config da backtest, diagnostica e ultimi trade. Unisce in un
    solo endpoint i dati di Strategies, Optimizer, Backtest e Strat Diag."""
    # 1. stato abilitazione
    settings = kv_get("settings", DEFAULT_SETTINGS) or {}
    primary, _ = _primary_ea()
    enabled_map = (primary or {}).get("strategies", {}) or {}
    strat_map = settings.get("strategies") or {}
    override = kv_get("strategies_override", {}) or {}
    en = strat_map.get(name, override.get(name, enabled_map.get(name)))
    enabled = (bool(en) if en is not None else True)

    # 2. metriche live + rischio dal leaderboard
    board, cfg, _balance = _strategy_leaderboard()
    live = next((r for r in board if r["name"] == name), None)

    # 3. miglior config da backtest (per simbolo, ordinata per sharpe)
    lib = kv_get("backtest_library", []) or []
    bt_rows = sorted([r for r in lib if r.get("strategy") == name],
                     key=lambda r: (r.get("metrics", {}).get("sharpe") or -9), reverse=True)
    bt_by_symbol = {}
    for r in bt_rows:
        bt_by_symbol.setdefault(r.get("symbol"), r)

    # 4. diagnostica + 5. ultimi trade
    diag = None
    with _conn() as c:
        for r in c.execute("SELECT payload FROM strategy_stats"):
            for s in (json.loads(r["payload"]).get("strategies") or []):
                if s.get("name") == name:
                    diag = s
        trades = [dict(t) for t in c.execute(
            "SELECT ticket,symbol,side,lots,open_price,close_price,pnl,open_time,close_time,reason "
            "FROM trades WHERE strategy=? ORDER BY COALESCE(close_time,open_time) DESC LIMIT 20", (name,))]

    return {
        "name": name, "enabled": enabled,
        "live": live,
        "risk_mult": (live or {}).get("effective_mult", 1.0),
        "auto_scaling": bool(cfg.get("enabled")),
        "backtest_best": bt_rows[0] if bt_rows else None,
        "backtest_by_symbol": list(bt_by_symbol.values()),
        "diagnostics": diag,
        "recent_trades": trades,
    }


# ======================= ANALYTICS (JWT) =============================== #
@app.get("/api/analytics/trades")
def analytics_trades(limit: int = 500, user: str = Depends(require_user)):
    # Il frontend usa la risposta come array diretto (.slice/.filter).
    return _trades_with_meta(limit)


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
    counts = {}
    with _conn() as c:
        for r in c.execute("SELECT tags FROM journal_meta WHERE tags IS NOT NULL"):
            try:
                for t in json.loads(r["tags"]):
                    counts[t] = counts.get(t, 0) + 1
            except Exception:
                pass
    tags = [{"tag": t, "count": n} for t, n in sorted(counts.items())]
    # 'tags' = stats per il frontend; 'preset'/'used' restano per compat
    return {"tags": tags, "preset": PRESET_TAGS, "used": sorted(counts.keys())}


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
    for r in rows:
        r["id"] = r["key"]   # il frontend usa lic.id per PATCH/DELETE
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
    try:
        start_equity = float(body.get("start_equity", body.get("initial_balance", 10000.0)))
        raw = backtest.run_backtest(
            symbol=body.get("symbol", "XAUUSD"),
            timeframe=body.get("timeframe") or body.get("interval") or "D1",
            strategy=body.get("strategy") or (body.get("strategies") or [None])[0],
            strategies=body.get("strategies"),
            # Alias sui nomi campo usati dal form React (atr_sl_mult/interval/…)
            risk_pct=float(body.get("risk_pct", body.get("RiskPercent", 1.0))),
            atr_sl=float(body.get("atr_sl", body.get("atr_sl_mult", body.get("AtrSLMult", 1.5)))),
            atr_tp=float(body.get("atr_tp", body.get("atr_tp_mult", body.get("AtrTPMult", 3.0)))),
            start_equity=start_equity,
            # GATE ora applicati davvero dal motore -> il backtest e' la fonte di
            # verita', e l'EA verra' adattato al setup vincente qui trovato.
            htf_filter=bool(body.get("htf_bias", body.get("htf_filter", False))),
            breakeven_r=float(body.get("breakeven_R", body.get("breakeven_r", 0.0)) or 0.0),
            trailing_atr=float(body.get("trailing_atr_mult", body.get("trailing_atr", 0.0)) or 0.0),
            cooldown_bars=int(body.get("cooldown_bars", 0) or 0),
        )
        return _adapt_backtest_result(raw, start_equity)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"backtest error: {e}")


@app.post("/api/backtest/creator")
async def backtest_creator(request: Request, user: str = Depends(require_user)):
    """Strategy Creator v1: genera COMBINAZIONI di strategie x griglia di
    parametri, le testa sul motore e le classifica coi verdetti. Ritorna i
    migliori setup (con robustezza), pronti da salvare.

    Body: {symbol, timeframe, pool:[strat...], combo_sizes:[1,2],
           param_grid:{atr_sl:[...], atr_tp:[...]}, risk_pct, initial_balance,
           min_trades, max_combos}"""
    import itertools
    body = await request.json()
    symbol = body.get("symbol", "XAUUSD")
    timeframe = body.get("timeframe") or body.get("interval") or "D1"
    pool = [s for s in (body.get("pool") or []) if s]
    if not pool:
        raise HTTPException(status_code=400, detail="campo 'pool' (strategie) mancante")
    combo_sizes = body.get("combo_sizes") or [1, 2]
    grid = body.get("param_grid") or {}
    atr_sls = grid.get("atr_sl") or [float(body.get("atr_sl_mult", 1.8))]
    atr_tps = grid.get("atr_tp") or [float(body.get("atr_tp_mult", 2.8))]
    risk = float(body.get("risk_pct", 1.0))
    start_eq = float(body.get("initial_balance", 10000.0))
    try:
        min_trades = max(1, int(body.get("min_trades", 8)))
        max_combos = max(1, min(400, int(body.get("max_combos", 80))))
    except (ValueError, TypeError):
        min_trades, max_combos = 8, 80

    # genera le combinazioni di strategie
    combos = []
    for k in combo_sizes:
        try:
            k = int(k)
        except (ValueError, TypeError):
            continue
        if 1 <= k <= len(pool):
            combos.extend(itertools.combinations(pool, k))

    results, runs = [], 0
    for combo in combos:
        for sl in atr_sls:
            for tp in atr_tps:
                if runs >= max_combos:
                    break
                runs += 1
                try:
                    r = backtest.run_backtest(
                        symbol=symbol, timeframe=timeframe,
                        strategy=list(combo)[0], strategies=list(combo),
                        risk_pct=risk, atr_sl=float(sl), atr_tp=float(tp),
                        start_equity=start_eq)
                except Exception:
                    continue
                n = r.get("trades", 0)
                pf = r.get("profit_factor") or 0.0
                exp = r.get("expectancy_r", 0.0)
                dd = r.get("max_dd_pct", 0.0)
                net = r.get("net_pnl", 0.0)
                row = {"executed": n, "profit_factor": pf,
                       "expectancy_R": exp, "winrate_pct": r.get("win_rate", 0),
                       "setup": n, "name": "+".join(combo)}
                v, why = bt_verdict._verdict(row, min_trades)
                # robustezza: expectancy x sqrt(trade) penalizzato dal drawdown
                robust = round(exp * (n ** 0.5) / (1.0 + max(0.0, dd) / 10.0), 3)
                results.append({
                    "combo": list(combo), "name": "+".join(combo),
                    "atr_sl": float(sl), "atr_tp": float(tp),
                    "trades": n, "net": round(net, 2), "pf": round(pf, 2),
                    "exp": round(exp, 3), "dd": round(dd, 2),
                    "wr": r.get("win_rate", 0), "verdict": v, "why": why,
                    "robust": robust,
                })

    # ordina: prima i verdetti migliori, poi robustezza
    rank = {"FORTE": 0, "OK": 1, "DEBOLE": 2, "CRITICA": 3, "POCHI_DATI": 4, "NO_SETUP": 5}
    results.sort(key=lambda x: (rank.get(x["verdict"], 9), -x["robust"]))
    top = results[:40]
    kv_set("creator_last", {"symbol": symbol, "timeframe": timeframe,
                            "ran": runs, "results": top, "at": iso()})
    return {"symbol": symbol, "timeframe": timeframe, "combos_tested": runs,
            "results": top}


@app.post("/api/backtest/optimize_per_strategy")
async def backtest_optimize_per_strategy(request: Request, user: str = Depends(require_user)):
    """Per OGNI strategia del pool trova i SUOI parametri migliori (sweep della
    griglia ATR SL/TP), non parametri globali. Ritorna la tabella
    strategia -> parametri ottimali + metriche + verdetto, da salvare/esportare
    e usare per rendere l'EA coerente col backtest.

    Body: {symbol, timeframe, pool:[...], param_grid:{atr_sl:[...],atr_tp:[...]},
           risk_pct, initial_balance, min_trades}"""
    body = await request.json()
    symbol = body.get("symbol", "XAUUSD")
    timeframe = body.get("timeframe") or body.get("interval") or "D1"
    pool = [s for s in (body.get("pool") or []) if s]
    if not pool:
        raise HTTPException(status_code=400, detail="campo 'pool' (strategie) mancante")
    grid = body.get("param_grid") or {}
    atr_sls = grid.get("atr_sl") or [1.2, 1.5, 1.8, 2.2, 2.6]
    atr_tps = grid.get("atr_tp") or [2.0, 2.8, 3.5, 4.5]
    risk = float(body.get("risk_pct", 1.0))
    start_eq = float(body.get("initial_balance", 10000.0))
    try:
        min_trades = max(1, int(body.get("min_trades", 8)))
    except (ValueError, TypeError):
        min_trades = 8

    # GATE testati PER STRATEGIA (mai globali): ognuno tiene solo quelli che lo
    # migliorano. Griglie modeste per non esplodere il numero di run.
    htf_opts   = grid.get("htf_filter", [False, True])
    be_opts    = grid.get("breakeven_r", [0.0, 1.0])
    trail_opts = grid.get("trailing_atr", [0.0, 2.0])
    rank = {"FORTE": 0, "OK": 1, "DEBOLE": 2, "CRITICA": 3, "POCHI_DATI": 4, "NO_SETUP": 5}

    def _eval(strat, sl, tp, htf, be, tr):
        try:
            r = backtest.run_backtest(
                symbol=symbol, timeframe=timeframe, strategy=strat, strategies=[strat],
                risk_pct=risk, atr_sl=float(sl), atr_tp=float(tp), start_equity=start_eq,
                htf_filter=bool(htf), breakeven_r=float(be), trailing_atr=float(tr))
        except Exception:
            return None
        n = r.get("trades", 0); pf = r.get("profit_factor") or 0.0
        exp = r.get("expectancy_r", 0.0); dd = r.get("max_dd_pct", 0.0)
        v, why = bt_verdict._verdict(
            {"executed": n, "profit_factor": pf, "expectancy_R": exp,
             "winrate_pct": r.get("win_rate", 0), "setup": n}, min_trades)
        robust = round(exp * (n ** 0.5) / (1.0 + max(0.0, dd) / 10.0), 3)
        return {"strategy": strat, "atr_sl": float(sl), "atr_tp": float(tp),
                "htf_filter": bool(htf), "breakeven_r": float(be), "trailing_atr": float(tr),
                "trades": n, "pf": round(pf, 2), "net": round(r.get("net_pnl", 0.0), 2),
                "exp": round(exp, 3), "dd": round(dd, 2), "wr": r.get("win_rate", 0),
                "verdict": v, "why": why, "robust": robust}

    def _key(c):
        return (rank.get(c["verdict"], 9), -c["robust"])

    table = []
    combos_per_strat = (len(atr_sls) * len(atr_tps) * len(htf_opts)
                        + max(0, len(be_opts) * len(trail_opts) - 1))
    for strat in pool:
        # Stadio 1: parametri + HTF (gate d'uscita spenti)
        best = None
        for sl in atr_sls:
            for tp in atr_tps:
                for htf in htf_opts:
                    c = _eval(strat, sl, tp, htf, 0.0, 0.0)
                    if c and (best is None or _key(c) < _key(best)):
                        best = c
        if not best:
            continue
        # Stadio 2: gate d'uscita (breakeven/trailing) SUI parametri migliori
        for be in be_opts:
            for tr in trail_opts:
                if be == 0.0 and tr == 0.0:
                    continue   # gia' valutato nello stadio 1
                c = _eval(strat, best["atr_sl"], best["atr_tp"], best["htf_filter"], be, tr)
                if c and _key(c) < _key(best):
                    best = c
        table.append(best)

    table.sort(key=lambda x: (rank.get(x["verdict"], 9), -x["robust"]))
    kv_set("creator_per_strategy_last",
           {"symbol": symbol, "timeframe": timeframe, "table": table, "at": iso()})
    return {"symbol": symbol, "timeframe": timeframe,
            "grid": {"atr_sl": atr_sls, "atr_tp": atr_tps, "htf_filter": htf_opts,
                     "breakeven_r": be_opts, "trailing_atr": trail_opts},
            "combos_per_strategy": combos_per_strat, "table": table}


@app.post("/api/backtest/optimize_multi_tf")
async def backtest_optimize_multi_tf(request: Request, user: str = Depends(require_user)):
    """Per OGNI strategia trova il TIMEFRAME migliore + parametri + gate + RISCHIO.
    Alcune strategie rendono in daily, altre H4/H1: qui le proviamo su tutti i TF
    e teniamo il TF vincente per ciascuna. Il rischio per-strategia e' dimensionato
    a un budget di drawdown (target_dd), dando piu' size alle piu' robuste.

    Body: {symbol, pool:[...], timeframes:[...], param_grid:{atr_sl,atr_tp,...},
           initial_balance, min_trades, target_dd, max_risk, min_risk}"""
    body = await request.json()
    symbol = body.get("symbol", "XAUUSD")
    pool = [s for s in (body.get("pool") or []) if s]
    if not pool:
        raise HTTPException(status_code=400, detail="campo 'pool' (strategie) mancante")
    tf_list = body.get("timeframes") or ["1d", "4h", "1h"]
    grid = body.get("param_grid") or {}
    atr_sls = grid.get("atr_sl") or [1.0, 1.5, 2.0]
    atr_tps = grid.get("atr_tp") or [2.0, 3.0, 4.5]
    htf_opts   = grid.get("htf_filter", [False, True])
    be_opts    = grid.get("breakeven_r", [0.0, 1.0])
    trail_opts = grid.get("trailing_atr", [0.0, 2.0])
    start_eq = float(body.get("initial_balance", 10000.0))
    target_dd = float(body.get("target_dd", 10.0))   # budget DD% per strategia
    max_risk = float(body.get("max_risk", 2.0))
    min_risk = float(body.get("min_risk", 0.25))
    try:
        min_trades = max(1, int(body.get("min_trades", 8)))
    except (ValueError, TypeError):
        min_trades = 8
    rank = {"FORTE": 0, "OK": 1, "DEBOLE": 2, "CRITICA": 3, "POCHI_DATI": 4, "NO_SETUP": 5}

    def _eval(strat, tf, sl, tp, htf, be, tr):
        try:
            r = backtest.run_backtest(
                symbol=symbol, timeframe=tf, strategy=strat, strategies=[strat],
                risk_pct=1.0, atr_sl=float(sl), atr_tp=float(tp), start_equity=start_eq,
                htf_filter=bool(htf), breakeven_r=float(be), trailing_atr=float(tr))
        except Exception:
            return None
        n = r.get("trades", 0); pf = r.get("profit_factor") or 0.0
        exp = r.get("expectancy_r", 0.0); dd = r.get("max_dd_pct", 0.0)
        v, why = bt_verdict._verdict(
            {"executed": n, "profit_factor": pf, "expectancy_R": exp,
             "winrate_pct": r.get("win_rate", 0), "setup": n}, min_trades)
        robust = round(exp * (n ** 0.5) / (1.0 + max(0.0, dd) / 10.0), 3)
        return {"strategy": strat, "tf": tf, "atr_sl": float(sl), "atr_tp": float(tp),
                "htf_filter": bool(htf), "breakeven_r": float(be), "trailing_atr": float(tr),
                "trades": n, "pf": round(pf, 2), "net": round(r.get("net_pnl", 0.0), 2),
                "exp": round(exp, 3), "dd": round(dd, 2), "wr": r.get("win_rate", 0),
                "verdict": v, "why": why, "robust": robust}

    def _key(c):
        return (rank.get(c["verdict"], 9), -c["robust"])

    def _best_for_tf(strat, tf):
        best = None
        for sl in atr_sls:
            for tp in atr_tps:
                for htf in htf_opts:
                    c = _eval(strat, tf, sl, tp, htf, 0.0, 0.0)
                    if c and (best is None or _key(c) < _key(best)):
                        best = c
        if not best:
            return None
        for be in be_opts:
            for tr in trail_opts:
                if be == 0.0 and tr == 0.0:
                    continue
                c = _eval(strat, tf, best["atr_sl"], best["atr_tp"], best["htf_filter"], be, tr)
                if c and _key(c) < _key(best):
                    best = c
        return best

    table = []
    for strat in pool:
        best = None
        for tf in tf_list:
            c = _best_for_tf(strat, tf)
            if c and (best is None or _key(c) < _key(best)):
                best = c
        if not best:
            continue
        # rischio per-strategia: scala a budget DD (dd% scala ~lineare col rischio).
        dd = max(0.5, best["dd"])
        sug = target_dd / dd
        if rank.get(best["verdict"], 9) >= 2:   # DEBOLE o peggio -> prudenza
            sug *= 0.5
        best["risk_pct"] = round(min(max_risk, max(min_risk, sug)), 2)
        table.append(best)

    table.sort(key=lambda x: (rank.get(x["verdict"], 9), -x["robust"]))
    payload = {"symbol": symbol, "timeframes": tf_list, "target_dd": target_dd,
               "table": table, "at": iso()}
    kv_set("creator_multi_tf_last", payload)
    return payload


@app.post("/api/backtest/creator/save")
async def backtest_creator_save(request: Request, user: str = Depends(require_user)):
    """Salva un setup creato (combo+parametri) nella lista dei setup del Creator."""
    body = await request.json()
    setup = body.get("setup") or {}
    if not setup.get("combo"):
        raise HTTPException(status_code=400, detail="setup.combo mancante")
    saved = kv_get("creator_setups", [])
    setup["saved_at"] = iso()
    saved.insert(0, setup)
    kv_set("creator_setups", saved[:50])
    return {"ok": True, "count": len(saved[:50])}


@app.get("/api/backtest/creator/saved")
def backtest_creator_saved(user: str = Depends(require_user)):
    return {"setups": kv_get("creator_setups", [])}


def _adapt_backtest_result(raw, start_equity):
    """Adatta il risultato piatto del motore allo shape atteso dal frontend
    (metrics annidate con suffissi _pct, trades list, by_strategy, first/last ts)."""
    trade_list = raw.get("trade_list") or []
    # aggregazione P&L per strategia
    agg = {}
    for t in trade_list:
        s = t.get("strategy") or "?"
        agg[s] = agg.get(s, 0.0) + (t.get("pnl") or 0.0)
    by_strategy = sorted(
        [{"strategy": s, "pnl": round(p, 2)} for s, p in agg.items()],
        key=lambda r: r["pnl"], reverse=True)
    final_eq = raw.get("final_equity", start_equity)
    ret = raw.get("return_pct", 0.0)
    curve = raw.get("equity_curve") or []
    first_ts = curve[0]["ts"] if curve else None
    last_ts = curve[-1]["ts"] if curve else None
    buy_hold = None
    if curve and curve[0].get("close") and curve[-1].get("close"):
        buy_hold = round((curve[-1]["close"] / curve[0]["close"] - 1) * 100, 2)
    # Sortino sui P&L per trade (downside deviation), coerente con lo Sharpe del motore.
    sortino = raw.get("sortino")
    pnls = [t.get("pnl") or 0.0 for t in trade_list]
    if sortino is None and len(pnls) > 1:
        mean = sum(pnls) / len(pnls)
        downside = [p for p in pnls if p < 0]
        dd = (sum(p * p for p in downside) / len(pnls)) ** 0.5 if downside else 0.0
        sortino = round(mean / dd, 2) if dd > 0 else None
    return {
        "demo": raw.get("demo", False),
        "data_source": raw.get("data_source"),
        "symbol": raw.get("symbol"),
        "timeframe": raw.get("timeframe"),
        "strategies": raw.get("strategies"),
        "trades_count": raw.get("trades"),
        "bars": raw.get("bars"),
        "first_ts": first_ts,
        "last_ts": last_ts,
        "equity_curve": curve,
        "trades": trade_list,
        "by_strategy": by_strategy,
        "metrics": {
            "win_rate_pct": raw.get("win_rate"),
            "profit_factor": raw.get("profit_factor"),
            "total_return_pct": ret,
            "max_dd_pct": raw.get("max_dd_pct"),
            "sharpe": raw.get("sharpe"),
            "sortino": sortino,
            "wins": raw.get("wins"),
            "losses": raw.get("losses"),
            "n_trades": raw.get("trades"),
            "initial_balance": round(start_equity, 2),
            "final_balance": round(final_eq, 2),
            "net_pnl": raw.get("net_pnl"),
            "avg_win": raw.get("avg_win"),
            "avg_loss": raw.get("avg_loss"),
            "expectancy_r": raw.get("expectancy_r"),
            "buy_hold_return_pct": buy_hold,
        },
    }


@app.post("/api/backtest/optimize")
async def backtest_optimize(request: Request, user: str = Depends(require_user)):
    body = await request.json()
    res = backtest.optimize(symbol=body.get("symbol", "XAUUSD"),
                            strategy=body.get("strategy", "ADX_RSI"))
    res["job_id"] = secrets.token_hex(6)
    kv_set("backtest_last_optimize", res)
    return res


@app.post("/api/backtest/management_report")
@app.get("/api/backtest/management_report")
async def backtest_mgmt(request: Request, user: str = Depends(require_user)):
    body = {}
    if request.method == "POST":
        try:
            body = await request.json()
        except Exception:
            body = {}
    return backtest.management_report(symbol=body.get("symbol", "XAUUSD"),
                                      strategy=body.get("strategy", "ADX_RSI"))


@app.post("/api/backtest/multi_tf_report")
@app.get("/api/backtest/multi_tf_report")
async def backtest_mtf(request: Request, user: str = Depends(require_user)):
    body = {}
    if request.method == "POST":
        try:
            body = await request.json()
        except Exception:
            body = {}
    return backtest.multi_tf_report(symbol=body.get("symbol", "XAUUSD"),
                                    strategy=body.get("strategy", "ADX_RSI"))


@app.get("/api/backtest/locked_profile/all")
def backtest_locked_all(user: str = Depends(require_user)):
    profiles = kv_get("locked_profiles", {})
    # il frontend si aspetta una lista `profiles` con il campo symbol
    as_list = [{**v, "symbol": sym} for sym, v in profiles.items()]
    return {"profiles": as_list, "locked_profiles": profiles, "demo": not bool(profiles)}


# ======================= CALENDAR (JWT, demo) ========================== #
@app.get("/api/calendar")
def calendar(user: str = Depends(require_user)):
    # Campi attesi dal frontend: ts, country, impact, title, note.
    base = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    raw = [
        (2, "US", "high", "Core CPI m/m"),
        (5, "EU", "medium", "ECB President Speech"),
        (26, "US", "high", "Non-Farm Payrolls"),
        (30, "UK", "medium", "BoE Rate Decision"),
        (50, "US", "high", "FOMC Statement"),
    ]
    events = [{"ts": (base + timedelta(hours=h)).isoformat(), "country": ctry,
               "impact": imp, "title": title, "note": ""}
              for (h, ctry, imp, title) in raw]
    return {"events": events, "demo": True,
            "note": "Calendario dimostrativo — collegare un feed news reale in seguito."}


# ======================= DOWNLOADS ===================================== #
DOWNLOADS_DIR = STATIC_DIR / "downloads"
_DOWNLOAD_LABELS = {
    ".set": "Preset EA (.set)",
    ".tpl": "Template grafico (.tpl)",
    ".ex5": "Indicatore compilato (.ex5)",
    ".mq5": "Sorgente MQL5 (.mq5)",
    ".zip": "Pacchetto (.zip)",
}


@app.get("/api/downloads/list")
def downloads_list(user: str = Depends(require_user)):
    """Elenco file scaricabili da server/static/downloads (preset, template…)."""
    items = []
    if DOWNLOADS_DIR.exists():
        for f in sorted(DOWNLOADS_DIR.iterdir()):
            if f.is_file():
                items.append({
                    "name": f.name,
                    "size": f.stat().st_size,
                    "kind": _DOWNLOAD_LABELS.get(f.suffix.lower(), f.suffix),
                    "url": f"/downloads/{f.name}",
                })
    return {"files": items, "count": len(items)}


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
                 "reset_anti_revenge, reset_daily, reset_protections), indicala chiaramente "
                 "così l'utente può confermarla. reset_protections sblocca una pausa ESL/DPT/"
                 "AutoClose bloccata (usalo solo se l'utente conferma che il rischio è sotto controllo).")
    return "\n".join(lines)


def _coach_sess_key(sid):
    return f"coach_sess:{sid or 'default'}"


@app.post("/api/coach/chat")
async def coach_chat(request: Request, user: str = Depends(require_user)):
    """Contratto frontend: {session_id, message, chart_context?}.
    Lo storico della sessione è mantenuto lato server (kv)."""
    body = await request.json()
    sid = body.get("session_id") or "default"
    context = body.get("context") or {}
    if body.get("chart_context"):
        context = {**context, "chart": body["chart_context"]}

    # storico per sessione
    skey = _coach_sess_key(sid)
    history = kv_get(skey, [])

    # messaggio nuovo: 'message' singolare (frontend) o 'messages' array (compat)
    new_user = (body.get("message") or "").strip()
    if not new_user and body.get("messages"):
        for m in body["messages"]:
            if m.get("role") != "assistant" and m.get("content"):
                new_user = str(m["content"]).strip()
    if not new_user:
        raise HTTPException(status_code=400, detail="message vuoto")

    # costruisci la conversazione per Anthropic
    convo = [{"role": ("assistant" if m.get("role") == "assistant" else "user"),
              "content": str(m.get("content", ""))} for m in history if m.get("content")]
    convo.append({"role": "user", "content": new_user})

    primary, _ = _primary_ea()
    with _conn() as c:
        memory = [r["text"] for r in c.execute(
            "SELECT text FROM coach_memory ORDER BY created_at DESC LIMIT 20")]
    system = _coach_system(primary, context, memory)
    text, err = _anthropic_chat(system, convo)
    if err:
        return {"reply": f"⚠️ Coach non disponibile: {err}", "demo": True, "error": err}

    # persisti storico (cap a 40 messaggi)
    history.append({"role": "user", "content": new_user, "ts": iso()})
    history.append({"role": "assistant", "content": text, "ts": iso()})
    kv_set(skey, history[-40:])
    return {"reply": text, "demo": False, "model": COACH_MODEL, "session_id": sid}


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
    # Il Coach invia {type, name, pct, duration_min, ...}; retro-compat con {action}.
    atype = body.get("type") or body.get("action")
    name = body.get("name")
    cmd_id = None

    # 1. Comandi runtime EA
    cmd_map = {
        "pause_ea": "pause", "pause": "pause",
        "resume_ea": "resume", "resume": "resume",
        "close_all": "close_all",
        "reset_anti_revenge": "reset_anti_revenge",
        "reset_daily": "reset_daily",
        "reset_protections": "reset_protections",
    }
    if atype in cmd_map:
        payload = {}
        if body.get("duration_min"):
            payload["duration_min"] = body["duration_min"]
        cmd_id = _enqueue_ea_command(cmd_map[atype], payload or None)
        note = f"Comando EA dal Coach: {cmd_map[atype]}"

    # 2. Abilita/disabilita strategia (live, via /api/ea/settings)
    elif atype in ("disable_strategy", "enable_strategy"):
        if not name:
            raise HTTPException(status_code=400, detail="nome strategia mancante")
        enable = (atype == "enable_strategy")
        settings = dict(kv_get("settings", DEFAULT_SETTINGS) or {})
        strat = dict(settings.get("strategies") or {})
        strat[name] = enable
        settings["strategies"] = strat
        kv_set("settings", settings)
        ov = kv_get("strategies_override", {}) or {}
        ov[name] = enable
        kv_set("strategies_override", ov)
        note = f"{'Riattivata' if enable else 'Disattivata'} strategia {name} dal Coach"

    # 3. Imposta rischio globale (RiskPercent, live)
    elif atype == "set_risk":
        pct = body.get("pct")
        if pct is None:
            raise HTTPException(status_code=400, detail="pct mancante")
        settings = dict(kv_get("settings", DEFAULT_SETTINGS) or {})
        settings["RiskPercent"] = max(0.0, min(10.0, float(pct)))
        kv_set("settings", settings)
        note = f"Risk impostato a {settings['RiskPercent']}% dal Coach"

    # 4. Imposta moltiplicatore rischio per-strategia (live)
    elif atype == "set_strategy_risk":
        if not name or body.get("mult") is None:
            raise HTTPException(status_code=400, detail="name/mult mancante")
        manual = kv_get("strategy_risk_manual", {}) or {}
        manual[name] = max(0.0, min(10.0, float(body["mult"])))
        kv_set("strategy_risk_manual", manual)
        note = f"Rischio {name} → x{manual[name]} dal Coach"

    else:
        raise HTTPException(status_code=400, detail=f"azione non applicabile: {atype}")

    with _conn() as c:
        c.execute("INSERT INTO coach_notifications(text,read,created_at) VALUES(?,0,?)",
                  (note, now()))
    return {"ok": True, "id": cmd_id, "action": atype, "note": note}


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


# ============ EXTRA ENDPOINTS richiesti dal frontend React =============== #
COMMON_SYMBOLS = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD",
                  "USDCAD", "NZDUSD", "US30", "NAS100", "SPX500", "GER40",
                  "BTCUSD", "ETHUSD"]
STRAT_META = {
    "ADX_RSI": "Trend+momentum (ADX/RSI)", "AMD_CONT": "AMD continuation",
    "AMD_REVERSAL": "AMD reversal (manipulation)", "BB_SQUEEZE": "Bollinger squeeze breakout",
    "BJORGUM": "Bjorgum key zones", "BOLLINGER": "Mean reversion bande",
    "BREAKOUT_ACC": "Breakout acceleration", "CISD": "Change in state of delivery (ICT)",
    "DISP_REBAL": "Displacement + rebalance", "EMA_PULLBACK": "EMA pullback",
    "FVG_CONT": "Fair Value Gap continuation", "FVG_MIT": "FVG mitigation",
    "ICHIMOKU": "Ichimoku Kumo break", "IFVG": "Inverted FVG",
    "JUDAS_SWING": "Judas swing (ICT false move)", "LDN_REVERSAL": "London reversal",
    "LIQ_SWEEP": "Liquidity sweep", "LIQ_VOID": "Liquidity void",
    "LONDON_BO": "London breakout", "MACD": "Momentum MACD",
    "MALAYSIAN_SNR": "Malaysian Support/Resistance", "NY_REVERSAL": "New York reversal",
    "OB_MIT": "Order block mitigation", "ORDER_BLOCK": "Order block",
    "OTE_CONT": "Optimal Trade Entry continuation", "PO3": "Power of Three (AMD)",
    "RANGE_FADE": "Range fade (mean reversion)", "RSI_DIV": "RSI divergence",
    "SAR": "Parabolic SAR trend", "SH_BMS_RTO": "Stop hunt + BMS + RTO",
    "SILVER_BULLET": "Silver Bullet (ICT killzone)", "SMS_BMS_RTO": "SMS + BMS + RTO",
    "STRUCT_REACT": "Structure reaction", "TSI": "True Strength Index",
    "TURTLE_SOUP": "Turtle soup (false breakout)", "WEEKLY_EXP": "Weekly expansion",
}


# ---- EA history (serie equity per il grafico live) ----
@app.get("/api/ea/history")
def ea_history(limit: int = 120, user: str = Depends(require_user)):
    # Array diretto di punti {ts, equity, balance, floatPnL} (lo usa HomePage).
    return kv_get("equity_history", [])[-limit:]


# ---- generic command (React POSTs /command) ----
@app.post("/api/command")
async def command_post(request: Request, user: str = Depends(require_user)):
    data = await request.json()
    action = data.get("action") or data.get("command")
    allowed = {"pause", "resume", "close_all", "close_position",
               "partial_close", "reset_anti_revenge", "reset_daily", "resync_trades",
               "reset_protections"}
    if action not in allowed:
        raise HTTPException(status_code=400, detail=f"action non valida: {action}")
    payload = {k: v for k, v in data.items() if k not in ("action", "command")}
    return {"ok": True, "id": _enqueue_ea_command(action, payload), "action": action}


# ---- settings history (array diretto: SettingsPage usa .flatMap/.length) ----
@app.get("/api/settings/history")
def settings_history(limit: int = 50, user: str = Depends(require_user)):
    return kv_get("settings_history", [])[-limit:]


# ---- analytics extra ----
@app.get("/api/analytics/calendar")
def analytics_calendar(days: int = 365, user: str = Depends(require_user)):
    trades = _trades_with_meta(100000)
    by_day = {}
    for t in trades:
        d = (t.get("closeTime") or "")[:10]
        if not d:
            continue
        g = by_day.setdefault(d, {"date": d, "pnl": 0.0, "trades": 0})
        g["pnl"] += (t["pnl"] or 0)
        g["trades"] += 1
    for g in by_day.values():
        g["pnl"] = round(g["pnl"], 2)
    return {"days": sorted(by_day.values(), key=lambda x: x["date"]), "demo": len(trades) == 0}


@app.get("/api/analytics/correlation")
def analytics_correlation(user: str = Depends(require_user)):
    return {"matrix": [], "symbols": [], "demo": True,
            "note": "Correlazione non ancora calcolata."}


@app.get("/api/analytics/heatmap")
def analytics_heatmap(user: str = Depends(require_user)):
    trades = _trades_with_meta(100000)
    cells = {}
    for t in trades:
        ct = t.get("closeTime") or ""
        hour = ct[11:13] if len(ct) >= 13 else "?"
        c = cells.setdefault(hour, {"hour": hour, "pnl": 0.0, "trades": 0})
        c["pnl"] += (t["pnl"] or 0)
        c["trades"] += 1
    for c in cells.values():
        c["pnl"] = round(c["pnl"], 2)
    return {"by_hour": sorted(cells.values(), key=lambda x: x["hour"]), "demo": len(trades) == 0}


@app.get("/api/analytics/shadow")
def analytics_shadow(limit: int = 200, user: str = Depends(require_user)):
    with _conn() as c:
        rows = [json.loads(r["payload"]) for r in c.execute(
            "SELECT payload FROM shadow_trades ORDER BY created_at DESC LIMIT ?", (limit,))]
    return {"shadow_trades": rows, "demo": len(rows) == 0}


@app.get("/api/analytics/strategy_meta")
def analytics_strategy_meta(user: str = Depends(require_user)):
    return {"strategies": [{"name": n, "description": STRAT_META.get(n, "")} for n in STRAT_LIST]}


def _all_strategy_stats():
    with _conn() as c:
        return [{"symbol": r["symbol"], "updated_at": r["updated_at"], "data": json.loads(r["payload"])}
                for r in c.execute("SELECT * FROM strategy_stats")]


@app.get("/api/analytics/strategy_stats/latest")
def strat_stats_latest(symbol: str = "", user: str = Depends(require_user)):
    stats = _all_strategy_stats()
    if symbol:
        stats = [s for s in stats if s["symbol"] == symbol]
    latest = max(stats, key=lambda s: s["updated_at"]) if stats else None
    return {"latest": latest, "demo": latest is None}


@app.get("/api/analytics/strategy_stats/symbols")
def strat_stats_symbols(user: str = Depends(require_user)):
    return {"symbols": [s["symbol"] for s in _all_strategy_stats()]}


@app.get("/api/analytics/strategy_stats/markdown")
def strat_stats_markdown(symbol: str = "", user: str = Depends(require_user)):
    stats = _all_strategy_stats()
    if symbol:
        stats = [s for s in stats if s["symbol"] == symbol]
    lines = ["# Strategy stats", ""]
    for blk in stats:
        lines.append(f"## {blk['symbol']}")
        lines.append("| strategia | called | exec | win | loss | health |")
        lines.append("|---|---|---|---|---|---|")
        for r in (blk["data"].get("strategies") or []):
            lines.append(f"| {r.get('name')} | {r.get('called',0)} | {r.get('executed',0)} | "
                         f"{r.get('wins',0)} | {r.get('losses',0)} | {r.get('health','')} |")
        lines.append("")
    return {"markdown": "\n".join(lines), "demo": not stats}


@app.post("/api/analytics/strategy_stats/upload")
async def strat_stats_upload(request: Request, user: str = Depends(require_user)):
    data = await request.json()
    symbol = data.get("symbol", "manual")
    with _conn() as c:
        c.execute("INSERT INTO strategy_stats(symbol,payload,updated_at) VALUES(?,?,?) "
                  "ON CONFLICT(symbol) DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at",
                  (symbol, json.dumps(data), now()))
    return {"ok": True, "symbol": symbol}


# ---- license summary ----
@app.get("/api/license/summary")
def license_summary(user: str = Depends(require_user)):
    with _conn() as c:
        total = c.execute("SELECT COUNT(*) n FROM licenses").fetchone()["n"]
        trial = c.execute("SELECT COUNT(*) n FROM licenses WHERE trial=1").fetchone()["n"]
    return {"total": total, "trial": trial, "active": total - trial, "mode": LICENSE_MODE}


# ---- calendar upcoming (alias del calendario) ----
@app.get("/api/calendar/upcoming")
def calendar_upcoming(user: str = Depends(require_user)):
    return calendar(user)


# ---- chart OHLC + markers (demo sintetico) ----
@app.get("/api/chart/ohlc")
def chart_ohlc(symbol: str = "XAUUSD", tf: str = "M15", limit: int = 300,
               user: str = Depends(require_user)):
    import math
    base = 2350.0 if symbol.startswith("XAU") else 1.10
    step = base * 0.001
    candles, price = [], base
    t0 = int(now()) - limit * 900
    for i in range(limit):
        drift = math.sin(i / 9.0) * step * 3 + ((i * 53) % 7 - 3) * step
        o = price
        c = price + drift
        h = max(o, c) + abs(drift) * 0.5
        low = min(o, c) - abs(drift) * 0.5
        candles.append({"time": t0 + i * 900, "open": round(o, 3), "high": round(h, 3),
                        "low": round(low, 3), "close": round(c, 3)})
        price = c
    return {"symbol": symbol, "tf": tf, "candles": candles, "demo": True}


@app.get("/api/chart/markers")
def chart_markers(symbol: str = "XAUUSD", user: str = Depends(require_user)):
    trades = [t for t in _trades_with_meta(200) if t.get("symbol") == symbol]
    markers = [{"time": t.get("closeTime"), "price": t.get("closePrice"),
                "side": t.get("side"), "pnl": t.get("pnl"), "ticket": t.get("ticket")}
               for t in trades if t.get("closePrice")]
    return {"markers": markers, "demo": len(markers) == 0}


# ---- backtest extra ----
@app.get("/api/backtest/presets")
def backtest_presets(user: str = Depends(require_user)):
    return {"presets": ["Conservative", "Balanced", "Aggressive", "Discovery"]}


@app.get("/api/backtest/strategies")
def backtest_strategies(user: str = Depends(require_user)):
    # 'all' = strategie che il motore Python sa DAVVERO testare (dict STRATEGIES);
    # il frontend (Creator/Run) usa questa chiave per popolare il pool.
    engine = sorted(backtest.STRATEGIES.keys())
    return {"strategies": STRAT_LIST, "all": engine, "engine": engine,
            "total_ea": len(STRAT_LIST)}


@app.get("/api/backtest/symbols")
def backtest_symbols(user: str = Depends(require_user)):
    # se c'è la libreria sweep, esponi le coppie effettivamente testate
    sweep = kv_get("backtest_library", [])
    if sweep:
        syms = []
        for r in sweep:
            if r.get("symbol") and r["symbol"] not in syms:
                syms.append(r["symbol"])
        return {"symbols": syms}
    return {"symbols": COMMON_SYMBOLS}


@app.post("/api/backtest/locked_profile")
async def backtest_locked_save(request: Request, user: str = Depends(require_user)):
    """Salva un locked profile (dal pulsante LOCK della Strategy Library).
    Mappa il base_cfg del frontend nei params che l'EA legge."""
    data = await request.json()
    sym = data.get("symbol") or "*"
    cfg = data.get("base_cfg") or {}
    ovr = data.get("overrides") or {}
    strat = (cfg.get("strategies") or [None])[0]
    profiles = kv_get("locked_profiles", {})
    profiles[sym] = {
        "locked": True,
        "label": data.get("label") or (f"{strat} · {sym}"),
        "saved_at": iso(),
        "strategy": strat,
        "management": ovr.get("GridMode") or data.get("management"),
        "metrics": data.get("metrics") or {},
        "params": {
            "RiskPct": cfg.get("risk_pct"), "AtrSLMult": cfg.get("atr_sl_mult"),
            "AtrTPMult": cfg.get("atr_tp_mult"), "MinScore": cfg.get("min_score"),
            "AdxMin": cfg.get("adx_min"), "HtfBiasRequired": cfg.get("htf_bias"),
            "SessionLondon": cfg.get("session_london"), "SessionNY": cfg.get("session_ny"),
            "SessionAsian": cfg.get("session_asian"), "CooldownBars": cfg.get("cooldown_bars"),
            "DailyDDCap": cfg.get("daily_dd_cap"), "MaxConcurrent": cfg.get("max_concurrent"),
            "BreakevenR": ovr.get("BreakevenR"), "TrailingAtrMult": ovr.get("TrailingAtrMult"),
        },
    }
    kv_set("locked_profiles", profiles)
    return {"ok": True, "symbol": sym, "strategy": strat}


@app.get("/api/backtest/optimize/{job_id}")
def backtest_optimize_job(job_id: str, user: str = Depends(require_user)):
    last = kv_get("backtest_last_optimize")
    if last:
        return {**last, "status": "completed"}
    return {"job_id": job_id, "status": "pending", "results": [], "best": None}


def _library_rows(symbol=""):
    """Righe per la Strategy Library. Priorità: ricetta per-strategia (motore,
    29 strat coi loro parametri/gate/verdetto migliori), poi sweep computato,
    poi i risultati importati, infine demo."""
    # 0) ricetta per-strategia (best_per_strategy dal motore Python) — sorgente
    #    primaria: mostra TUTTE le strategie coi dati reali del backtest.
    recipe = _recipe_library_rows(symbol)
    if recipe:
        recipe.sort(key=lambda x: (x["metrics"]["profit_factor"]
                    if x["metrics"]["profit_factor"] is not None else -9), reverse=True)
        return recipe
    # 1) sweep computato (sweep.py) — strategia × coppia × gestione
    sweep = kv_get("backtest_library", [])
    if sweep:
        rows = []
        for r in sweep:
            if symbol and r.get("symbol") != symbol:
                continue
            m = r.get("metrics") or {}
            tf = r.get("timeframe") or "1h"
            rows.append({
                "strategy": r.get("strategy"), "symbol": r.get("symbol", ""),
                "timeframe": str(tf).lower(), "variant": r.get("variant") or "baseline",
                "atr_sl_mult": None, "atr_tp_mult": None,
                "overrides": {"GridMode": r.get("variant"), "lot_mult": r.get("lot_mult")},
                "metrics": {
                    "n_trades": m.get("n_trades"), "win_rate_pct": m.get("win_rate"),
                    "profit_factor": m.get("profit_factor"), "sharpe": m.get("sharpe"),
                    "max_dd_pct": m.get("max_dd"), "total_return_pct": m.get("return_pct"),
                },
            })
        rows.sort(key=lambda x: (x["metrics"]["sharpe"] if x["metrics"]["sharpe"] is not None else -9),
                  reverse=True)
        return rows
    # 2) risultati importati da Emergent
    imported = kv_get("strategy_results", [])
    rows = []
    for r in imported:
        p = r.get("params") or {}
        tf = r.get("timeframe") or "D1"
        rows.append({
            "strategy": r.get("strategy") or r.get("name"),
            "symbol": symbol or r.get("symbol") or "",
            "timeframe": "1d" if tf in ("D1", "1d", "") else str(tf).lower(),
            "variant": r.get("management") or "baseline",
            "atr_sl_mult": p.get("AtrSLMult", p.get("atr_sl")),
            "atr_tp_mult": p.get("AtrTPMult", p.get("atr_tp")),
            "overrides": p,
            "metrics": {
                "n_trades": r.get("trades"),
                "win_rate_pct": r.get("win_rate"),
                "profit_factor": r.get("profit_factor"),
                "sharpe": r.get("sharpe"),
                "max_dd_pct": r.get("max_dd"),
                "total_return_pct": r.get("net"),
            },
        })
    rows.sort(key=lambda x: (x["metrics"]["sharpe"] if x["metrics"]["sharpe"] is not None else -9),
              reverse=True)
    return rows


@app.get("/api/backtest/strategy_library")
def backtest_library(symbol: str = "", user: str = Depends(require_user)):
    rows = _library_rows(symbol)
    return {"rows": rows, "count": len(rows), "symbol": symbol, "demo": len(rows) == 0}


@app.post("/api/backtest/import_results")
async def backtest_import_results(request: Request, user: str = Depends(require_user)):
    """Importa i risultati reali del backtest (36 strategie) come strategy library
    e, opzionalmente, come locked profiles pronti all'uso per l'EA.

    Body: {
      "results": [ {"strategy","symbol"?,"sharpe","profit_factor","win_rate",
                    "max_dd","management","params":{RiskPct,AtrSLMult,AtrTPMult,
                    MinScore,BreakevenR,TrailingAtrMult,...}}, ... ],
      "make_locked_profiles": true,
      "locked_by": "symbol" | "best_overall"
    }
    """
    body = await request.json()
    results = body.get("results") or (body if isinstance(body, list) else [])
    if not isinstance(results, list) or not results:
        raise HTTPException(status_code=400, detail="campo 'results' (lista) mancante")

    # normalizza e salva la library
    norm = []
    for r in results:
        if not isinstance(r, dict) or not r.get("strategy"):
            continue
        norm.append({
            "name": r["strategy"], "strategy": r["strategy"], "symbol": r.get("symbol", ""),
            "sharpe": r.get("sharpe"), "profit_factor": r.get("profit_factor") or r.get("pf"),
            "win_rate": r.get("win_rate"), "max_dd": r.get("max_dd") or r.get("max_dd_pct"),
            "management": r.get("management") or r.get("variant"),
            "params": r.get("params") or {},
        })
    kv_set("strategy_results", norm)

    locked_written = 0
    if body.get("make_locked_profiles", True):
        profiles = kv_get("locked_profiles", {})
        mode = body.get("locked_by", "symbol")
        # raggruppa: per ogni symbol prendi la strategia col Sharpe migliore
        best_by_sym = {}
        for r in norm:
            sym = r["symbol"] or "*"
            cur = best_by_sym.get(sym)
            if not cur or (r.get("sharpe") or -9) > (cur.get("sharpe") or -9):
                best_by_sym[sym] = r
        keep = best_by_sym
        if mode == "best_overall":
            best = max(norm, key=lambda r: (r.get("sharpe") or -9))
            keep = {"*": best}
        for sym, r in keep.items():
            p = r.get("params") or {}
            profiles[sym] = {
                "locked": True,
                "label": f"{r['strategy']} · {r.get('management') or 'default'}",
                "saved_at": iso(),
                "metrics": {"sharpe": r.get("sharpe"), "profit_factor": r.get("profit_factor"),
                            "win_rate": r.get("win_rate"), "max_dd": r.get("max_dd")},
                "strategy": r["strategy"], "management": r.get("management"),
                "params": {
                    "RiskPct": p.get("RiskPct", p.get("risk_pct")),
                    "AtrSLMult": p.get("AtrSLMult", p.get("atr_sl")),
                    "AtrTPMult": p.get("AtrTPMult", p.get("atr_tp")),
                    "MinScore": p.get("MinScore"), "AdxMin": p.get("AdxMin"),
                    "HtfBiasRequired": p.get("HtfBiasRequired"),
                    "SessionLondon": p.get("SessionLondon"), "SessionNY": p.get("SessionNY"),
                    "SessionAsian": p.get("SessionAsian"), "CooldownBars": p.get("CooldownBars"),
                    "DailyDDCap": p.get("DailyDDCap"), "BreakevenR": p.get("BreakevenR"),
                    "TrailingAtrMult": p.get("TrailingAtrMult"), "MaxConcurrent": p.get("MaxConcurrent"),
                },
            }
            locked_written += 1
        kv_set("locked_profiles", profiles)

    return {"ok": True, "imported": len(norm), "locked_profiles_written": locked_written}


@app.post("/api/backtest/analyze_csv")
async def backtest_analyze_csv(request: Request, user: str = Depends(require_user)):
    """Analizza il CSV per-strategia REALE di un test MT5 (OnTester logger) e
    ritorna la tabella dei verdetti (FORTE/OK/DEBOLE/CRITICA/BLOCCATA/NO_SETUP/
    POCHI_DATI) + raccomandazioni concrete. Body: {csv:"...", min_trades?:int}.
    L'ultimo risultato viene salvato per riaprirlo senza ricaricare il file."""
    body = await request.json()
    text = body.get("csv") or body.get("text") or ""
    if not text.strip():
        raise HTTPException(status_code=400, detail="campo 'csv' mancante")
    try:
        min_trades = int(body.get("min_trades", 10))
    except (ValueError, TypeError):
        min_trades = 10
    out = bt_verdict.analyze_stats_csv(text, min_trades=min_trades)
    if out.get("error"):
        raise HTTPException(status_code=400, detail=out["error"])
    out["analyzed_at"] = iso()
    out["name"] = (body.get("name") or "").strip()[:120]
    kv_set("backtest_last_analysis", out)
    return out


@app.get("/api/backtest/analyze_csv/last")
def backtest_analyze_last(user: str = Depends(require_user)):
    """Ritorna l'ultima analisi CSV salvata (per riaprire la vista senza reupload)."""
    return kv_get("backtest_last_analysis", {}) or {}


@app.get("/api/analytics/journal_verdict")
def analytics_journal_verdict(min_trades: int = 10, limit: int = 2000,
                              user: str = Depends(require_user)):
    """Verdetti per-strategia sui trade REALI gia' sincronizzati dalla demo
    (tabella trades) - stessa forma di /backtest/analyze_csv, cosi' il frontend
    riusa la stessa tabella. Dice quali strategie tenere/spegnere sui soldi veri."""
    try:
        mt = max(1, int(min_trades))
    except (ValueError, TypeError):
        mt = 10
    trades = _trades_with_meta(limit=limit)
    out = bt_verdict.analyze_live_trades(trades, min_trades=mt)
    if out.get("error"):
        return {"rows": [], "summary": {"total": 0, "trades": 0}, "recommendations": {},
                "note": out["error"]}
    out["source"] = "journal_live"
    return out


@app.get("/api/analytics/strategy_diagnostic_live")
def analytics_strategy_diagnostic_live(symbol: str = "", min_trades: int = 10,
                                       user: str = Depends(require_user)):
    """Verdetti + BLOCCHI per-strategia dalle stat live che l'EA gia' pusha
    (/api/ea/strategy_stats): dice quali strategie funzionano E quali formano il
    setup ma non aprono, con quale blocco. Stessa forma/tabella del CSV."""
    try:
        mt = max(1, int(min_trades))
    except (ValueError, TypeError):
        mt = 10
    stats = _all_strategy_stats()
    if symbol:
        stats = [s for s in stats if s["symbol"] == symbol]
    if not stats:
        return {"rows": [], "summary": {"total": 0}, "recommendations": {},
                "note": "nessuna stat live: l'EA non ha ancora pushato (web sync attiva?)"}
    latest = max(stats, key=lambda s: s.get("updated_at") or 0)
    srows = (latest.get("data") or {}).get("strategies") or []
    out = bt_verdict.analyze_stats_rows(srows, min_trades=mt)
    if out.get("error"):
        return {"rows": [], "summary": {"total": 0}, "recommendations": {}, "note": out["error"]}
    out["source"] = "diagnostic_live"
    out["symbol"] = latest.get("symbol")
    out["updated_at"] = latest.get("updated_at")
    return out


@app.get("/api/backtest/strategy_library/{job_id}")
def backtest_library_job(job_id: str, user: str = Depends(require_user)):
    symbol = kv_get(f"btjob:{job_id}", "")
    rows = _library_rows(symbol)
    return {"job_id": job_id, "status": "done", "progress": len(rows),
            "total": len(rows) or 36, "rows": rows}


@app.post("/api/backtest/strategy_library/build")
async def backtest_library_build(request: Request, user: str = Depends(require_user)):
    """Rigenera la libreria per la coppia: ri-esegue lo sweep reale (36×7) su dati
    Yahoo (fallback sintetico). ~4s per coppia."""
    body = await request.json()
    sym = body.get("symbol", "")
    job_id = "lib-" + secrets.token_hex(5)
    kv_set(f"btjob:{job_id}", sym)
    if sym:
        try:
            import sweep
            res = sweep.run_sweep(symbols=[sym], interval="1h", rng="6mo",
                                  optimize=True, progress=False)
            lib = [r for r in kv_get("backtest_library", []) if r.get("symbol") != sym]
            lib.extend(res["rows"])
            kv_set("backtest_library", lib)
        except Exception as e:
            print(f"[NEXUS] library rebuild failed for {sym}: {e}")
    return {"ok": True, "job_id": job_id, "status": "queued", "total": 36}


# ---- coach extra ----
@app.post("/api/coach/notifications/{nid}/read")
def coach_notif_read_one(nid: int, user: str = Depends(require_user)):
    with _conn() as c:
        c.execute("UPDATE coach_notifications SET read=1 WHERE id=?", (nid,))
    return {"ok": True, "id": nid}


@app.get("/api/coach/daily_brief")
def coach_daily_brief(user: str = Depends(require_user)):
    primary, _ = _primary_ea()
    summ = analytics_summary(user)
    if primary:
        brief = (f"EA su {primary.get('symbol')} {'online' if primary.get('_online') else 'offline'}. "
                 f"Equity {primary.get('equity')}, P&L giorno {primary.get('dailyPnL')}, "
                 f"drawdown {primary.get('drawdownPct')}%.")
    else:
        brief = "Nessun EA collegato. Avvia l'EA per ricevere il brief giornaliero."
    if not summ.get("demo"):
        brief += f" Storico: {summ['trades']} trade, win rate {summ['win_rate']}%, PF {summ.get('profit_factor')}."
    # Health: segnala le anomalie attive
    if primary:
        try:
            score, level, _checks, anomaly = _compute_ea_health(primary)
            brief += f" Health {score}/100 ({level})."
            if anomaly:
                brief += " ⚠ " + "; ".join(a["msg"] for a in anomaly[:3])
        except Exception:
            pass
    # Optimizer: migliore e peggiore strategia per profit factor
    try:
        board, _cfg, _bal = _strategy_leaderboard()
        ranked = [r for r in board if r["trades"] >= 5]
        if ranked:
            best = ranked[0]
            worst = ranked[-1]
            brief += (f" Migliore: {best['name']} (PF {best['profit_factor']}); "
                      f"peggiore: {worst['name']} (PF {worst['profit_factor']}).")
    except Exception:
        pass
    return {"id": None, "brief": brief, "demo": primary is None}


@app.get("/api/coach/history")
def coach_history(session_id: str = "default", user: str = Depends(require_user)):
    msgs = kv_get(_coach_sess_key(session_id), [])
    return {"messages": msgs, "session_id": session_id, "demo": not msgs}


@app.get("/api/coach/quick_insights")
def coach_quick_insights(user: str = Depends(require_user)):
    insights = []
    summ = analytics_summary(user)
    if not summ.get("demo"):
        insights.append(f"Profit factor attuale: {summ.get('profit_factor')}.")
        insights.append(f"Win rate: {summ['win_rate']}% su {summ['trades']} trade.")
    br = analytics_by_reason(user)
    worst = min(br["by_reason"], key=lambda r: r["pnl"], default=None)
    if worst and worst["pnl"] < 0:
        insights.append(f"Il motivo più costoso è '{worst['reason']}' ({worst['pnl']}).")
    # Strategie deboli dal leaderboard Optimizer (azionabili dal Coach)
    try:
        board, _cfg, _bal = _strategy_leaderboard()
        for r in board:
            if r["trades"] >= 10 and r["profit_factor"] < 0.9:
                insights.append(
                    f"{r['name']} è in perdita (PF {r['profit_factor']} su {r['trades']} trade): "
                    f"valuta di disattivarla. <action type=\"disable_strategy\" name=\"{r['name']}\" />")
    except Exception:
        pass
    return {"insights": insights, "demo": not insights}


@app.delete("/api/coach/session/{session_id}")
def coach_session_delete(session_id: str, user: str = Depends(require_user)):
    kv_set(_coach_sess_key(session_id), [])
    return {"ok": True, "deleted": session_id}


# ======================= REACT APP (SPA su /app) ======================== #
APP_DIR = STATIC_DIR / "app"


@app.get("/app")
@app.get("/app/{full_path:path}")
def serve_react_app(full_path: str = ""):
    """Serve la dashboard React buildata con fallback SPA per il client routing.

    Cache-Control esplicito, altrimenti il browser sceglie da solo (caching
    euristico) quanto tenere in cache index.html — e ogni deploy SOSTITUISCE
    interamente questa cartella, quindi i file con l'hash della build
    precedente spariscono. Un browser con un index.html vecchio in cache
    proverebbe a caricare un bundle che non esiste piu' (404) e la pagina
    resterebbe bianca. index.html sempre rivalidato; gli asset con hash nel
    nome sono invece sicuri da cachare per sempre (l'hash cambia col
    contenuto).
    """
    index = APP_DIR / "index.html"
    if not index.exists():
        raise HTTPException(status_code=404, detail="frontend React non buildato")
    if full_path:
        candidate = (APP_DIR / full_path).resolve()
        if str(candidate).startswith(str(APP_DIR.resolve())) and candidate.is_file():
            is_hashed_asset = candidate.parent.name in ("js", "css", "media") and candidate != index
            headers = (
                {"Cache-Control": "public, max-age=31536000, immutable"}
                if is_hashed_asset
                else {"Cache-Control": "no-cache"}
            )
            return FileResponse(str(candidate), headers=headers)
    return FileResponse(str(index), headers={"Cache-Control": "no-cache"})


# ======================= STATIC SITE ===================================== #
# Sito multi-pagina (index/login/dashboard/performance/prezzi/faq/strategia).
# Montato su "/" DOPO le route /api: html=True serve index.html sulla root e
# i singoli .html sui rispettivi path. Le route API sopra hanno la precedenza.
# Homepage -> landing 3D immersiva (React su /app). Le altre pagine statiche
# (prezzi/faq/…) restano raggiungibili ai loro path; solo "/" reindirizza.
@app.get("/")
def _root_redirect():
    return RedirectResponse(url="/app/landing")

if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="site")
else:
    @app.get("/site-missing")
    def _no_site():
        return JSONResponse({"service": "nexus-backend", "site": "static/ mancante"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8001")))
