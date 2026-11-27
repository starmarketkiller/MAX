#!/usr/local/bin/python3 -I
"""chart-authority - confine OPERATOR-ONLY dell'autorita' persistente del Chart (CHART-ONLY-DEPLOY-READY-01, GATE 01).

Problema risolto: l'entrypoint storico faceva `chown -R nexus:nexus /data`, quindi il processo applicativo poteva modificare, sostituire o
cancellare il record di autorizzazione (e lo store) che il contratto dichiara scrivibili solo dall'operatore. Questo strumento gira come ROOT
(solo prima di abbassare i privilegi e su richiesta di un operatore con shell root) e stabilisce, a ogni avvio, un confine verificabile:

  /data                      root:nexus  01770   (nexus crea/modifica i propri file; lo sticky bit gli impedisce di rinominare/cancellare cio' che non e' suo)
  /data/chart_auth/          root:root   0755    (record di autorizzazione)    }  namespace PROTETTI: nexus legge, non scrive
  /data/chart_store/         root:root   0755    (store dati autorizzato, ro)  }
  tutto il resto di /data    nexus:nexus         (database, Jarvis, Dukascopy: invariato rispetto all'entrypoint storico)

Principi: fail-closed (se il confine non e' verificato il Chart riceve un percorso d'autorita' inesistente => nega tutto; il backend parte comunque),
nessun symlink accettato nel percorso, nessuna dipendenza fuori dalla stdlib, nessuna lettura di dati sigillati. Non modifica il codice Chart.
Precondizione di sicurezza: `boot` viene eseguito PRIMA di avviare il processo applicativo (nessun processo nexus in esecuzione => nessuna corsa).
"""
from __future__ import annotations

import argparse
import base64
import binascii
import dataclasses
import errno
import hashlib
import json
import os
import posixpath as pp
import sys
import time

SCHEMA = "NEXUS_CHART_AUTHORIZATION_V1"
DATA_ROOT = "/data"
APP_USER = "nexus"
CANARY_NAME = ".chart_boundary_canary"
DENIED_AUTH_PATH = "/nonexistent/chart-authority-boundary-not-verified/chart_authorization.json"
PROBE_OPS = ("read_canary", "write_canary", "truncate_canary", "unlink_canary", "rename_canary_file", "create_in_canary_dir", "mkdir_in_canary_dir",
             "symlink_in_canary_dir", "chmod_canary", "rename_canary_dir", "rmdir_canary_dir", "app_writes_own_file_in_data")
DATA_MODE = 0o1770
DIR_MODE = 0o755
FILE_MODE = 0o644


def log(msg: str) -> None:
    print("[chart-authority] " + msg, file=sys.stderr, flush=True)


# --------------------------------------------------------------------------- modello e policy pura (testabile ovunque)
@dataclasses.dataclass(frozen=True)
class Node:
    path: str
    kind: str          # 'dir' | 'file' | 'symlink' | 'other'
    uid: int
    gid: int
    mode: int          # include lo sticky bit (0o1000)


@dataclasses.dataclass(frozen=True)
class App:
    uid: int
    gid: int
    gids: tuple


def _bits(node: Node, app: App) -> int:
    if node.uid == app.uid:
        return (node.mode >> 6) & 7
    if node.gid in app.gids or node.gid == app.gid:
        return (node.mode >> 3) & 7
    return node.mode & 7


def app_can(node: Node, app: App, want: int) -> bool:
    """Permessi POSIX (r=4, w=2, x=1) dell'identita' applicativa su un nodo (root esclusa)."""
    if app.uid == 0:
        return True
    return (_bits(node, app) & want) == want


def app_can_replace_entry(parent: Node, child: Node, app: App) -> bool:
    """Puo' l'app rinominare/cancellare/sostituire `child` dentro `parent`? Serve w+x sulla directory e, con sticky bit, possedere il figlio o la directory."""
    if not (app_can(parent, app, 2) and app_can(parent, app, 1)):
        return False
    if parent.mode & 0o1000 and app.uid not in (child.uid, parent.uid):
        return False
    return True


def evaluate_boundary(chain: list[Node], app: App) -> list[str]:
    """Violazioni del confine "operator-only" per una catena di nodi dalla radice al bersaglio (file o directory protetta).
    Vuota => l'app puo' al piu' LEGGERE il bersaglio e non puo' modificarlo, sostituirlo, rinominarlo, cancellarlo ne' sostituire un antenato."""
    v: list[str] = []
    if not chain:
        return ["EMPTY_CHAIN"]
    for n in chain:
        if n.kind == "symlink":
            v.append("SYMLINK_IN_PATH:" + n.path)
        elif n.kind == "other":
            v.append("SPECIAL_FILE_IN_PATH:" + n.path)
    for i, n in enumerate(chain):
        if i == 0:
            continue
        if n.uid == app.uid:
            v.append("APP_OWNS_COMPONENT:" + n.path)                    # il proprietario puo' chmod/chown-ridurre e sostituire
        if app_can_replace_entry(chain[i - 1], n, app):
            v.append("APP_CAN_REPLACE:" + n.path)
    target = chain[-1]
    if target.kind == "file" and app_can(target, app, 2):
        v.append("APP_CAN_WRITE_FILE:" + target.path)
    if target.kind == "dir" and app_can(target, app, 2):
        v.append("APP_CAN_WRITE_DIR:" + target.path)
    if not app_can(target, app, 4):
        v.append("APP_CANNOT_READ_TARGET:" + target.path)               # l'autorita' deve restare leggibile dall'applicazione
    return v


def validate_record_bytes(raw: bytes) -> tuple[bool, str, dict | None]:
    """Stessi criteri strutturali del guardia (schema/owner/finestre); non sostituisce la guardia: serve a non pubblicare record inservibili."""
    try:
        doc = json.loads(raw.decode("utf-8"))
    except Exception as ex:                                                 # noqa: BLE001
        return False, "NOT_JSON:" + type(ex).__name__, None
    if not isinstance(doc, dict):
        return False, "NOT_OBJECT", None
    if doc.get("schema") != SCHEMA or doc.get("authorized_by") != "owner":
        return False, "SCHEMA_OR_OWNER_INVALID", None
    ds = doc.get("datasets")
    if not isinstance(ds, dict):
        return False, "DATASETS_NOT_OBJECT", None
    import datetime as dt
    for name, rule in ds.items():
        if not isinstance(rule, dict) or rule.get("kind") != "EXPLICIT_WINDOWS":
            return False, "RULE_KIND_UNSUPPORTED:" + str(name), None        # il confine operatore pubblica solo finestre esplicite (XM-only)
        wins = rule.get("windows_utc")
        if not isinstance(wins, list) or not wins:
            return False, "WINDOWS_MISSING:" + str(name), None
        for w in wins:
            try:
                a, b = (dt.datetime.fromisoformat(str(x).replace("Z", "+00:00")) for x in w)
                if a.tzinfo is None or b.tzinfo is None or not a < b:
                    return False, "WINDOW_INVALID:" + str(name), None
            except Exception:                                               # noqa: BLE001
                return False, "WINDOW_UNPARSABLE:" + str(name), None
    return True, "OK", doc


def deny_record_bytes() -> bytes:
    return (json.dumps({"schema": SCHEMA, "authorized_by": "owner", "decision_ref": "DENY-ALL (revoca/fail-closed)", "datasets": {}}, indent=1, sort_keys=True) + "\n").encode()


# --------------------------------------------------------------------------- accesso al filesystem (reale o fittizio nei test)
class RealFs:
    def lstat(self, path: str) -> Node | None:
        import stat as st
        try:
            s = os.lstat(path)
        except FileNotFoundError:
            return None
        kind = "symlink" if st.S_ISLNK(s.st_mode) else "dir" if st.S_ISDIR(s.st_mode) else "file" if st.S_ISREG(s.st_mode) else "other"
        return Node(path, kind, s.st_uid, s.st_gid, s.st_mode & 0o7777)

    def listdir(self, path: str) -> list[str]:
        return sorted(os.listdir(path))

    def mkdir(self, path: str, mode: int) -> None:
        os.mkdir(path, 0o700)
        os.chmod(path, mode)

    def lchown(self, path: str, uid: int, gid: int) -> None:
        os.lchown(path, uid, gid)

    def chmod(self, path: str, mode: int) -> None:
        os.chmod(path, mode)

    def unlink(self, path: str) -> None:
        os.unlink(path)

    def rmdir(self, path: str) -> None:
        os.rmdir(path)

    def rename(self, src: str, dst: str) -> None:
        os.rename(src, dst)

    def read_bytes(self, path: str) -> bytes:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            chunks = []
            while True:
                c = os.read(fd, 1 << 20)
                if not c:
                    break
                chunks.append(c)
            return b"".join(chunks)
        finally:
            os.close(fd)

    def write_atomic(self, path: str, data: bytes, uid: int, gid: int, mode: int) -> None:
        d = pp.dirname(path)
        tmp = pp.join(d, ".tmp-%d-%s" % (os.getpid(), binascii.hexlify(os.urandom(4)).decode()))
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            os.write(fd, data)
            os.fchown(fd, uid, gid)
            os.fchmod(fd, mode)
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(tmp, path)
        dfd = os.open(d, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)

    def walk(self, top: str):
        """Genera (path, Node) senza seguire symlink; le directory sono restituite prima del contenuto."""
        stack = [top]
        while stack:
            p = stack.pop()
            n = self.lstat(p)
            if n is None:
                continue
            yield p, n
            if n.kind == "dir":
                for name in reversed(self.listdir(p)):
                    stack.append(pp.join(p, name))

    def realpath(self, path: str) -> str:
        return os.path.realpath(path)


def chain_for(fs, path: str) -> list[Node]:
    """Nodi da '/' a `path` (lstat di ogni componente, nessun symlink seguito)."""
    parts = [p for p in path.split("/") if p]
    chain, cur = [], ""
    root = fs.lstat("/")
    if root is None:
        return []
    chain.append(root)
    for p in parts:
        cur = cur + "/" + p
        n = fs.lstat(cur)
        if n is None:
            break
        chain.append(n)
    return chain


# --------------------------------------------------------------------------- operazioni di confine
@dataclasses.dataclass
class Result:
    hardened: bool = False
    deny: bool = False
    actions: list = dataclasses.field(default_factory=list)
    violations: list = dataclasses.field(default_factory=list)
    notes: list = dataclasses.field(default_factory=list)

    def act(self, msg: str) -> None:
        self.actions.append(msg)
        log(msg)

    def fail(self, msg: str) -> None:
        self.deny = True
        self.violations.append(msg)
        log("VIOLAZIONE: " + msg)


def _set_owner_mode(fs, node: Node, uid: int, gid: int, mode: int, res: Result) -> None:
    if node.kind == "symlink":
        return
    if (node.uid, node.gid) != (uid, gid):
        fs.lchown(node.path, uid, gid)
    cur = fs.lstat(node.path)
    if cur is not None and cur.mode != mode:
        fs.chmod(node.path, mode)
        res.act("chmod %s %o -> %o" % (node.path, cur.mode, mode))


def normalize_protected_dir(fs, path: str, res: Result) -> dict:
    """Rende `path` (figlio diretto di /data) una directory root:root 0755 il cui contenuto e' tutto root:root, regolare, 0644/0755.
    Ogni symlink/file speciale e' rimosso. Restituisce info sul record trovato in precedenza con proprieta' non fidata."""
    info = {"untrusted": []}
    n = fs.lstat(path)
    if n is not None and n.kind != "dir":
        fs.unlink(path)
        res.act("rimosso %s (%s al posto della directory protetta)" % (path, n.kind))
        n = None
    if n is None:
        fs.mkdir(path, DIR_MODE)
        fs.lchown(path, 0, 0)
        res.act("creata directory protetta %s root:root %o" % (path, DIR_MODE))
        return info
    for p, node in list(fs.walk(path)):
        if node.kind in ("symlink", "other"):
            fs.unlink(p)
            res.act("rimosso %s (%s non ammesso nel namespace protetto)" % (p, node.kind))
            continue
        if p != path and (node.uid != 0 or node.mode & 0o022):
            info["untrusted"].append(p)                                    # modificabile da non-root prima del boot => contenuto non fidato
        _set_owner_mode(fs, node, 0, 0, DIR_MODE if node.kind == "dir" else FILE_MODE, res)
    return info


def _quarantine(fs, path: str, res: Result) -> None:
    dst = "%s.untrusted-%d" % (path, int(time.time()))
    fs.rename(path, dst)
    fs.lchown(dst, 0, 0)
    fs.chmod(dst, 0o600)                                                   # non piu' leggibile come autorita'
    res.act("quarantena di %s -> %s (proprieta'/permessi non fidati prima del boot)" % (path, dst))


def boot(fs, env: dict, app: App, kernel_probe=None, data: str = DATA_ROOT) -> Result:
    """Stabilisce e verifica il confine. Idempotente: due boot consecutivi non cambiano nulla."""
    res = Result()
    auth = env.get("NEXUS_CHART_AUTH_FILE", "").strip()
    store = env.get("NEXUS_CHART_STORE_ROOT", "").strip()
    d = fs.lstat(data)
    if d is None or d.kind != "dir":
        res.fail("DATA_ROOT_NOT_A_DIRECTORY")
        return res
    if not auth:
        # Chart non configurato con un'autorita' persistente: nessun confine da stabilire; comportamento storico invariato (chown ricorsivo gestito dall'entrypoint)
        res.notes.append("NEXUS_CHART_AUTH_FILE non impostata: modalita' storica, autorita' dall'immagine")
        return res
    res.hardened = True
    protected = []
    for label, p in (("NEXUS_CHART_AUTH_FILE", pp.dirname(auth)), ("NEXUS_CHART_STORE_ROOT", store)):
        if not p:
            continue
        if pp.normpath(p) != p or pp.dirname(p) != data or pp.basename(p) in ("", ".", ".."):
            res.fail("%s_NOT_A_DIRECT_CHILD_OF_DATA:%s" % (label, p))
            continue
        protected.append(p)
    if pp.dirname(auth) not in protected:
        res.fail("AUTH_NAMESPACE_NOT_PROTECTABLE")
        return res
    names = {pp.basename(p) for p in protected} | {CANARY_NAME}

    def is_protected_name(n: str) -> bool:
        return n in names or any(n.startswith(x + ".") for x in names)
    # 1) radice del volume: root:nexus 01770 (sticky: nexus non puo' rinominare/cancellare cio' che non possiede)
    _set_owner_mode(fs, d, 0, app.gid, DATA_MODE, res)
    # 2) proprieta' selettiva: tutto tranne i namespace protetti resta/torna a nexus (nessuna modifica ai permessi interni oltre alla proprieta')
    for name in fs.listdir(data):
        if is_protected_name(name):
            continue
        for p, node in list(fs.walk(pp.join(data, name))):
            if (node.uid, node.gid) != (app.uid, app.gid):
                fs.lchown(p, app.uid, app.gid)
    # 3) namespace protetti (e i loro fratelli .old-/.staging-/.untrusted-, mai assegnati a nexus); residui del canary rimossi
    siblings = [pp.join(data, n) for n in fs.listdir(data) if n not in names and is_protected_name(n)]
    for sib in siblings:
        if sib.startswith(pp.join(data, CANARY_NAME) + "."):
            for p, node in reversed(list(fs.walk(sib))):
                (fs.rmdir if node.kind == "dir" else fs.unlink)(p)
            res.act("rimosso residuo del canary " + sib)
    siblings = [x for x in siblings if fs.lstat(x) is not None]
    untrusted_record = False
    for p in protected + [pp.join(data, CANARY_NAME)] + siblings:
        info = normalize_protected_dir(fs, p, res)
        if p == pp.dirname(auth) and pp.basename(auth) in [pp.basename(x) for x in info["untrusted"]]:
            untrusted_record = True
    # 4) record
    b64 = env.get("CHART_AUTHORITY_B64", "").strip()
    record = fs.lstat(auth)
    if untrusted_record and record is not None:
        _quarantine(fs, auth, res)
        fs.write_atomic(auth, deny_record_bytes(), 0, 0, FILE_MODE)
        res.act("installato record DENY-ALL (il record precedente era modificabile dall'app)")
        record = fs.lstat(auth)
    if b64:
        try:
            raw = base64.b64decode(b64, validate=True)
            ok, why, _ = validate_record_bytes(raw)
        except (binascii.Error, ValueError):
            ok, why, raw = False, "BASE64_INVALID", b""
        if ok:
            fs.write_atomic(auth, raw, 0, 0, FILE_MODE)
            res.act("record installato da CHART_AUTHORITY_B64 sha256=%s" % hashlib.sha256(raw).hexdigest())
        else:
            fs.write_atomic(auth, deny_record_bytes(), 0, 0, FILE_MODE)
            res.act("CHART_AUTHORITY_B64 non valido (%s): installato DENY-ALL" % why)
        record = fs.lstat(auth)
    # canary (specchio dei namespace protetti: i probe distruttivi colpiscono solo lui)
    canary_dir = pp.join(data, CANARY_NAME)
    canary_file = pp.join(canary_dir, "canary.txt")
    fs.write_atomic(canary_file, b"chart-authority canary\n", 0, 0, FILE_MODE)
    # 5-6) verifica del modello su dati reali + probe di kernel (funzione separata: `verify` la usa SENZA mutare nulla)
    verify_boundary(fs, env, app, kernel_probe, data, res)
    return res


def verify_boundary(fs, env: dict, app: App, kernel_probe, data: str, res: Result) -> Result:
    """Verifica del confine: modello (policy su lstat reali, nessun symlink) + probe di kernel come utente applicativo. NON modifica ne' ownership ne' permessi
    (scrive soltanto il file canary dentro la directory root-protetta del canary): sicura da eseguire a servizio attivo."""
    auth = env.get("NEXUS_CHART_AUTH_FILE", "").strip()
    store = env.get("NEXUS_CHART_STORE_ROOT", "").strip()
    if not auth:
        res.notes.append("NEXUS_CHART_AUTH_FILE non impostata: nessun confine da verificare")
        return res
    canary_dir = pp.join(data, CANARY_NAME)
    record = fs.lstat(auth)
    targets = [auth if record is not None else pp.dirname(auth)]
    if store and pp.dirname(store) == data and fs.lstat(store) is not None:
        targets.append(store)
    for t in targets:
        chain = chain_for(fs, t)
        if fs.realpath(t) != t:
            res.fail("REALPATH_DIFFERS:" + t)
        for v in evaluate_boundary(chain, app):
            res.fail(v)
    if record is None:
        res.notes.append("record assente: la guardia del Chart nega tutto finche' l'operatore non lo pubblica")
    if kernel_probe is not None:
        cn = fs.lstat(canary_dir)
        if cn is None or cn.kind != "dir" or cn.uid != 0 or cn.mode & 0o022:
            res.fail("CANARY_MISSING_OR_UNPROTECTED")
            return res
        fs.write_atomic(pp.join(canary_dir, "canary.txt"), b"chart-authority canary\n", 0, 0, FILE_MODE)
        probe = kernel_probe(canary_dir, data, app)
        res.notes.append("kernel_probe=" + json.dumps(probe, sort_keys=True))
        if "probe_error" in probe:
            res.fail("KERNEL_PROBE_ERROR:" + str(probe["probe_error"]))
        for op in PROBE_OPS:                                              # un probe incompleto non prova nulla: ogni operazione attesa deve essere presente
            if op not in probe:
                res.fail("KERNEL_PROBE_MISSING:" + op)
        for op, outcome in probe.items():
            if op == "probe_error":
                continue
            expect_allowed = op in ("read_canary", "app_writes_own_file_in_data")
            if (outcome == "ALLOWED") != expect_allowed:
                res.fail("KERNEL_PROBE_%s=%s" % (op, outcome))
    return res


def linux_kernel_probe(canary_dir: str, data: str, app: App) -> dict:
    """Esegue operazioni NON distruttive per i dati reali (solo sul canary) con l'identita' applicativa, in un processo figlio che abbassa i privilegi."""
    r, w = os.pipe()
    pid = os.fork()
    if pid == 0:
        code = 0
        try:
            os.close(r)
            os.setgroups(list(app.gids))
            os.setgid(app.gid)
            os.setuid(app.uid)
            if os.getuid() == 0 or os.geteuid() == 0:
                raise RuntimeError("privilegi non abbassati")
            cf = pp.join(canary_dir, "canary.txt")
            out: dict = {}

            def attempt(name, fn):
                try:
                    fn()
                    out[name] = "ALLOWED"
                except OSError as e:
                    out[name] = "DENIED:" + errno.errorcode.get(e.errno, str(e.errno))

            def rd():
                with open(cf, "rb") as f:
                    f.read()

            def wr():
                with open(cf, "r+b") as f:
                    f.write(b"x")

            def tr():
                with open(cf, "wb"):
                    pass

            def mk():
                with open(pp.join(canary_dir, "new.txt"), "xb"):
                    pass

            def own():
                p = pp.join(data, ".app_write_probe")
                with open(p, "wb") as f:
                    f.write(b"ok")
                os.unlink(p)

            attempt("read_canary", rd)
            attempt("write_canary", wr)
            attempt("truncate_canary", tr)
            attempt("unlink_canary", lambda: os.unlink(cf))
            attempt("rename_canary_file", lambda: os.rename(cf, cf + ".x"))
            attempt("create_in_canary_dir", mk)
            attempt("mkdir_in_canary_dir", lambda: os.mkdir(pp.join(canary_dir, "d")))
            attempt("symlink_in_canary_dir", lambda: os.symlink("/etc/passwd", pp.join(canary_dir, "l")))
            attempt("chmod_canary", lambda: os.chmod(cf, 0o666))
            attempt("rename_canary_dir", lambda: os.rename(canary_dir, canary_dir + ".moved"))
            attempt("rmdir_canary_dir", lambda: os.rmdir(canary_dir))
            attempt("app_writes_own_file_in_data", own)
            os.write(w, json.dumps(out).encode())
        except BaseException as ex:                                         # noqa: BLE001
            os.write(w, json.dumps({"probe_error": "ERROR:" + repr(ex)}).encode())
            code = 1
        finally:
            os._exit(code)
    os.close(w)
    data_b = b""
    while True:
        c = os.read(r, 65536)
        if not c:
            break
        data_b += c
    os.close(r)
    os.waitpid(pid, 0)
    return json.loads(data_b.decode() or "{}") or {"probe_error": "NO_OUTPUT"}


def app_identity() -> App:
    import pwd
    pw = pwd.getpwnam(APP_USER)
    return App(pw.pw_uid, pw.pw_gid, tuple(os.getgrouplist(APP_USER, pw.pw_gid)))


# --------------------------------------------------------------------------- comandi operatore
def cmd_publish(fs, env, raw: bytes, label: str) -> int:
    ok, why, _ = validate_record_bytes(raw)
    if not ok:
        log("record RIFIUTATO: " + why)
        return 5
    auth = env.get("NEXUS_CHART_AUTH_FILE", "")
    if not auth:
        log("NEXUS_CHART_AUTH_FILE non impostata")
        return 5
    d = fs.lstat(pp.dirname(auth))
    if d is None or d.kind != "dir" or d.uid != 0 or d.mode & 0o022:
        log("la directory dell'autorita' non e' protetta (esegui `chart-authority boot` o riavvia): rifiuto")
        return 6
    fs.write_atomic(auth, raw, 0, 0, FILE_MODE)
    print(json.dumps({"published": auth, "label": label, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}))
    return 0


def cmd_status(fs, env, app: App) -> int:
    auth = env.get("NEXUS_CHART_AUTH_FILE", "")
    rec = fs.lstat(auth) if auth else None
    raw = fs.read_bytes(auth) if rec is not None and rec.kind == "file" else None
    chain = chain_for(fs, auth) if auth else []
    out = {"auth_file": auth, "record": dataclasses.asdict(rec) if rec else None, "sha256": hashlib.sha256(raw).hexdigest() if raw is not None else None,
           "record_valid": validate_record_bytes(raw)[:2] if raw is not None else None, "boundary_violations": evaluate_boundary(chain, app) if chain else ["NO_CHAIN"]}
    print(json.dumps(out, indent=1))
    return 0 if not out["boundary_violations"] and (raw is None or out["record_valid"][0]) else 7


def cmd_install_store(fs, env, src: str, manifest_path: str, manifest_sha: str) -> int:
    store = env.get("NEXUS_CHART_STORE_ROOT", "")
    if not store or pp.dirname(store) != DATA_ROOT:
        log("NEXUS_CHART_STORE_ROOT deve essere un figlio diretto di /data")
        return 5
    mraw = fs.read_bytes(manifest_path)
    if hashlib.sha256(mraw).hexdigest() != manifest_sha.lower():
        log("hash del manifest dati diverso da --manifest-sha256: rifiuto")
        return 5
    man = json.loads(mraw.decode("utf-8"))
    files = man["files"]
    seen = set()
    blobs = {}
    for f in files:
        rel = f["source_relative"]
        if rel.startswith("/") or ".." in rel.split("/"):
            log("percorso non ammesso nel manifest: " + rel)
            return 5
        p = pp.join(src, rel)
        n = fs.lstat(p)
        if n is None or n.kind != "file":
            log("file mancante o non regolare: " + rel)
            return 5
        b = fs.read_bytes(p)
        if len(b) != f["bytes"] or hashlib.sha256(b).hexdigest() != f["sha256"]:
            log("dimensione/hash non conformi: " + rel)
            return 5
        blobs[rel] = b                                                      # gli stessi byte verificati saranno quelli scritti (nessuna seconda lettura: niente TOCTOU)
        seen.add(rel)
    extra = [p for p, n in fs.walk(src) if n.kind != "dir" and pp.relpath(p, src).replace("\\", "/") not in seen]
    if extra:
        log("file extra nella sorgente (rifiuto): %s" % extra[:3])
        return 5
    total = sum(f["bytes"] for f in files)
    if total != man.get("total_bytes"):
        log("somma byte diversa dal manifest")
        return 5
    stage = "%s.staging-%d" % (store, int(time.time()))
    fs.mkdir(stage, DIR_MODE)
    fs.lchown(stage, 0, 0)
    for f in files:
        rel = f["source_relative"]
        dst = pp.join(stage, rel)
        cur = stage
        for part in rel.split("/")[:-1]:
            cur = pp.join(cur, part)
            if fs.lstat(cur) is None:
                fs.mkdir(cur, DIR_MODE)
                fs.lchown(cur, 0, 0)
        fs.write_atomic(dst, blobs[rel], 0, 0, FILE_MODE)
    old = None
    if fs.lstat(store) is not None:
        old = "%s.old-%d" % (store, int(time.time()))
        fs.rename(store, old)
    fs.rename(stage, store)
    print(json.dumps({"installed": store, "files": len(files), "bytes": total, "previous": old}))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="chart-authority")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("boot")
    sub.add_parser("status")
    sub.add_parser("verify")
    sub.add_parser("revoke")
    p = sub.add_parser("publish")
    p.add_argument("--file", required=True)
    s = sub.add_parser("install-store")
    s.add_argument("--from", dest="src", required=True)
    s.add_argument("--manifest", required=True)
    s.add_argument("--manifest-sha256", required=True)
    a = ap.parse_args(argv)
    if os.name != "posix":
        log("richiede Linux")
        return 4
    if os.geteuid() != 0:
        log("richiede root")
        return 4
    fs, env, app = RealFs(), dict(os.environ), app_identity()
    if a.cmd == "boot":
        res = boot(fs, env, app, kernel_probe=linux_kernel_probe)
        print(json.dumps(dataclasses.asdict(res), indent=1))
        return 3 if res.deny else 0
    if a.cmd == "verify":                                                   # sola verifica: nessuna mutazione di ownership/permessi (sicuro a servizio attivo)
        res = Result(hardened=True)
        verify_boundary(fs, env, app, linux_kernel_probe, DATA_ROOT, res)
        print(json.dumps(dataclasses.asdict(res), indent=1))
        return 3 if res.deny else 0
    if a.cmd == "status":
        return cmd_status(fs, env, app)
    if a.cmd == "revoke":
        return cmd_publish(fs, env, deny_record_bytes(), "REVOKE")
    if a.cmd == "publish":
        return cmd_publish(fs, env, fs.read_bytes(a.file), a.file)
    if a.cmd == "install-store":
        return cmd_install_store(fs, env, a.src, a.manifest, a.manifest_sha256)
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:                                                # noqa: BLE001
        log("ERRORE: %r" % (exc,))
        sys.exit(2)
