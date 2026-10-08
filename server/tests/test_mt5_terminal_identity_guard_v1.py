"""Test per MT5_TERMINAL_IDENTITY_GUARD_V1 (LocalBridge/nexus_terminal_identity_guard.py).

Nessuna modifica a MQL5/risk/execution/runtime: questo modulo e' puro Python,
non tocca mai un terminale MT5 reale - i test usano solo path finti e un
registro di profili temporaneo.
"""
import json
import sys
import time
from pathlib import Path

import pytest

LOCAL_BRIDGE_DIR = Path(__file__).resolve().parents[2] / "LocalBridge"
sys.path.insert(0, str(LOCAL_BRIDGE_DIR))

import nexus_terminal_identity_guard as guard  # noqa: E402


PROFILES = {
    "schema_version": 1,
    "profiles": {
        "LIVE_TERMINAL": {
            "expected_terminal_path_substring": "MetaTrader 5",
            "expected_data_dir_substring": "MetaQuotes\\Terminal",
            "pinned_terminal_id": None,
            "allowed_operations": ["ping", "restart_mt5", "open_chart", "deploy_files"],
            "forbidden_operations": ["compile_ea"],
        },
        "TESTER_TERMINAL": {
            "expected_terminal_path_substring": "MT5-Tester",
            "expected_data_dir_substring": "MT5-Tester",
            "pinned_terminal_id": None,
            "allowed_operations": ["ping", "compile_ea", "deploy_files"],
            "forbidden_operations": [],
        },
    },
}

LIVE_CFG = {
    "terminal_role": "LIVE_TERMINAL",
    "mt5_path": r"C:\Program Files\MetaTrader 5\terminal64.exe",
    "mql5_experts": r"C:\Users\x\AppData\Roaming\MetaQuotes\Terminal\D0E8209F\MQL5\Experts",
}

TESTER_CFG = {
    "terminal_role": "TESTER_TERMINAL",
    "mt5_path": r"C:\MT5-Tester\terminal64.exe",
    "mql5_experts": r"C:\MT5-Tester\MQL5\Experts",
}


@pytest.fixture(autouse=True)
def _isolated_guard_paths(tmp_path, monkeypatch):
    """Ogni test usa un proprio registro profili e una propria lock dir -
    nessun test tocca i file reali di LocalBridge/, nessuno sporca gli altri."""
    profiles_path = tmp_path / "nexus_terminal_profiles.config.json"
    profiles_path.write_text(json.dumps(PROFILES), encoding="utf-8")
    monkeypatch.setattr(guard, "PROFILES_PATH_OVERRIDE", profiles_path)
    monkeypatch.setattr(guard, "PROFILES_PATH_EXAMPLE", tmp_path / "does_not_exist.json")
    monkeypatch.setattr(guard, "LOCK_DIR", tmp_path / "locks")
    yield


def test_live_profile_correct():
    identity = guard.resolve_and_verify(LIVE_CFG, "ping")
    assert identity.role == "LIVE_TERMINAL"
    assert "MetaTrader 5" in identity.terminal_path
    assert "MetaQuotes" in identity.data_dir


def test_tester_profile_correct():
    identity = guard.resolve_and_verify(TESTER_CFG, "compile_ea")
    assert identity.role == "TESTER_TERMINAL"
    assert "MT5-Tester" in identity.terminal_path


def test_windows_identity_paths_keep_windows_semantics_on_any_host():
    identity = guard.resolve_and_verify(LIVE_CFG, "ping")
    assert identity.terminal_path == r"C:\Program Files\MetaTrader 5\terminal64.exe"
    assert identity.data_dir == r"C:\Users\x\AppData\Roaming\MetaQuotes\Terminal\D0E8209F"
    assert not identity.data_dir.startswith(str(Path.cwd()))


def test_terminal_path_mismatch():
    bad_cfg = dict(LIVE_CFG, mt5_path=r"C:\MT5-Tester\terminal64.exe")
    with pytest.raises(guard.IdentityMismatch, match="mismatch di identita'"):
        guard.resolve_and_verify(bad_cfg, "ping")


def test_data_dir_mismatch():
    bad_cfg = dict(LIVE_CFG, mql5_experts=r"C:\MT5-Tester\MQL5\Experts")
    with pytest.raises(guard.IdentityMismatch, match="data directory"):
        guard.resolve_and_verify(bad_cfg, "ping")


def test_operation_not_allowed_forbidden_list():
    # compile_ea e' esplicitamente in forbidden_operations per LIVE_TERMINAL.
    with pytest.raises(guard.IdentityMismatch, match="non e' consentita"):
        guard.resolve_and_verify(LIVE_CFG, "compile_ea")


def test_operation_not_allowed_not_in_allowlist():
    # "apply_template" non e' nella allowlist di nessuno dei due profili di test.
    with pytest.raises(guard.IdentityMismatch, match="non e' consentita"):
        guard.resolve_and_verify(LIVE_CFG, "apply_template")


def test_tester_operation_not_in_allowlist():
    # TESTER_TERMINAL nel profilo di test consente solo ping/compile_ea/
    # deploy_files - "restart_mt5" non e' autorizzato (non e' in forbidden,
    # ma nemmeno nell'allowlist: deve comunque fallire).
    with pytest.raises(guard.IdentityMismatch, match="non e' consentita"):
        guard.resolve_and_verify(TESTER_CFG, "restart_mt5")


def test_missing_terminal_role_fails_closed():
    cfg = dict(LIVE_CFG)
    cfg.pop("terminal_role")
    with pytest.raises(guard.IdentityMismatch, match="terminal_role"):
        guard.resolve_and_verify(cfg, "ping")


def test_invalid_terminal_role_fails_closed():
    cfg = dict(LIVE_CFG, terminal_role="SOMETHING_ELSE")
    with pytest.raises(guard.IdentityMismatch, match="terminal_role"):
        guard.resolve_and_verify(cfg, "ping")


def test_concurrent_lock_rejection():
    identity = guard.resolve_and_verify(LIVE_CFG, "restart_mt5")
    lock1 = guard.acquire_lock(identity, "restart_mt5")
    try:
        with pytest.raises(guard.LockBusy, match="lock gia' attivo"):
            guard.acquire_lock(identity, "restart_mt5")
    finally:
        guard.release_lock(lock1)


def test_lock_released_allows_next_acquire():
    identity = guard.resolve_and_verify(LIVE_CFG, "restart_mt5")
    lock1 = guard.acquire_lock(identity, "restart_mt5")
    guard.release_lock(lock1)
    lock2 = guard.acquire_lock(identity, "restart_mt5")  # non deve sollevare LockBusy
    guard.release_lock(lock2)


def test_stale_lock_recovery_dead_process():
    # pid palesemente inesistente -> reclaim immediato, indipendentemente
    # dall'eta' (anche appena oltre STALE_LOCK_SEC, non serve HARD).
    identity = guard.resolve_and_verify(LIVE_CFG, "restart_mt5")
    lock_path = guard._lock_path(identity.role)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    stale_age = guard.STALE_LOCK_SEC + 10
    lock_path.write_text(json.dumps({
        "pid": 999999, "ts": time.time() - stale_age, "action": "restart_mt5",
        "role": identity.role, "job_id": "old-job",
    }), encoding="utf-8")

    new_lock = guard.acquire_lock(identity, "restart_mt5", job_id="new-job")
    assert new_lock == lock_path
    recorded = json.loads(new_lock.read_text(encoding="utf-8"))
    assert recorded["job_id"] == "new-job"
    guard.release_lock(new_lock)


def test_alive_process_lock_is_not_reclaimed_even_if_old():
    """Il punto centrale segnalato in review: un lock vecchio ma di un
    processo ANCORA VIVO non deve essere scippato solo per l'eta'. Si usa il
    pid del processo di test stesso (os.getpid()), che e' per definizione
    vivo, con un timestamp oltre STALE_LOCK_SEC ma sotto HARD_STALE_LOCK_SEC."""
    identity = guard.resolve_and_verify(LIVE_CFG, "restart_mt5")
    lock_path = guard._lock_path(identity.role)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    age = guard.STALE_LOCK_SEC + 30
    assert age < guard.HARD_STALE_LOCK_SEC
    lock_path.write_text(json.dumps({
        "pid": guard.os.getpid(), "ts": time.time() - age, "action": "restart_mt5",
        "role": identity.role, "job_id": "slow-but-alive",
    }), encoding="utf-8")

    with pytest.raises(guard.LockBusy, match="vivo=True"):
        guard.acquire_lock(identity, "restart_mt5", job_id="new-job")
    # il lock originale deve restare intatto, non toccato
    recorded = json.loads(lock_path.read_text(encoding="utf-8"))
    assert recorded["job_id"] == "slow-but-alive"


def test_hard_stale_ceiling_overrides_even_alive_process():
    """Valvola di sicurezza: anche un processo vivo perde il lock se l'eta'
    supera HARD_STALE_LOCK_SEC - altrimenti un processo bloccato per sempre
    terrebbe il lock per sempre."""
    identity = guard.resolve_and_verify(LIVE_CFG, "restart_mt5")
    lock_path = guard._lock_path(identity.role)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    age = guard.HARD_STALE_LOCK_SEC + 10
    lock_path.write_text(json.dumps({
        "pid": guard.os.getpid(), "ts": time.time() - age, "action": "restart_mt5",
        "role": identity.role, "job_id": "stuck-forever",
    }), encoding="utf-8")

    new_lock = guard.acquire_lock(identity, "restart_mt5", job_id="new-job")
    assert new_lock == lock_path
    guard.release_lock(new_lock)


def test_pid_is_alive_for_current_process():
    assert guard._pid_is_alive(guard.os.getpid()) is True


def test_pid_is_alive_false_for_bogus_pid():
    assert guard._pid_is_alive(999999) is False


def test_pid_is_alive_false_for_nonpositive_pid():
    assert guard._pid_is_alive(0) is False
    assert guard._pid_is_alive(-1) is False


def test_fresh_lock_is_not_treated_as_stale():
    identity = guard.resolve_and_verify(LIVE_CFG, "restart_mt5")
    lock1 = guard.acquire_lock(identity, "restart_mt5")
    try:
        with pytest.raises(guard.LockBusy):
            guard.acquire_lock(identity, "restart_mt5")
    finally:
        guard.release_lock(lock1)


def test_release_lock_is_idempotent(tmp_path):
    # Rilasciare due volte, o un path None, non deve mai sollevare.
    guard.release_lock(None)
    fake = tmp_path / "nonexistent.lock"
    guard.release_lock(fake)  # non esiste: no-op silenzioso


def test_unknown_role_profile_missing():
    cfg = dict(LIVE_CFG, terminal_role="TESTER_TERMINAL",
               mt5_path=r"C:\Program Files\MetaTrader 5\terminal64.exe")
    # ruolo valido ma path che non corrisponde al profilo TESTER -> mismatch,
    # non un crash
    with pytest.raises(guard.IdentityMismatch):
        guard.resolve_and_verify(cfg, "ping")


def test_missing_profiles_file_fails_closed(monkeypatch, tmp_path):
    monkeypatch.setattr(guard, "PROFILES_PATH_OVERRIDE", tmp_path / "missing1.json")
    monkeypatch.setattr(guard, "PROFILES_PATH_EXAMPLE", tmp_path / "missing2.json")
    with pytest.raises(guard.IdentityMismatch, match="nessun registro"):
        guard.resolve_and_verify(LIVE_CFG, "ping")
