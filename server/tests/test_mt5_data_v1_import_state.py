"""Test per import_state.py: IMPORT_NEW/APPEND/RESCAN/SKIPPED_DUPLICATE,
preservazione del raw (sez.15/16/17)."""
from mt5_data_v1 import identity, import_state

ACCOUNT_ID = identity.derive_account_id("import_test_login", "Broker", "Server")


def test_classify_import_new_when_no_previous():
    assert import_state.classify_import(b"abc", None) == import_state.IMPORT_NEW


def test_classify_import_duplicate_when_identical():
    assert import_state.classify_import(b"abc", b"abc") == import_state.SKIPPED_DUPLICATE


def test_classify_import_append_when_prefix_matches():
    assert import_state.classify_import(b"abcdef", b"abc") == import_state.APPEND


def test_classify_import_rescan_when_content_diverges():
    assert import_state.classify_import(b"xyzdef", b"abc") == import_state.RESCAN


def test_classify_import_rescan_when_shorter_than_previous():
    # file piu' corto del precedente non e' un append, anche se e' un prefisso valido al contrario
    assert import_state.classify_import(b"ab", b"abcdef") == import_state.RESCAN


def test_import_raw_file_first_time_is_new(tmp_path):
    root = tmp_path / "data"
    source = tmp_path / "source.csv"
    source.write_text("header\nrow1\n", encoding="utf-8")

    entry = import_state.import_raw_file(root, ACCOUNT_ID, source)
    assert entry["import_mode"] == import_state.IMPORT_NEW

    from mt5_data_v1 import account_package
    raw_copy = account_package.raw_dir(root, ACCOUNT_ID) / "source.csv"
    assert raw_copy.exists()
    assert raw_copy.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")


def test_import_raw_file_duplicate_does_not_rewrite(tmp_path):
    root = tmp_path / "data"
    source = tmp_path / "source.csv"
    source.write_text("header\nrow1\n", encoding="utf-8")

    import_state.import_raw_file(root, ACCOUNT_ID, source)
    entry2 = import_state.import_raw_file(root, ACCOUNT_ID, source)
    assert entry2["import_mode"] == import_state.SKIPPED_DUPLICATE


def test_import_raw_file_append_detected(tmp_path):
    root = tmp_path / "data"
    source = tmp_path / "source.csv"
    source.write_text("header\nrow1\n", encoding="utf-8")
    import_state.import_raw_file(root, ACCOUNT_ID, source)

    source.write_text("header\nrow1\nrow2\n", encoding="utf-8")
    entry2 = import_state.import_raw_file(root, ACCOUNT_ID, source)
    assert entry2["import_mode"] == import_state.APPEND

    from mt5_data_v1 import account_package
    raw_copy = account_package.raw_dir(root, ACCOUNT_ID) / "source.csv"
    assert raw_copy.read_text(encoding="utf-8") == "header\nrow1\nrow2\n"


def test_import_raw_file_rescan_when_content_changes_without_prefix(tmp_path):
    root = tmp_path / "data"
    source = tmp_path / "source.csv"
    source.write_text("header\nrow1\n", encoding="utf-8")
    import_state.import_raw_file(root, ACCOUNT_ID, source)

    source.write_text("completely,different,content\n", encoding="utf-8")
    entry2 = import_state.import_raw_file(root, ACCOUNT_ID, source)
    assert entry2["import_mode"] == import_state.RESCAN
