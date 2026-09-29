from pathlib import Path

import pytest

from path_resolver import resolve_contracts_dir, resolve_project_root


def test_resolver_supports_flattened_docker_app_layout(tmp_path, monkeypatch):
    monkeypatch.delenv("NEXUS_CONTRACTS_DIR", raising=False)
    app_root = tmp_path / "app"
    module = app_root / "orchestrator_v1" / "core" / "ledger.py"
    module.parent.mkdir(parents=True)
    module.touch()
    contracts = app_root / "contracts"
    contracts.mkdir()
    (contracts / "nexus-event.schema.json").write_text("{}", encoding="utf-8")

    assert resolve_contracts_dir(module) == contracts.resolve()
    assert resolve_project_root(module) == app_root.resolve()
    assert resolve_contracts_dir(module) != Path("/contracts")


def test_explicit_contracts_directory_is_validated(tmp_path, monkeypatch):
    configured = tmp_path / "canonical-contracts"
    configured.mkdir()
    monkeypatch.setenv("NEXUS_CONTRACTS_DIR", str(configured))
    assert resolve_contracts_dir(__file__) == configured.resolve()

    monkeypatch.setenv("NEXUS_CONTRACTS_DIR", str(tmp_path / "missing"))
    with pytest.raises(FileNotFoundError, match="NEXUS_CONTRACTS_DIR"):
        resolve_contracts_dir(__file__)


def test_checkout_resolves_repository_contracts(monkeypatch):
    monkeypatch.delenv("NEXUS_CONTRACTS_DIR", raising=False)
    contracts = resolve_contracts_dir(__file__)
    assert contracts.name == "contracts"
    assert (contracts / "nexus-event.schema.json").is_file()
