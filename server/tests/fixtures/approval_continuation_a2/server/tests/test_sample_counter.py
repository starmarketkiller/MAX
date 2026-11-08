"""Behavioral contract for the small-file experiment. Written before any model call."""
import importlib.util
from pathlib import Path


def _load():
    path = Path(__file__).resolve().parents[2] / "protocol_a_fixture" / "sample_counter.py"
    spec = importlib.util.spec_from_file_location("sample_counter", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_next_value_advances():
    assert _load().next_value(2) == 3


def test_next_value_from_zero_does_not_raise():
    assert _load().next_value(0) == 1
