#!/usr/bin/env python3
"""PR8 — worker LocalBridge DEDUPLICATO.

Prima esisteva una copia byte-identica sia qui sia in `server/nexus_local_worker.py`
(due sorgenti da mantenere in sync a mano). La fonte unica e' ora
`server/nexus_local_worker.py`; questo resta come entrypoint storico ed esegue
quel file, cosi' non c'e' piu' codice duplicato da tenere allineato.
"""
import os
import runpy

_CANONICAL = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "server", "nexus_local_worker.py")

if __name__ == "__main__":
    runpy.run_path(_CANONICAL, run_name="__main__")
