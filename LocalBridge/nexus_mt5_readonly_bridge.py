#!/usr/bin/env python3
"""Local read-only view of the MT5 account. It does not send, modify or close orders.

Bind is refused unless it is loopback. The process belongs on the PC that
runs the terminal, never on Render. Credentials are not read and not returned.
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOOPBACK = {"127.0.0.1", "localhost"}


def read_mt5_account():
    """Ask the local terminal who is logged in. No order_send, no password."""
    try:
        import MetaTrader5 as mt5
    except ImportError:
        return {"connected": False, "reason": "MetaTrader5 package not installed"}
    if not mt5.initialize():
        return {"connected": False, "reason": "terminal not initialized"}
    info = mt5.account_info()
    if info is None:
        return {"connected": False, "reason": "no account"}
    trade_mode = {0: "DEMO", 1: "CONTEST", 2: "LIVE"}.get(int(info.trade_mode), "UNKNOWN")
    return {"connected": True, "login": int(info.login), "server": str(info.server),
            "trade_mode": trade_mode}


def make_handler(token, reader):
    expected = str(token or "")
    if len(expected) < 24:
        raise ValueError("bridge token must be at least 24 characters")

    class Handler(BaseHTTPRequestHandler):
        def _json(self, code, body):
            raw = json.dumps(body).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _authorized(self):
            return self.headers.get("X-Nexus-Token") == expected

        def do_GET(self):
            if self.path != "/v1/mt5/account":
                self._json(404, {"error": "not_found"})
                return
            if not self._authorized():
                self._json(401, {"error": "unauthorized"})
                return
            account = reader()
            account["accepts_orders"] = False
            self._json(200, account)

        def do_POST(self):
            self._json(405, {"error": "this bridge does not accept orders"})

        def log_message(self, fmt, *args):
            return

    return Handler


def serve(host, port, token, reader=read_mt5_account):
    if host not in LOOPBACK:
        raise RuntimeError("bridge refuses a public bind")
    server = ThreadingHTTPServer((host, port), make_handler(token, reader))
    server.serve_forever()
    return server


if __name__ == "__main__":
    import os
    token = os.environ.get("NEXUS_BRIDGE_TOKEN", "")
    serve("127.0.0.1", int(os.environ.get("NEXUS_MT5_BRIDGE_PORT", "8765")), token)
