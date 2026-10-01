from pathlib import Path

from path_provenance import repo_safe_path


def test_repo_path_remains_repo_relative(tmp_path):
    root = tmp_path / "repo"
    source = root / "server" / "artifact.json"
    assert repo_safe_path(source, root) == "server/artifact.json"


def test_external_fixture_is_safe_and_deterministic(tmp_path):
    root = tmp_path / "repo"
    first = tmp_path / "outside-a" / "missing.json"
    second = tmp_path / "outside-b" / "missing.json"
    assert repo_safe_path(first, root) == "external://missing.json"
    assert repo_safe_path(second, root) == "external://missing.json"
    assert str(tmp_path) not in repo_safe_path(first, root)
