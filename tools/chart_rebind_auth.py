"""Ricalcola i legami di hash (normalizzati LF) fra server/chart_authorization.json e i manifest canonici di Phase 7. Da eseguire SOLO su decisione esplicita del proprietario:
cambiare i manifest canonici senza rieseguire questo comando chiude l'accesso (fail-closed)."""
import hashlib, json, os, sys
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
canon = os.path.join(ROOT, "server", "research_scripts", "phase7")
path = os.path.join(ROOT, "server", "chart_authorization.json")
a = json.load(open(path, encoding="utf-8"))
a["bound_manifests"] = {f: hashlib.sha256(open(os.path.join(canon, f), "rb").read().replace(b"\r\n", b"\n")).hexdigest() for f in a["bound_manifests"]}
open(path, "w", encoding="utf-8", newline="\n").write(json.dumps(a, indent=1) + "\n")
print(json.dumps(a["bound_manifests"], indent=1))
