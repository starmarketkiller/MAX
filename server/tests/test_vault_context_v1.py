"""NEXUS_LOCAL_OPERATOR_BOOTSTRAP_V1 Phase 4 - vault_context.py. Uses the
real vault/ and .claude/skills/ directories already in this repo (no
synthetic fixtures for namespace selection - this is read-only, and the
real content is what proves the stopword/scoring fix actually works), plus
isolated tmp_path fixtures for the pure top_k/empty-query edge cases."""
from pathlib import Path

from jarvis_v1 import vault_context as vc


def test_vault_root_resolves_to_real_vault_directory():
    assert vc.vault_root().is_dir()
    assert (vc.vault_root() / "01-Trading").is_dir()


def test_query_terms_strips_stopwords_and_short_tokens():
    terms = vc._query_terms("quali sono le decisioni di funding recenti?")
    assert "funding" in terms
    assert "decisioni" in terms
    assert "quali" not in terms
    assert "sono" not in terms
    assert "di" not in terms  # sotto MIN_TERM_LENGTH


def test_empty_query_selects_no_namespace():
    assert vc.select_namespace("") is None
    assert vc.build_context_pack("")["notes"] == []


def test_funding_query_selects_revenue_namespace_not_trading():
    # Bug reale corretto in questa sessione: senza lo stopword filter e con
    # punteggio per frequenza invece che per presenza distinta, questa query
    # selezionava TRADING (cartella molto piu' grande) invece di REVENUE
    # (l'unica cartella che menziona davvero "funding").
    assert vc.select_namespace("quali sono le decisioni di funding recenti?") == "REVENUE"


def test_skill_query_selects_skills_namespace():
    namespace = vc.select_namespace("che skill MQL5 esistono per l'engineering?")
    assert namespace == "SKILLS"


def test_build_context_pack_never_exceeds_top_k():
    pack = vc.build_context_pack("NEXUS EA strategia trading", top_k=2)
    assert len(pack["notes"]) <= 2


def test_build_context_pack_notes_have_required_shape():
    pack = vc.build_context_pack("funding opportunity")
    for note in pack["notes"]:
        assert set(note) == {"title", "source", "snippet"}
        assert note["snippet"]
        assert not note["source"].startswith("/")  # path relativo, mai assoluto


def test_search_namespace_on_empty_directory_returns_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(vc, "_namespace_dirs", lambda namespace: [tmp_path / "does-not-exist"])
    assert vc.search_namespace("TRADING", "qualunque cosa") == []


def test_namespace_vault_dirs_match_real_layout_found_in_census():
    # Ancorato alla struttura reale verificata in questa sessione - non
    # cartelle inventate.
    assert vc.NAMESPACE_VAULT_DIRS["DECISIONS"] == ["01-Trading/Decisions"]
    assert (vc.vault_root() / "01-Trading" / "Decisions").is_dir()
    assert vc.NAMESPACE_VAULT_DIRS["TASKS"] == ["01-Trading/TODO"]
    assert (vc.vault_root() / "01-Trading" / "TODO").is_dir()
