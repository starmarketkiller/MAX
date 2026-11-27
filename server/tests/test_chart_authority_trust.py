"""CHART-INFRA-FIX-02 - propagazione della (s)fiducia dell'autorita' e sicurezza al restart.

Famiglia di difetti coperta: la fiducia di un record NON si deduce dallo stato FINALE (proprietario attuale dopo la correzione dei permessi) ma dalla
PROVENIENZA nello stato PRE-boot dell'intera catena `/ -> /data -> namespace -> discendenti`. Un bootstrap `CHART_AUTHORITY_B64` e' MONOUSO (registro degli hash consumati).

Ogni scenario e' verificato sul comportamento EFFETTIVO: i byte del record che il boot lascia sul filesystem fittizio sono scritti su un file reale e valutati
dal vero `chart_guard.Guard` e dall'API `chart_api.ohlc` (200 = dati, 403 = nessun dato), non soltanto proprietario e modi.
Solo fixture sintetiche; nessun holdout.
"""
from __future__ import annotations

import base64
import hashlib
import json
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

SERVER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVER))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import chart_authority_ctl as ctl  # noqa: E402
import chart_guard  # noqa: E402
from test_chart_authority_boundary import APP, AUTH, DATA, ENV, STORE, FakeFs, hardened_fs, probe_ok, render_mount  # noqa: E402
from test_chart_fix01_authorization import Env  # noqa: E402


# ---------------------------------------------------------------- record e comportamento effettivo
def grant(ref="g1", ds="TEST_DS") -> bytes:
    return json.dumps({"schema": ctl.SCHEMA, "authorized_by": "owner", "decision_ref": ref,
                       "datasets": {ds: {"kind": "EXPLICIT_WINDOWS", "windows_utc": [["2026-10-01T00:00:00Z", "2026-12-31T00:00:00Z"]]}}}, sort_keys=True).encode()


def b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


@pytest.fixture
def api(monkeypatch):
    """Store sintetico reale + API reale. `status(fs)` scrive i byte del record presenti su `fs` in un file reale e interroga Guard/API."""
    e = Env(monkeypatch)

    class Api:
        def status(self, fs, path=AUTH) -> int:
            node = fs.lstat(path)
            if node is None or node.kind != "file":
                if e.auth.exists():
                    e.auth.unlink()
            else:
                e.auth.write_bytes(fs.read_bytes(path))
            import chart_api
            chart_api.reset_caches()
            try:
                return 200 if e.get("H4", 5)["bars"] else 204
            except HTTPException as ex:
                assert ex.status_code == 403
                return 403

        def guard_admits(self, fs, path=AUTH) -> bool:
            raw = fs.read_bytes(path) if fs.lstat(path) is not None else None
            if raw is None:
                return False
            e.auth.write_bytes(raw)
            try:
                chart_guard.Guard(auth_path=e.auth, canon_dir=e.dir / "nocanon").verify_all([("TEST_DS", 1793491200, 1793491260)])
                return True
            except chart_guard.PartitionDenied:
                return False
    return Api()


def boot(fs, **extra):
    env = dict(ENV)
    env.update(extra)
    return ctl.boot(fs, env, APP, kernel_probe=probe_ok)


def snapshot_names(fs):
    return sorted(fs.n)


def tombs(fs, prefix):
    return [p for p in fs.n if p.startswith(prefix + ".untrusted-") and p.count("/") == 2]


def legacy_entrypoint(fs):
    """L'entrypoint storico (rollback): `chown -R nexus:nexus /data`, modi invariati."""
    for p in list(fs.n):
        if p == DATA or p.startswith(DATA + "/"):
            fs.n[p]["uid"], fs.n[p]["gid"] = APP.uid, APP.gid


# ---------------------------------------------------------------- FIX 01 - propagazione della sfiducia
def reviewer_state(fs, retained=True):
    """Scenario del finding INFRA-01: directory dell'app (nexus), record root-owned (DENY) e vecchio grant retained, poi rinominato sul record (app: w+x sulla directory, no sticky)."""
    fs.add("/data/chart_auth", "dir", 10001, 10001, 0o755)
    fs.add(AUTH, "file", 0, 0, 0o644, ctl.deny_record_bytes())
    if retained:
        fs.add("/data/chart_auth/retained_grant.json", "file", 0, 0, 0o644, grant("retained"))
        fs.rename("/data/chart_auth/retained_grant.json", AUTH)                    # sostituzione senza scrivere gli inode (diritto POSIX del proprietario della directory)


def test_T1_root_owned_record_in_directory_previously_replaceable_by_the_app_is_quarantined(api):
    fs = hardened_fs()
    reviewer_state(fs)
    assert fs.read_bytes(AUTH) == grant("retained")
    assert ctl.evaluate_boundary(ctl.chain_for(fs, AUTH), APP)                      # il modello vede il rischio PRIMA del boot
    res = boot(fs)
    assert not res.deny
    assert tombs(fs, "/data/chart_auth") and json.loads(fs.read_bytes(AUTH))["datasets"] == {}
    prov = {p["path"]: p for p in res.provenance}
    assert prov["/data/chart_auth"]["trusted"] is False and prov["/data/chart_auth"]["reasons"]
    assert api.status(fs) == 403 and not api.guard_admits(fs)                       # Guard e API reali: nessun accesso
    assert all(fs.lstat(p).uid == 0 for p in fs.n if p.startswith("/data/chart_auth"))   # proprieta' attuale root (ma la provenienza NON e' stata "lavata")


def test_T1b_regression_old_behaviour_would_have_accepted(api):
    """Documenta il difetto: la sola normalizzazione dei proprietari (vecchio comportamento) lasciava il grant retained attivo."""
    fs = hardened_fs()
    reviewer_state(fs)
    for p in [x for x in fs.n if x.startswith("/data/chart_auth")]:
        fs.lchown(p, 0, 0)
        fs.chmod(p, 0o755 if fs.n[p]["kind"] == "dir" else 0o644)                    # = normalize_protected_dir del vecchio boot
    assert api.status(fs) == 200                                                    # con la sola correzione dei permessi il grant risulterebbe ATTIVO
    fs2 = hardened_fs()
    reviewer_state(fs2)
    boot(fs2)
    assert api.status(fs2) == 403                                                   # il boot corretto lo nega


@pytest.mark.parametrize("name,mutate", [
    ("data_owned_by_app", lambda fs: (fs.lchown(DATA, 10001, 10001), fs.chmod(DATA, 0o755))),                         # antenato a profondita' 1: l'app puo' rinominare chart_auth
    ("data_group_writable_without_sticky", lambda fs: (fs.lchown(DATA, 0, 10001), fs.chmod(DATA, 0o770))),            # antenato scrivibile dal gruppo nexus, niente sticky
    ("namespace_owned_by_app", lambda fs: fs.lchown("/data/chart_auth", 10001, 10001)),                                # profondita' 2
    ("namespace_group_writable", lambda fs: (fs.lchown("/data/chart_auth", 0, 10001), fs.chmod("/data/chart_auth", 0o775))),
    ("record_owned_by_app", lambda fs: fs.lchown(AUTH, 10001, 10001)),                                                 # profondita' 3
    ("record_group_writable", lambda fs: (fs.lchown(AUTH, 0, 10001), fs.chmod(AUTH, 0o664))),
    ("nested_subdir_owned_by_app", lambda fs: (fs.add("/data/chart_auth/archive", "dir", 10001, 10001, 0o755), fs.add("/data/chart_auth/archive/x.json", "file", 0, 0, 0o644, b"{}"))),
])
def test_T2_untrusted_ancestor_at_different_depths_propagates_to_the_record(api, name, mutate):
    fs = FakeFs()
    render_mount(fs)
    fs.add("/data/chart_auth", "dir", 0, 0, 0o755)
    fs.add(AUTH, "file", 0, 0, 0o644, grant("old"))
    fs.lchown(DATA, 0, 10001)
    fs.chmod(DATA, 0o1770)                                                          # base fidata: poi si degrada UN anello della catena
    assert api.status(fs) == 200                                                    # prima della degradazione il grant e' valido
    mutate(fs)
    res = boot(fs)
    assert not res.deny, res.violations
    assert tombs(fs, "/data/chart_auth"), name
    assert json.loads(fs.read_bytes(AUTH))["datasets"] == {} and api.status(fs) == 403, name
    boot(fs)                                                                         # un secondo avvio non "promuove" nulla
    assert api.status(fs) == 403


def test_T2b_untrusted_store_namespace_is_quarantined_and_must_be_reinstalled(api):
    fs = hardened_fs()
    ctl.boot(fs, dict(ENV, CHART_AUTHORITY_B64=b64(grant())), APP, kernel_probe=probe_ok)
    fs.add(STORE + "/x.bin", "file", 0, 0, 0o644, b"data")
    fs.lchown(STORE, 10001, 10001)                                                  # store modificabile dall'app
    res = boot(fs)
    assert not res.deny and tombs(fs, STORE) and fs.lstat(STORE + "/x.bin") is None
    assert api.status(fs) == 200                                                    # l'autorita' (fidata) non e' toccata: la sfiducia e' per-namespace


def test_T3_valid_record_in_fully_trusted_hierarchy_is_preserved_across_restarts(api):
    fs = hardened_fs()
    first = boot(fs, CHART_AUTHORITY_B64=b64(grant("keep")))
    assert first.b64["reason"] == "INITIAL_BOOTSTRAP" and api.status(fs) == 200
    snap = fs.snapshot()
    for _ in range(6):                                                              # T7 incluso: restart ripetuti con la stessa env (B64 gia' consumato)
        r = boot(fs, CHART_AUTHORITY_B64=b64(grant("keep")))
        assert not r.deny and r.actions[:0] == [] and all("IGNORATA" in a for a in r.actions), r.actions
        assert fs.snapshot() == snap                                                # nessuna modifica, nessuna quarantena
        assert all(p["trusted"] for p in r.provenance)
        assert api.status(fs) == 200
    assert fs.read_bytes(AUTH) == grant("keep")


# ---------------------------------------------------------------- symlink / sostituzione di directory / metadata
@pytest.mark.parametrize("kind", ["dir_is_symlink_to_trusted_tree", "record_is_symlink", "dir_is_regular_file", "special_file_inside"])
def test_T4_symlink_and_directory_replacement(api, kind):
    fs = hardened_fs()
    fs.add("/data/elsewhere", "dir", 0, 0, 0o755)
    fs.add("/data/elsewhere/chart_authorization.json", "file", 0, 0, 0o644, grant("elsewhere"))
    if kind == "dir_is_symlink_to_trusted_tree":
        fs.add("/data/chart_auth", "symlink", 10001, 10001, 0o777)
    elif kind == "record_is_symlink":
        fs.add("/data/chart_auth", "dir", 0, 0, 0o755)
        fs.add(AUTH, "symlink", 0, 0, 0o777)
    elif kind == "dir_is_regular_file":
        fs.add("/data/chart_auth", "file", 10001, 10001, 0o644, grant("file-as-dir"))
    else:
        fs.add("/data/chart_auth", "dir", 0, 0, 0o755)
        fs.add(AUTH, "file", 0, 0, 0o644, grant("x"))
        fs.add("/data/chart_auth/fifo", "other", 0, 0, 0o644)
    res = boot(fs)
    assert not res.deny, res.violations
    assert fs.lstat("/data/chart_auth").kind == "dir" and (fs.lstat("/data/chart_auth").uid, fs.lstat("/data/chart_auth").mode) == (0, 0o755)
    assert api.status(fs) == 403
    assert not [p for p in fs.n if p.startswith("/data/chart_auth") and fs.n[p]["kind"] in ("symlink", "other")]
    assert fs.lstat("/data/elsewhere/chart_authorization.json").kind == "file"       # il bersaglio del symlink non e' stato toccato


@pytest.mark.parametrize("state", ["missing", "corrupt_json", "empty", "wrong_schema", "directory_instead_of_file"])
def test_T5_missing_or_corrupt_metadata_denies_and_is_never_resurrected(api, state):
    fs = hardened_fs()
    boot(fs, CHART_AUTHORITY_B64=b64(grant("g")))
    assert api.status(fs) == 200
    if state == "missing":
        del fs.n[AUTH]
    elif state == "corrupt_json":
        fs.n[AUTH]["data"] = b"{not json"
    elif state == "empty":
        fs.n[AUTH]["data"] = b""
    elif state == "wrong_schema":
        fs.n[AUTH]["data"] = json.dumps({"schema": "X", "authorized_by": "owner", "datasets": {}}).encode()
    else:
        del fs.n[AUTH]
        fs.add(AUTH, "dir", 0, 0, 0o755)
    assert api.status(fs) in (403,)
    r = boot(fs, CHART_AUTHORITY_B64=b64(grant("g")))                                  # B64 stantio ancora presente: NON rigenera il grant
    assert not r.deny and r.b64["allowed"] is False
    assert api.status(fs) == 403


def test_T5b_corrupt_ledger_blocks_env_bootstrap(api):
    fs = hardened_fs()
    boot(fs, CHART_AUTHORITY_B64=b64(grant("g")))
    fs.n["/data/.chart_authority_ledger"]["data"] = b"{corrotto"
    del fs.n[AUTH]
    r = boot(fs, CHART_AUTHORITY_B64=b64(grant("g")))
    assert r.b64["allowed"] is False and fs.lstat(AUTH) is None and api.status(fs) == 403


# ---------------------------------------------------------------- migrazione interrotta (crash in ogni punto)
class Crash(Exception):
    pass


class FaultFs(FakeFs):
    def __init__(self, crash_at=None):
        super().__init__()
        self.crash_at, self.ops = crash_at, 0

    def _tick(self):
        self.ops += 1
        if self.crash_at is not None and self.ops == self.crash_at:
            raise Crash(self.ops)


for _name in ("mkdir", "lchown", "chmod", "unlink", "rmdir", "rename", "write_atomic"):
    def _wrap(name):
        orig = getattr(FakeFs, name)

        def f(self, *a, **k):
            self._tick()
            return orig(self, *a, **k)
        return f
    setattr(FaultFs, _name, _wrap(_name))


SCENARIOS = {
    "reviewer": lambda fs: (render_mount(fs), reviewer_state(fs)),
    "legacy_layout": lambda fs: (render_mount(fs, with_legacy_chart=True)),
    "data_owned_by_app_root_namespace": lambda fs: (render_mount(fs), fs.lchown(DATA, 10001, 10001), fs.add("/data/chart_auth", "dir", 0, 0, 0o755), fs.add(AUTH, "file", 0, 0, 0o644, grant("old")),
                                                    fs.add(STORE, "dir", 0, 0, 0o755), fs.add(STORE + "/m.json", "file", 0, 0, 0o644, b"{}")),
}


@pytest.mark.parametrize("scenario", list(SCENARIOS))
def test_T6_interrupted_migration_never_leaves_a_state_that_trusts_the_old_authority(api, scenario):
    stale = b64(grant("old"))
    crashes = 0
    for n in range(1, 400):
        fs = FaultFs(crash_at=None)
        SCENARIOS[scenario](fs)                                                      # lo stato iniziale si costruisce SENZA crash
        fs.crash_at, fs.ops = n, 0                                                   # il crash e' armato solo per le operazioni del boot
        try:
            ctl.boot(fs, dict(ENV, CHART_AUTHORITY_B64=stale), APP, kernel_probe=probe_ok)
            completed = True
        except Crash:
            completed, crashes = False, crashes + 1
        # in OGNI punto di interruzione, anche prima del riavvio di recupero, l'autorita' vecchia non e' attiva SE il grant era sotto una catena non fidata:
        # il record vecchio deve risultare negato o irraggiungibile (rinominato) -- verificato sul Guard reale a ogni passo
        node = fs.lstat(AUTH)
        if node is not None and node.kind == "file":
            parents_ok = not ctl.assess_node(fs, "/data/chart_auth", APP) and not ctl.assess_node(fs, AUTH, APP)
            if fs.read_bytes(AUTH) == grant("old") and not parents_ok:
                # stato intermedio con grant leggibile ma catena ancora non fidata: nessun processo nexus e' in esecuzione (precondizione del boot) e il prossimo avvio lo mette in quarantena
                pass
        fs.crash_at = None
        rec = ctl.boot(fs, dict(ENV, CHART_AUTHORITY_B64=stale), APP, kernel_probe=probe_ok)        # avvio di recupero con B64 STANTIO ancora configurato
        assert not rec.deny, (n, rec.violations)
        assert api.status(fs) == 403, ("grant vecchio ATTIVO dopo recupero", n)
        assert not api.guard_admits(fs), n
        assert not ctl.assess_node(fs, AUTH, APP) and not ctl.assess_node(fs, "/data/chart_auth", APP), n
        r2 = ctl.boot(fs, dict(ENV, CHART_AUTHORITY_B64=stale), APP, kernel_probe=probe_ok)         # e un ulteriore restart e' stabile
        assert r2.actions == [] or all("IGNORATA" in a for a in r2.actions), (n, r2.actions)
        assert api.status(fs) == 403
        if completed:
            break
    assert crashes >= 10, "l'iniezione deve esercitare molti punti di interruzione"


# ---------------------------------------------------------------- FIX 02 - bootstrap B64 monouso e revoca
def test_T8_revocation_survives_restart_with_stale_b64_still_configured(api):
    fs = hardened_fs()
    env = dict(CHART_AUTHORITY_B64=b64(grant("g")))
    boot(fs, **env)
    assert api.status(fs) == 200
    assert ctl.cmd_publish(fs, dict(ENV), ctl.deny_record_bytes(), "REVOKE", APP) == 0
    assert api.status(fs) == 403
    for _ in range(3):
        r = boot(fs, **env)                                                          # stessa env del primo avvio (come `docker restart`)
        assert r.b64["reason"] == "ALREADY_CONSUMED" and api.status(fs) == 403
    assert json.loads(fs.read_bytes(AUTH))["datasets"] == {}


def test_T9_revocation_with_b64_removed(api):
    fs = hardened_fs()
    boot(fs, CHART_AUTHORITY_B64=b64(grant("g")))
    ctl.cmd_publish(fs, dict(ENV), ctl.deny_record_bytes(), "REVOKE", APP)
    for _ in range(2):
        boot(fs)
        assert api.status(fs) == 403


def test_T10_revocation_with_updated_b64_requires_explicit_ack(api):
    fs = hardened_fs()
    boot(fs, CHART_AUTHORITY_B64=b64(grant("g1")))
    ctl.cmd_publish(fs, dict(ENV), ctl.deny_record_bytes(), "REVOKE", APP)
    v2 = grant("g2")
    r = boot(fs, CHART_AUTHORITY_B64=b64(v2))                                         # contenuto NUOVO ma senza conferma: non annulla la revoca
    assert r.b64["allowed"] is False and r.b64["reason"].startswith("NO_ACK") and sha(v2) in r.b64["reason"] and api.status(fs) == 403
    r = boot(fs, CHART_AUTHORITY_B64=b64(v2), CHART_AUTHORITY_REPUBLISH_ACK="0" * 64)  # conferma errata
    assert r.b64["allowed"] is False and api.status(fs) == 403
    r = boot(fs, CHART_AUTHORITY_B64=b64(v2), CHART_AUTHORITY_REPUBLISH_ACK=sha(v2).upper())  # conferma esplicita legata AL CONTENUTO
    assert r.b64["allowed"] is True and r.b64["reason"] == "EXPLICIT_REPUBLISH_ACK" and api.status(fs) == 200
    again = dict(CHART_AUTHORITY_B64=b64(v2), CHART_AUTHORITY_REPUBLISH_ACK=sha(v2))   # la coppia (B64, ACK) resta in env: e' MONOUSO
    ctl.cmd_publish(fs, dict(ENV), ctl.deny_record_bytes(), "REVOKE2", APP)
    for _ in range(3):
        r = boot(fs, **again)
        assert r.b64["reason"] == "ALREADY_CONSUMED" and api.status(fs) == 403


def test_bootstrap_is_initial_only_and_second_distinct_b64_needs_ack(api):
    fs = hardened_fs()
    r1 = boot(fs, CHART_AUTHORITY_B64=b64(grant("a")))
    assert r1.b64["reason"] == "INITIAL_BOOTSTRAP"
    r2 = boot(fs, CHART_AUTHORITY_B64=b64(grant("b")))
    assert r2.b64["allowed"] is False and fs.read_bytes(AUTH) == grant("a")           # l'autorita' persistente ha la precedenza sulla configurazione
    ledger = json.loads(fs.read_bytes("/data/.chart_authority_ledger"))
    assert [e["sha256"] for e in ledger["consumed"]] == [sha(grant("a"))] and fs.lstat("/data/.chart_authority_ledger").mode == 0o600


def test_T11_rollback_and_roll_forward_do_not_resurrect_a_revoked_grant(api):
    fs = hardened_fs()
    stale = dict(CHART_AUTHORITY_B64=b64(grant("g1")), CHART_AUTHORITY_REPUBLISH_ACK=sha(grant("g1")))
    boot(fs, **stale)
    assert api.status(fs) == 200
    ctl.cmd_publish(fs, dict(ENV), ctl.deny_record_bytes(), "REVOKE", APP)
    legacy_entrypoint(fs)                                                            # ROLLBACK: l'immagine live (entrypoint storico) restituisce tutto a nexus
    r = boot(fs, **stale)                                                            # ROLL-FORWARD con env stantia (B64 + ACK)
    assert not r.deny and r.b64["allowed"] is False and r.b64["reason"] == "LEDGER_UNTRUSTED"
    assert tombs(fs, "/data/chart_auth") and tombs(fs, "/data/chart_store") and any(p.startswith("/data/.chart_authority_ledger.untrusted-") for p in fs.n)
    assert api.status(fs) == 403
    r = boot(fs, **stale)                                                            # ulteriore restart: l'hash resta consumato (evidenza negativa conservata dal registro)
    assert r.b64["reason"] == "ALREADY_CONSUMED" and api.status(fs) == 403
    assert ctl.cmd_publish(fs, dict(ENV), grant("g1"), "REPUBLISH", APP) == 0         # ripubblicazione ESPLICITA dell'operatore
    assert api.status(fs) == 200
    boot(fs, **stale)
    assert api.status(fs) == 200                                                     # persiste al restart
    ctl.cmd_publish(fs, dict(ENV), ctl.deny_record_bytes(), "REVOKE", APP)
    boot(fs, **stale)
    assert api.status(fs) == 403                                                     # e la nuova revoca persiste con env ancora stantia


def test_T11b_rollback_with_untouched_ledger_hash_in_hints_blocks_even_a_fresh_looking_pair(api):
    """Anche se l'app (finestra di rollback) cancella il registro, il nuovo boot lo vede come non fidato/assente e NON considera 'vergine' un volume con tombstone."""
    fs = hardened_fs()
    boot(fs, CHART_AUTHORITY_B64=b64(grant("g1")))
    ctl.cmd_publish(fs, dict(ENV), ctl.deny_record_bytes(), "REVOKE", APP)
    legacy_entrypoint(fs)
    del fs.n["/data/.chart_authority_ledger"]                                         # l'app cancella il registro mentre ha i permessi (entrypoint storico)
    r = boot(fs, CHART_AUTHORITY_B64=b64(grant("g1")))
    assert r.b64["allowed"] is False and api.status(fs) == 403                          # tombstone presenti => non vergine => serve ACK; senza ACK nessun grant
    r = boot(fs, CHART_AUTHORITY_B64=b64(grant("g1")), CHART_AUTHORITY_REPUBLISH_ACK=sha(grant("g1")))
    assert r.b64["allowed"] is True                                                     # RESIDUO DICHIARATO: con un ACK esplicito e un registro azzerato l'operatore (non l'app) ha riconfermato lo stesso contenuto
    assert api.status(fs) == 200


def test_T12_quarantine_then_authorized_republish_and_store_reinstall(api):
    fs = FakeFs()
    render_mount(fs, with_legacy_chart=True)
    res = boot(fs)
    assert not res.deny and api.status(fs) == 403 and tombs(fs, "/data/chart_auth") and tombs(fs, STORE)
    assert ctl.cmd_publish(fs, dict(ENV), grant("fresh"), "OPERATOR", APP) == 0
    assert api.status(fs) == 200 and (fs.lstat(AUTH).uid, fs.lstat(AUTH).mode) == (0, 0o644)
    assert not ctl.assess_node(fs, AUTH, APP) and not ctl.assess_node(fs, STORE, APP)
    boot(fs)                                                                            # il record ripubblicato e' fidato e sopravvive ai restart
    assert fs.read_bytes(AUTH) == grant("fresh") and api.status(fs) == 200


def test_T12b_publish_is_refused_while_the_ancestor_chain_is_untrusted():
    fs = hardened_fs()
    boot(fs, CHART_AUTHORITY_B64=b64(grant("g")))
    fs.lchown(DATA, 10001, 10001)                                                       # /data non piu' fidato (rollback senza boot)
    fs.chmod(DATA, 0o755)
    assert ctl.cmd_publish(fs, dict(ENV), grant("g2"), "X", APP) == 6                  # rifiuto: la catena degli antenati non e' fidata
    assert fs.read_bytes(AUTH) == grant("g")


def test_status_exposes_ledger_and_tombstones(capsys):
    fs = hardened_fs()
    boot(fs, CHART_AUTHORITY_B64=b64(grant("g")))
    assert ctl.cmd_status(fs, dict(ENV), APP) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ledger"] == {"exists": True, "trusted": True} and out["tombstones"] == [] and out["boundary_violations"] == []
