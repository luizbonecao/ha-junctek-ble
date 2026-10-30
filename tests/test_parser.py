"""Tests for the Junctek protocol decoder (no Home Assistant needed)."""

import importlib.util
import pathlib

_spec = importlib.util.spec_from_file_location(
    "parser",
    pathlib.Path(__file__).parents[1] / "custom_components/junctek_ble/parser.py",
)
parser = importlib.util.module_from_spec(_spec)
import sys
sys.modules["parser"] = parser
_spec.loader.exec_module(parser)


def frame(*parts: bytes) -> bytes:
    return b"\xbb" + b"".join(parts) + b"\xee"


def test_basic_values():
    p = parser.JunctekParser(capacity_ah=30)
    p.feed(frame(bytes.fromhex("1234C0"), bytes.fromhex("0523C1"), bytes.fromhex("6470D8")))
    s = p.state.as_dict()
    assert s["voltage"] == 12.34
    # direction not reported yet -> unknown, never a guessed sign
    assert s["current"] is None
    assert s["power"] is None
    assert s["status"] is None
    p.feed(frame(bytes.fromhex("00D1")))
    s = p.state.as_dict()
    assert s["current"] == -5.23
    assert s["power"] == -64.7
    assert s["status"] == "discharging"


def test_direction_and_soc():
    p = parser.JunctekParser(capacity_ah=30)
    p.feed(frame(bytes.fromhex("01D1"), bytes.fromhex("0300C1"), bytes.fromhex("025500D2")))
    s = p.state.as_dict()
    assert s["current"] == 3.0
    assert s["remaining_ah"] == 25.5
    assert s["soc"] == 85.0
    assert s["status"] == "charging"


def test_counters_infer_direction():
    p = parser.JunctekParser()
    p.feed(frame(bytes.fromhex("0200C1"), bytes.fromhex("001000D3"), bytes.fromhex("002000D4")))
    p.feed(frame(bytes.fromhex("002100D4")))  # charged counter grew
    assert p.state.charging is True
    p.feed(frame(bytes.fromhex("001001D3")))  # discharged counter grew
    assert p.state.charging is False


def test_split_frames_temperature_time():
    p = parser.JunctekParser()
    data = frame(bytes.fromhex("0125D9"), bytes.fromhex("0090D6"))
    for i in range(len(data)):  # one byte per notification
        p.feed(data[i : i + 1])
    assert p.state.temperature == 25.0
    assert p.state.minutes_left == 90.0


def test_garbage_outside_frame_ignored():
    p = parser.JunctekParser()
    assert p.feed(bytes.fromhex("1234C0")) is False
    assert p.state.voltage is None


def test_soc_clamped():
    p = parser.JunctekParser(capacity_ah=10)
    p.feed(frame(bytes.fromhex("020000D2")))
    assert p.state.soc == 100.0


def test_idle_without_direction():
    p = parser.JunctekParser()
    p.feed(frame(bytes.fromhex("0002C1")))
    assert p.state.status == "idle"
    assert p.state.current == 0.0
