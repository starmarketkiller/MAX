"""CHART-ONLY-DEPLOY-READY-01 / GATE 01 - confine operator-only dell'autorita' persistente.

Cosa provano questi test (e cosa NO):
 * la POLICY (`evaluate_boundary`) e la logica di `boot`/`publish`/`install-store` su un filesystem FITTIZIO che modella proprietari, modi, sticky bit e symlink;
 * la logica dell'entrypoint con comandi sostituiti da stub (fail-closed, modalita' storica).
NON provano l'enforcement del kernel Linux (chown/chmod/sticky reali, `su`, container): quello e' coperto da `tools/docker_runtime_verify.sh`
(da eseguire su Linux/Docker: CI o host autorizzato) e dai probe di kernel dentro `chart-authority boot`.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import posixpath as pp
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

SERVER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVER))
import chart_authority_ctl as ctl  # noqa: E402
from chart_authority_ctl import App, Node, evaluate_boundary  # noqa: E402

APP = App(uid=10001, gid=10001, gids=(10001,))
DATA = "/data"
AUTH = "/data/chart_auth/chart_authorization.json"
STORE = "/data/chart_store"
ENV = {"NEXUS_CHART_AUTH_FILE": AUTH, "NEXUS_CHART_STORE_ROOT": STORE}


# ------------------------------------------------------------------ filesystem fittizio
class FakeFs:
    def __init__(self):
        self.n: dict[str, dict] = {}
        self.add("/", "dir", 0, 0, 0o755)

    def add(self, path, kind, uid, gid, mode, data=b""):
        self.n[path] = {"kind": kind, "uid": uid, "gid": gid, "mode": mode, "data": data}

    def lstat(self, path):
        d = self.n.get(path)
        return None if d is None else Node(path, d["kind"], d["uid"], d["gid"], d["mode"])

    def listdir(self, path):
        pre = path.rstrip("/") + "/"
        return sorted({p[len(pre):].split("/")[0] for p in self.n if p.startswith(pre) and p != path})

    def mkdir(self, path, mode):
        assert pp.dirname(path) in self.n and self.n[pp.dirname(path)]["kind"] == "dir", path
        assert path not in self.n, path
        self.add(path, "dir", 0, 0, mode)

    def lchown(self, path, uid, gid):
        self.n[path]["uid"], self.n[path]["gid"] = uid, gid

    def chmod(self, path, mode):
        self.n[path]["mode"] = mode

    def unlink(self, path):
        assert self.n[path]["kind"] != "dir", path
        del self.n[path]

    def rmdir(self, path):
        assert not self.listdir(path), path
        del self.n[path]

    def rename(self, src, dst):
        moved = {p: v for p, v in self.n.items() if p == src or p.startswith(src + "/")}
        for p in moved:
            del self.n[p]
        for p, v in moved.items():
            self.n[dst + p[len(src):]] = v

    def read_bytes(self, path):
        assert self.n[path]["kind"] == "file", path
        return self.n[path]["data"]

    def write_atomic(self, path, data, uid, gid, mode):
        assert self.n[pp.dirname(path)]["kind"] == "dir"
        self.add(path, "file", uid, gid, mode, data)

    def walk(self, top):
        stack = [top]
        while stack:
            p = stack.pop()
            nd = self.lstat(p)
            if nd is None:
                continue
            yield p, nd
            if nd.kind == "dir":
                for name in reversed(self.listdir(p)):
                    stack.append(pp.join(p, name))

    def realpath(self, p):
        return p

    def snapshot(self):
        return {p: (v["kind"], v["uid"], v["gid"], v["mode"], hashlib.sha256(v["data"]).hexdigest()) for p, v in self.n.items()}


def render_mount(fs, with_legacy_chart=False):
    """Stato di un volume Render appena montato (root:root) con dati dell'app preesistenti; opzionalmente un layout storico (tutto nexus) con record/store modificabili dall'app."""
    fs.add(DATA, "dir", 0, 0, 0o755)
    fs.add("/data/nexus.db", "file", 10001, 10001, 0o644, b"sqlite")
    fs.add("/data/nexus.db-wal", "file", 0, 0, 0o600, b"wal")                          # creato come root da una vecchia versione: deve tornare a nexus
    fs.add("/data/jarvis", "dir", 10001, 10001, 0o750)
    fs.add("/data/jarvis/state.json", "file", 10001, 10001, 0o600, b"{}")
    fs.add("/data/dukascopy", "dir", 10001, 10001, 0o755)
    fs.add("/data/dukascopy/2023.bin", "file", 10001, 10001, 0o644, b"x")
    if with_legacy_chart:
        fs.add("/data/chart_auth", "dir", 10001, 10001, 0o755)
        good = json.dumps({"schema": ctl.SCHEMA, "authorized_by": "owner", "datasets": {"X": {"kind": "EXPLICIT_WINDOWS", "windows_utc": [["2026-11-16T00:00:00Z", "2026-11-20T22:00:00Z"]]}}}).encode()
        fs.add(AUTH, "file", 10001, 10001, 0o644, good)                                # modificabile dall'app prima dell'upgrade => non fidato
        fs.add(STORE, "dir", 10001, 10001, 0o755)
        fs.add(STORE + "/manifest.json", "file", 10001, 10001, 0o644, b"{}")
    return fs


def good_record(window=("2026-11-16T00:00:00Z", "2026-11-20T22:00:00Z")):
    return json.dumps({"schema": ctl.SCHEMA, "authorized_by": "owner", "decision_ref": "t", "datasets": {"XM": {"kind": "EXPLICIT_WINDOWS", "windows_utc": [list(window)]}}}).encode()


def hardened_fs():
    fs = FakeFs()
    render_mount(fs)
    return fs


# ------------------------------------------------------------------ policy pura
def chain(*spec):
    return [Node(p, k, u, g, m) for p, k, u, g, m in spec]


PROTECTED = chain(("/", "dir", 0, 0, 0o755), ("/data", "dir", 0, 10001, 0o1770), ("/data/chart_auth", "dir", 0, 0, 0o755), (AUTH, "file", 0, 0, 0o644))


def test_policy_accepts_the_hardened_layout():
    assert evaluate_boundary(PROTECTED, APP) == []


@pytest.mark.parametrize("mut,expect", [
    (lambda c: [c[0], c[1], c[2], Node(AUTH, "file", 10001, 10001, 0o644)], "APP_OWNS_COMPONENT"),                       # record dell'app (layout storico)
    (lambda c: [c[0], c[1], Node(c[2].path, "dir", 10001, 10001, 0o755), c[3]], "APP_OWNS_COMPONENT"),                   # directory dell'app
    (lambda c: [c[0], Node("/data", "dir", 10001, 10001, 0o755), c[2], c[3]], "APP_OWNS_COMPONENT"),                     # /data di nexus (puo' rinominare chart_auth)
    (lambda c: [c[0], Node("/data", "dir", 0, 10001, 0o770), c[2], c[3]], "APP_CAN_REPLACE:/data/chart_auth"),           # /data g+w SENZA sticky: nexus sostituisce la directory
    (lambda c: [c[0], c[1], Node(c[2].path, "dir", 0, 0, 0o775), c[3]], None),                                           # g+w root: nexus non e' nel gruppo root
    (lambda c: [c[0], c[1], Node(c[2].path, "dir", 0, 10001, 0o775), c[3]], "APP_CAN_REPLACE:" + AUTH),                  # directory scrivibile dal gruppo nexus
    (lambda c: [c[0], c[1], c[2], Node(AUTH, "file", 0, 10001, 0o664)], "APP_CAN_WRITE_FILE"),                           # file g+w nexus
    (lambda c: [c[0], c[1], c[2], Node(AUTH, "file", 0, 0, 0o666)], "APP_CAN_WRITE_FILE"),                               # world-writable
    (lambda c: [c[0], c[1], Node(c[2].path, "symlink", 0, 0, 0o777), c[3]], "SYMLINK_IN_PATH"),                          # directory sostituita da symlink
    (lambda c: [c[0], c[1], c[2], Node(AUTH, "symlink", 0, 0, 0o777)], "SYMLINK_IN_PATH"),
    (lambda c: [c[0], c[1], c[2], Node(AUTH, "file", 0, 0, 0o600)], "APP_CANNOT_READ_TARGET"),                            # l'app deve poterlo leggere
    (lambda c: [c[0], c[1], c[2], Node(AUTH, "other", 0, 0, 0o644)], "SPECIAL_FILE_IN_PATH"),
])
def test_policy_flags_every_way_the_app_could_alter_or_replace_the_authority(mut, expect):
    v = evaluate_boundary(mut(PROTECTED), APP)
    if expect is None:
        assert v == []
    else:
        assert any(x.startswith(expect) for x in v), v


def test_policy_app_in_supplementary_group_is_considered():
    a = App(uid=10001, gid=10001, gids=(10001, 777))
    c = [PROTECTED[0], PROTECTED[1], Node(PROTECTED[2].path, "dir", 0, 777, 0o775), PROTECTED[3]]
    assert any(x.startswith("APP_CAN_REPLACE") for x in evaluate_boundary(c, a))


def test_policy_legacy_entrypoint_layout_is_a_violation():
    legacy = chain(("/", "dir", 0, 0, 0o755), ("/data", "dir", 10001, 10001, 0o755), ("/data/chart_auth", "dir", 10001, 10001, 0o755), (AUTH, "file", 10001, 10001, 0o644))
    v = evaluate_boundary(legacy, APP)
    assert len(v) >= 5 and any("APP_CAN_WRITE_FILE" in x for x in v)


# ------------------------------------------------------------------ boot
def probe_ok(canary_dir, data, app):
    out = {op: "DENIED:EACCES" for op in ctl.PROBE_OPS}
    out["read_canary"] = "ALLOWED"
    out["app_writes_own_file_in_data"] = "ALLOWED"
    return out


def test_boot_fresh_render_volume_creates_protected_namespaces_and_preserves_app_data():
    fs = hardened_fs()
    before_app = {p: v for p, v in fs.snapshot().items() if p.startswith(("/data/jarvis", "/data/dukascopy", "/data/nexus.db"))}
    res = ctl.boot(fs, dict(ENV), APP, kernel_probe=probe_ok)
    assert not res.deny and res.hardened, res.violations
    assert fs.lstat(DATA).uid == 0 and fs.lstat(DATA).gid == APP.gid and fs.lstat(DATA).mode == 0o1770
    for p in ("/data/chart_auth", STORE, "/data/.chart_boundary_canary"):
        n = fs.lstat(p)
        assert (n.kind, n.uid, n.gid, n.mode) == ("dir", 0, 0, 0o755), p
    # dati dell'app: proprietario nexus, contenuto e MODI invariati (nessun chmod indiscriminato); nexus.db-wal torna a nexus
    after = fs.snapshot()
    for p, (k, u, g, m, h) in before_app.items():
        assert after[p][0] == k and after[p][4] == h
        assert (after[p][1], after[p][2]) == (10001, 10001), p
        if p != "/data/nexus.db-wal":
            assert after[p][3] == m, p
    assert fs.lstat(AUTH) is None and any("record assente" in n for n in res.notes)


def test_boot_upgrade_from_legacy_layout_quarantines_the_app_modifiable_record_and_denies():
    fs = FakeFs()
    render_mount(fs, with_legacy_chart=True)
    res = ctl.boot(fs, dict(ENV), APP, kernel_probe=probe_ok)
    assert not res.deny, res.violations
    rec = fs.lstat(AUTH)
    assert (rec.uid, rec.gid, rec.mode) == (0, 0, 0o644)
    assert json.loads(fs.read_bytes(AUTH))["datasets"] == {}                       # il vecchio record (app-modificabile) NON e' piu' autorita': DENY-ALL
    q = [p for p in fs.n if ".untrusted-" in p]
    assert q and fs.lstat(q[0]).mode == 0o600 and fs.lstat(q[0]).uid == 0
    assert (fs.lstat(STORE).uid, fs.lstat(STORE + "/manifest.json").uid) == (0, 0)  # anche lo store torna di root
    assert all(not evaluate_boundary(ctl.chain_for(fs, t), APP) for t in (AUTH, STORE))


def test_boot_is_idempotent_and_survives_restart_cycles():
    fs = hardened_fs()
    ctl.boot(fs, dict(ENV), APP, kernel_probe=probe_ok)
    s1 = fs.snapshot()
    for _ in range(3):
        res = ctl.boot(fs, dict(ENV), APP, kernel_probe=probe_ok)
        assert not res.deny and res.actions == [], res.actions
    assert fs.snapshot() == s1


def test_boot_restores_permissions_if_the_platform_resets_the_mount_root():
    fs = hardened_fs()
    ctl.boot(fs, dict(ENV), APP, kernel_probe=probe_ok)
    fs.lchown(DATA, 10001, 10001)
    fs.chmod(DATA, 0o755)                                                          # il nuovo mount (redeploy) riporta /data a uno stato generico
    res = ctl.boot(fs, dict(ENV), APP, kernel_probe=probe_ok)
    assert (fs.lstat(DATA).uid, fs.lstat(DATA).gid, fs.lstat(DATA).mode) == (0, APP.gid, 0o1770) and not res.deny


def test_boot_installs_record_from_operator_env_and_it_survives_the_next_boot():
    fs = hardened_fs()
    env = dict(ENV, CHART_AUTHORITY_B64=base64.b64encode(good_record()).decode())
    res = ctl.boot(fs, env, APP, kernel_probe=probe_ok)
    assert not res.deny and fs.read_bytes(AUTH) == good_record()
    assert (fs.lstat(AUTH).uid, fs.lstat(AUTH).mode) == (0, 0o644)
    ctl.boot(fs, dict(ENV), APP, kernel_probe=probe_ok)                             # riavvio senza la variabile: il record persistente resta
    assert fs.read_bytes(AUTH) == good_record()


@pytest.mark.parametrize("b64", ["!!!notbase64!!!", base64.b64encode(b"{not json").decode(), base64.b64encode(json.dumps({"schema": "X"}).encode()).decode(),
                                 base64.b64encode(json.dumps({"schema": ctl.SCHEMA, "authorized_by": "owner", "datasets": {"A": {"kind": "PHASE7_PARTITIONS"}}}).encode()).decode(),
                                 base64.b64encode(json.dumps({"schema": ctl.SCHEMA, "authorized_by": "owner", "datasets": {"A": {"kind": "EXPLICIT_WINDOWS", "windows_utc": [["2026-11-20T00:00:00Z", "2026-11-16T00:00:00Z"]]}}}).encode()).decode()])
def test_boot_invalid_operator_record_installs_deny_all(b64):
    fs = hardened_fs()
    fs.add("/data/chart_auth", "dir", 0, 0, 0o755)
    fs.add(AUTH, "file", 0, 0, 0o644, good_record())                                # esisteva un record valido
    res = ctl.boot(fs, dict(ENV, CHART_AUTHORITY_B64=b64), APP, kernel_probe=probe_ok)
    assert not res.deny
    assert json.loads(fs.read_bytes(AUTH))["datasets"] == {}                        # fail-closed: nessun contenuto precedente sopravvive a una configurazione invalida


def test_boot_removes_planted_symlinks_and_special_files():
    fs = hardened_fs()
    fs.add("/data/chart_auth", "symlink", 10001, 10001, 0o777)                      # la directory del record sostituita da un symlink (es. a /data/jarvis)
    fs.add("/data/chart_store", "dir", 10001, 10001, 0o755)
    fs.add("/data/chart_store/leak", "symlink", 10001, 10001, 0o777)
    res = ctl.boot(fs, dict(ENV), APP, kernel_probe=probe_ok)
    assert not res.deny
    assert fs.lstat("/data/chart_auth").kind == "dir" and fs.lstat("/data/chart_auth").uid == 0
    assert fs.lstat("/data/chart_store/leak") is None


def test_boot_siblings_of_protected_namespaces_never_go_to_the_app():
    fs = hardened_fs()
    ctl.boot(fs, dict(ENV), APP, kernel_probe=probe_ok)
    fs.add("/data/chart_store.old-1", "dir", 0, 0, 0o755)
    fs.add("/data/chart_store.old-1/m.json", "file", 0, 0, 0o644, b"{}")
    fs.add("/data/.chart_boundary_canary.moved", "dir", 0, 0, 0o755)
    ctl.boot(fs, dict(ENV), APP, kernel_probe=probe_ok)
    assert fs.lstat("/data/chart_store.old-1").uid == 0 and fs.lstat("/data/chart_store.old-1/m.json").uid == 0
    assert fs.lstat("/data/.chart_boundary_canary.moved") is None


def test_boot_denies_when_paths_are_not_direct_children_of_data():
    for env in ({"NEXUS_CHART_AUTH_FILE": "/data/a/b/auth.json"}, {"NEXUS_CHART_AUTH_FILE": "/etc/auth.json"}, {"NEXUS_CHART_AUTH_FILE": AUTH, "NEXUS_CHART_STORE_ROOT": "/data/x/y"}):
        res = ctl.boot(hardened_fs(), env, APP, kernel_probe=probe_ok)
        assert res.deny, env


def test_boot_without_persistent_authority_is_the_historical_mode_and_changes_nothing():
    fs = hardened_fs()
    s = fs.snapshot()
    res = ctl.boot(fs, {}, APP, kernel_probe=probe_ok)
    assert not res.hardened and not res.deny and fs.snapshot() == s


@pytest.mark.parametrize("bad", ["write_canary", "rename_canary_dir", "unlink_canary", "create_in_canary_dir", "chmod_canary", "symlink_in_canary_dir"])
def test_kernel_probe_allowing_any_forbidden_operation_denies(bad):
    def probe(c, d, a):
        out = dict(probe_ok(c, d, a))
        out[bad] = "ALLOWED"
        return out
    res = ctl.boot(hardened_fs(), dict(ENV), APP, kernel_probe=probe)
    assert res.deny and any("KERNEL_PROBE_" + bad in v for v in res.violations)


def test_kernel_probe_blocking_the_apps_own_writes_denies_too():
    def probe(c, d, a):
        out = dict(probe_ok(c, d, a))
        out["app_writes_own_file_in_data"] = "DENIED:EACCES"                        # il confine non deve togliere all'app la scrittura di DB/Jarvis
        return out
    assert ctl.boot(hardened_fs(), dict(ENV), APP, kernel_probe=probe).deny


def test_incomplete_kernel_probe_denies():
    def probe(c, d, a):
        out = dict(probe_ok(c, d, a))
        del out["rename_canary_dir"]
        return out
    res = ctl.boot(hardened_fs(), dict(ENV), APP, kernel_probe=probe)
    assert res.deny and any("KERNEL_PROBE_MISSING:rename_canary_dir" in v for v in res.violations)


def test_kernel_probe_failure_denies():
    assert ctl.boot(hardened_fs(), dict(ENV), APP, kernel_probe=lambda c, d, a: {"probe_error": "ERROR:x"}).deny


def test_boundary_violation_in_real_layout_is_detected_if_a_component_is_app_owned():
    fs = hardened_fs()
    ctl.boot(fs, dict(ENV), APP, kernel_probe=probe_ok)
    fs.lchown("/data/chart_auth", 10001, 10001)                                    # corruzione successiva del confine
    v = [x for t in (AUTH, "/data/chart_auth") for x in evaluate_boundary(ctl.chain_for(fs, t), APP)]
    assert v


# ------------------------------------------------------------------ comandi operatore
def protected_fs_with_record():
    fs = hardened_fs()
    ctl.boot(fs, dict(ENV, CHART_AUTHORITY_B64=base64.b64encode(good_record()).decode()), APP, kernel_probe=probe_ok)
    return fs


def test_publish_requires_valid_record_and_protected_directory_and_is_root_owned():
    fs = protected_fs_with_record()
    new = good_record(("2026-11-16T00:00:00Z", "2026-11-18T00:00:00Z"))
    assert ctl.cmd_publish(fs, dict(ENV), new, "t") == 0
    assert fs.read_bytes(AUTH) == new and (fs.lstat(AUTH).uid, fs.lstat(AUTH).mode) == (0, 0o644)
    assert ctl.cmd_publish(fs, dict(ENV), b"{broken", "t") == 5 and fs.read_bytes(AUTH) == new      # rifiutato, record invariato
    fs.lchown("/data/chart_auth", 10001, 10001)
    assert ctl.cmd_publish(fs, dict(ENV), new, "t") == 6                                            # directory non protetta: rifiuto


def test_revoke_publishes_deny_all_and_restore_requires_a_valid_record():
    fs = protected_fs_with_record()
    assert ctl.cmd_publish(fs, dict(ENV), ctl.deny_record_bytes(), "REVOKE") == 0
    assert json.loads(fs.read_bytes(AUTH))["datasets"] == {}
    assert ctl.cmd_publish(fs, dict(ENV), good_record(), "RESTORE") == 0 and json.loads(fs.read_bytes(AUTH))["datasets"]


def test_status_reports_clean_boundary():
    fs = protected_fs_with_record()
    assert ctl.cmd_status(fs, dict(ENV), APP) == 0


# ------------------------------------------------------------------ install-store con il manifest dati reale (273.050 byte)
TRANSFER = Path(os.environ.get("NEXUS_CHART_TRANSFER_MANIFEST", r"C:\Users\User\ClaudeWork\NEXUS_CHART_REAL_DATA_V1_FIX_02\DATA_TRANSFER_MANIFEST.json"))
STORE_SRC = Path(os.environ.get("NEXUS_CHART_STORE_SRC", r"C:\Users\User\ClaudeWork\NEXUS_CHART_REAL_DATA_V1\store"))


def load_tree(fs, root_virtual, real_dir):
    fs.add(root_virtual, "dir", 10001, 10001, 0o755)
    for b, ds, fl in os.walk(real_dir):
        rel = os.path.relpath(b, real_dir).replace("\\", "/")
        vb = root_virtual if rel == "." else root_virtual + "/" + rel
        if rel != ".":
            fs.add(vb, "dir", 10001, 10001, 0o755)
        for f in fl:
            fs.add(vb + "/" + f, "file", 10001, 10001, 0o644, (Path(b) / f).read_bytes())


@pytest.mark.skipif(not (TRANSFER.is_file() and STORE_SRC.is_dir()), reason="manifest dati/store XM non presenti")
def test_install_store_verifies_the_real_10_files_273050_bytes_and_makes_them_root_read_only():
    man = json.loads(TRANSFER.read_text(encoding="utf-8"))
    assert man["file_count"] == 10 and man["total_bytes"] == 273050
    fs = protected_fs_with_record()
    load_tree(fs, "/inbox/store", STORE_SRC)
    # restringe l'inbox al solo dataset del manifest (lo store locale puo' contenere altri dataset non autorizzati)
    for p in [p for p in list(fs.n) if p.startswith("/inbox/store/") and not p.startswith("/inbox/store/XM-GOLD-2026-11-16-20")]:
        if fs.n[p]["kind"] != "dir" or p != "/inbox/store":
            del fs.n[p]
    fs.add("/inbox/manifest.json", "file", 10001, 10001, 0o644, TRANSFER.read_bytes())
    sha = hashlib.sha256(TRANSFER.read_bytes()).hexdigest()
    assert ctl.cmd_install_store(fs, dict(ENV), "/inbox/store", "/inbox/manifest.json", sha) == 0
    installed = [p for p, v in fs.n.items() if p.startswith(STORE + "/") and v["kind"] == "file"]
    assert len(installed) == 10 and sum(len(fs.n[p]["data"]) for p in installed) == 273050
    assert all(fs.n[p]["uid"] == 0 and fs.n[p]["mode"] == 0o644 for p in installed)
    assert evaluate_boundary(ctl.chain_for(fs, STORE), APP) == []
    # un file alterato (1 byte) o un file extra o un hash del manifest errato => rifiuto, nessuna scrittura
    tamper = protected_fs_with_record()
    load_tree(tamper, "/inbox/store", STORE_SRC)
    for p in [p for p in list(tamper.n) if p.startswith("/inbox/store/") and not p.startswith("/inbox/store/XM-GOLD-2026-11-16-20")]:
        if tamper.n[p]["kind"] != "dir":
            del tamper.n[p]
    tamper.add("/inbox/manifest.json", "file", 10001, 10001, 0o644, TRANSFER.read_bytes())
    victim = next(p for p, v in tamper.n.items() if p.startswith("/inbox/store/XM") and v["kind"] == "file" and p.endswith(".bin"))
    tamper.n[victim]["data"] = tamper.n[victim]["data"][:-1] + bytes([tamper.n[victim]["data"][-1] ^ 1])
    assert ctl.cmd_install_store(tamper, dict(ENV), "/inbox/store", "/inbox/manifest.json", sha) == 5
    assert not [p for p in tamper.n if p.startswith(STORE + "/")]
    assert ctl.cmd_install_store(tamper, dict(ENV), "/inbox/store", "/inbox/manifest.json", "0" * 64) == 5


# ------------------------------------------------------------------ entrypoint (logica con stub)
# bash NON di login (il wrapper Git\bin\bash.exe avvia una shell di login che azzera il PATH degli stub); su Linux /bin/bash
BASH = next((b for b in (r"C:\Program Files\Git\usr\bin\bash.exe", "/bin/bash", "/usr/bin/bash") if Path(b).exists()), None)


def run_entrypoint(tmp_path, uid, env_extra, ctl_rc):
    stubs = tmp_path / "bin"
    stubs.mkdir(exist_ok=True)
    log = tmp_path / "calls.log"

    def stub(name, body):
        (stubs / name).write_text("#!/bin/sh\n" + body + "\n", newline="\n")

    stub("id", 'echo %d' % uid)
    stub("mkdir", 'echo "mkdir $@" >> "%s"' % log.as_posix())
    stub("chown", 'echo "chown $@" >> "%s"' % log.as_posix())
    stub("find", 'echo "find $@" >> "%s"' % log.as_posix())
    stub("su", 'echo "su AUTH=${NEXUS_CHART_AUTH_FILE:-<unset>} ARGS=$*" >> "%s"' % log.as_posix())
    ctl_stub = tmp_path / "ctl"
    ctl_stub.write_text("#!/bin/sh\necho \"ctl $@\" >> \"%s\"\nexit %d\n" % (log.as_posix(), ctl_rc), newline="\n")
    env = dict(os.environ, PATH=str(stubs) + os.pathsep + os.environ.get("PATH", ""), CHART_AUTHORITY_CTL=ctl_stub.as_posix())
    for k in ("NEXUS_CHART_AUTH_FILE",):
        env.pop(k, None)
    env.update(env_extra)
    stub("appstub", 'echo "app AUTH=${NEXUS_CHART_AUTH_FILE:-<unset>}" >> "%s"' % log.as_posix())
    p = subprocess.run([BASH, str(SERVER / "docker-entrypoint.sh"), "appstub"], env=env, capture_output=True, text=True, timeout=60)
    return p, (log.read_text() if log.exists() else "")


@pytest.mark.skipif(BASH is None, reason="bash non disponibile")
def test_entrypoint_hardened_boot_ok_keeps_authority_path_and_never_does_blanket_chown(tmp_path):
    p, calls = run_entrypoint(tmp_path, 0, {"NEXUS_CHART_AUTH_FILE": AUTH}, 0)
    assert "ctl boot" in calls and "AUTH=" + AUTH in calls and "chown" not in calls and "find" not in calls, calls


@pytest.mark.skipif(BASH is None, reason="bash non disponibile")
@pytest.mark.parametrize("rc", [2, 3, 4, 127])
def test_entrypoint_boot_failure_is_fail_closed_for_chart_only(tmp_path, rc):
    p, calls = run_entrypoint(tmp_path, 0, {"NEXUS_CHART_AUTH_FILE": AUTH}, rc)
    assert "AUTH=" + ctl.DENIED_AUTH_PATH in calls                                  # il Chart riceve un'autorita' inesistente
    assert "su AUTH=" in calls                                                      # il backend parte comunque
    assert "find /data -mindepth 1 -maxdepth 1" in calls and "chart_auth" in calls and "chart_store" in calls    # fallback: i namespace protetti sono esclusi dal chown


@pytest.mark.skipif(BASH is None, reason="bash non disponibile")
def test_entrypoint_without_persistent_authority_keeps_historical_blanket_chown(tmp_path):
    p, calls = run_entrypoint(tmp_path, 0, {}, 0)
    assert "chown -R nexus:nexus /data" in calls and "ctl boot" not in calls and "su AUTH=<unset>" in calls


@pytest.mark.skipif(BASH is None, reason="bash non disponibile")
def test_entrypoint_non_root_with_persistent_authority_is_fail_closed(tmp_path):
    p, calls = run_entrypoint(tmp_path, 1000, {"NEXUS_CHART_AUTH_FILE": AUTH}, 0)
    assert "ctl boot" not in calls and "su " not in calls
    assert "app AUTH=" + ctl.DENIED_AUTH_PATH in calls                              # l'app parte, ma il Chart e' in fail-closed
    assert "non-root" in p.stderr


@pytest.mark.skipif(BASH is None, reason="bash non disponibile")
def test_entrypoint_missing_ctl_is_fail_closed(tmp_path):
    stubs = tmp_path / "bin"
    stubs.mkdir()
    log = tmp_path / "calls.log"
    for name, body in (("id", "echo 0"), ("mkdir", "true"), ("chown", "true"), ("find", 'echo "find $@" >> "%s"' % log.as_posix()), ("su", 'echo "su AUTH=${NEXUS_CHART_AUTH_FILE:-<unset>}" >> "%s"' % log.as_posix())):
        (stubs / name).write_text("#!/bin/sh\n" + body + "\n", newline="\n")
    env = dict(os.environ, PATH=str(stubs) + os.pathsep + os.environ.get("PATH", ""), CHART_AUTHORITY_CTL=(tmp_path / "missing").as_posix(), NEXUS_CHART_AUTH_FILE=AUTH)
    subprocess.run([BASH, str(SERVER / "docker-entrypoint.sh"), "appstub"], env=env, capture_output=True, text=True, timeout=60)
    assert "AUTH=" + ctl.DENIED_AUTH_PATH in log.read_text()


def test_dockerfile_installs_root_owned_entrypoint_outside_app_dir():
    d = (SERVER / "Dockerfile").read_text(encoding="utf-8")
    assert 'ENTRYPOINT ["/usr/local/sbin/docker-entrypoint.sh"]' in d
    assert "COPY server/chart_authority_ctl.py /usr/local/sbin/chart-authority" in d and "chown root:root /usr/local/sbin/docker-entrypoint.sh" in d
    assert "chown -R nexus:nexus /app /data" in d                                     # il layer immagine resta com'era; il confine e' stabilito a runtime


def test_ctl_and_entrypoint_use_lf_line_endings_in_git_attributes():
    ga = (SERVER.parent / ".gitattributes").read_text(encoding="utf-8")
    assert "server/docker-entrypoint.sh text eol=lf" in ga and "server/chart_authority_ctl.py text eol=lf" in ga


# ------------------------------------------------------------------ revisione di sicurezza dei comandi a servizio attivo
def test_verify_boundary_is_read_only_apart_from_the_canary_file():
    fs = protected_fs_with_record()
    fs.lchown("/data/jarvis", 0, 0)                                                # uno stato "sporco" che un boot correggerebbe
    before = fs.snapshot()
    res = ctl.Result(hardened=True)
    ctl.verify_boundary(fs, dict(ENV), APP, probe_ok, DATA, res)
    assert not res.deny
    after = fs.snapshot()
    changed = {p for p in set(before) | set(after) if before.get(p) != after.get(p)}
    assert changed <= {"/data/.chart_boundary_canary/canary.txt"}, changed         # nessuna ownership/permesso modificato (sicuro con l'app in esecuzione)


def test_install_store_reads_each_source_file_once_so_a_swap_after_verification_is_harmless():
    fs = protected_fs_with_record()
    payload = b"A" * 100
    man = {"files": [{"source_relative": "DS/f.bin", "bytes": 100, "sha256": hashlib.sha256(payload).hexdigest()}], "total_bytes": 100}
    fs.add("/inbox", "dir", 10001, 10001, 0o755)
    fs.add("/inbox/DS", "dir", 10001, 10001, 0o755)
    fs.add("/inbox/DS/f.bin", "file", 10001, 10001, 0o644, payload)
    mraw = json.dumps(man).encode()
    fs.add("/meta", "dir", 0, 0, 0o755)
    fs.add("/meta/manifest.json", "file", 0, 0, 0o644, mraw)
    reads = []
    orig = fs.read_bytes

    def spy(path):
        reads.append(path)
        data = orig(path)
        if path == "/inbox/DS/f.bin":
            fs.n[path]["data"] = b"B" * 100                                         # l'app sostituisce il file subito dopo la lettura
        return data
    fs.read_bytes = spy
    assert ctl.cmd_install_store(fs, dict(ENV), "/inbox", "/meta/manifest.json", hashlib.sha256(mraw).hexdigest()) == 0
    assert reads.count("/inbox/DS/f.bin") == 1
    assert orig(STORE + "/DS/f.bin") == payload                                     # installati i byte VERIFICATI, non quelli sostituiti dopo
