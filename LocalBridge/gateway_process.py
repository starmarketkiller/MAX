"""Identify a listener before starting the gateway. This file starts nothing."""
from __future__ import annotations

import argparse
import json
import socket
import sys
from http.client import HTTPConnection
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nexus_local_inference_gateway import SERVICE_NAME  # noqa: E402

EXIT_GATEWAY = 0
EXIT_FOREIGN = 3
EXIT_ABSENT = 4


def identify(port, timeout=4.0):
    """Return gateway, foreign, or absent. A non-gateway occupant is foreign.

    Health asks Ollama with a 2s timeout before it answers. The identity
    read has to outlast that check, otherwise our own gateway looks foreign
    while Ollama is down and a second start would be refused for the wrong
    reason. A peer that accepts and never answers is still foreign.
    """
    probe = socket.socket()
    probe.settimeout(timeout)
    try:
        occupied = probe.connect_ex(("127.0.0.1", int(port))) == 0
    except OSError:
        occupied = False
    finally:
        probe.close()
    if not occupied:
        return "absent"
    try:
        conn = HTTPConnection("127.0.0.1", int(port), timeout=timeout)
        conn.request("GET", "/v1/jarvis/health")
        response = conn.getresponse()
        body = json.loads(response.read().decode("utf-8"))
        conn.close()
    except (OSError, ValueError, json.JSONDecodeError):
        return "foreign"
    if (response.status == 200 and body.get("service") == SERVICE_NAME
            and body.get("liveness") is True):
        return "gateway"
    return "foreign"


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args(argv)
    kind = identify(args.port)
    print(kind)
    return {"gateway": EXIT_GATEWAY, "foreign": EXIT_FOREIGN, "absent": EXIT_ABSENT}[kind]


if __name__ == "__main__":
    raise SystemExit(main())
