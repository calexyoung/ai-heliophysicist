"""Offline tests for radio_bursts on planted dynamic spectra.

Mirrors helio-agent's test_radio: 12 log-spaced channels (20 kHz to 10 MHz)
at 3-min cadence with a broadband fast-drifting type III and a slow
4-channel type II lane drifting down over an hour.
"""

import math

import pytest

from helio_agent.registry import run_tool
from helio_agent.tools.radio import channel_frequency, leblanc_density, radius_for_frequency

CENTERS = [20000, 35188, 61909, 108921, 191634, 337159, 593192, 1043654,
           1836189, 3230563, 5683804, 10000000]
N_ROWS = 100  # 5 h at 3 min


def _stamp(i):
    m = 30 + 180 * i
    return f"2024-05-10T{m // 3600:02d}:{(m % 3600) // 60:02d}:{m % 60:02d}"


def _plant(path, *, typeiii=True, typeii=True, channels=CENTERS):
    n = len(channels)
    rows = [[0.0] * n for _ in range(N_ROWS)]
    if typeiii:
        # row 10: all channels bright; row 11: only the low half — a downward
        # centroid jump across 3 min = electron-beam speed
        for j in range(n):
            rows[10][j] = 25.0
        for j in range(n // 2):
            rows[11][j] = 20.0
    if typeii:
        # rows 40..60 (60 min): a 4-channel lane sliding down one channel
        # every 5 rows, from channels 7-10 to 3-6
        for k, r in enumerate(range(40, 61)):
            top = 10 - k // 5
            for j in range(top - 3, top + 1):
                rows[r][j] = 15.0
    header = "time," + ",".join(f"c{c:g}" for c in channels)
    lines = [header] + [f"{_stamp(i)}," + ",".join(f"{v:.2f}" for v in row)
                        for i, row in enumerate(rows)]
    path.write_text("\n".join(lines) + "\n")
    return str(path)


def _run(file, **kw):
    kw.setdefault("plot", False)
    kw.setdefault("min_channels", 4)
    return run_tool("radio_bursts", file=file, **kw)


def test_leblanc_inversion_roundtrip():
    for f_hz in (30e3, 200e3, 1e6, 10e6):
        r = radius_for_frequency(f_hz)
        assert 8.98 * math.sqrt(leblanc_density(r)) == pytest.approx(f_hz / 1e3, rel=1e-3)
    # lower frequency = lower density = farther out
    assert radius_for_frequency(50e3) > radius_for_frequency(1e6)


def test_channel_names_parse():
    assert channel_frequency("c268") == 268.0
    assert channel_frequency("c1.009e+07") == 1.009e7
    assert channel_frequency("10000000") == 1e7
    assert channel_frequency("E_Average_3") == 3.0  # anonymous index, not a frequency
    assert channel_frequency("flow_speed") is None


def test_classifies_typeiii_and_typeii(tmp_path):
    out = _run(_plant(tmp_path / "w.csv"))
    assert out["status"] == "ok" and out["n_bursts"] == 2
    typeiii, typeii = out["bursts"]
    assert typeiii["classification"] == "type III"
    assert typeiii["inferred_speed_km_s"] > 5000
    assert typeiii["freq_max_hz"] == 10_000_000 and typeiii["peak_db"] == 25.0
    assert typeii["classification"] == "type II candidate"
    assert 200 <= typeii["inferred_speed_km_s"] <= 5000
    assert typeii["duration_minutes"] == 60.0 and typeii["n_samples"] == 21
    assert out["counts"] == {"type III": 1, "type II candidate": 1}
    assert "2 radio bursts" in out["note"]


def test_quiet_window_finds_nothing(tmp_path):
    out = _run(_plant(tmp_path / "q.csv", typeiii=False, typeii=False))
    assert out["n_bursts"] == 0 and out["counts"] == {}
    assert "no radio bursts" in out["note"]


def test_default_channel_gate_keeps_only_the_broadband_burst(tmp_path):
    # the second type III row lights only 6 channels, so one active sample remains
    out = _run(_plant(tmp_path / "g.csv"), min_channels=8)
    assert out["n_bursts"] == 1
    assert out["bursts"][0]["classification"] == "type III (impulsive)"


def test_single_sample_broadband_is_impulsive(tmp_path):
    f = _plant(tmp_path / "i.csv", typeii=False)
    # drop the second type III row by demanding 8 channels: one active sample
    out = _run(f, min_channels=8)
    b = out["bursts"][0]
    assert b["classification"] == "type III (impulsive)"
    assert b["duration_minutes"] == 0.0 and b["inferred_speed_km_s"] is None


def test_gap_splits_bursts(tmp_path):
    out = _run(_plant(tmp_path / "s.csv"), gap_minutes=2.0)
    # the two type III rows (3 min apart) split, and the 21-sample type II
    # lane fragments into 21 single samples
    assert out["n_bursts"] == 2 + 21


def test_min_freq_excludes_low_channels(tmp_path):
    f = _plant(tmp_path / "m.csv")
    out = _run(f, min_freq_hz=2e6)
    assert out["n_channels"] == 3
    bad = _run(f, min_freq_hz=1e9)
    assert bad["status"] == "error" and "excludes every channel" in bad["error"]


def test_non_spectrogram_refuses(tmp_path):
    p = tmp_path / "flat.csv"
    p.write_text("time,flow_speed,T\n2024-05-10T00:00:00,400,1e5\n")
    out = run_tool("radio_bursts", file=str(p), plot=False)
    assert out["status"] == "error" and "fetch_cdaweb_spectrogram" in out["error"]


def test_fill_is_ignored(tmp_path):
    f = _plant(tmp_path / "fill.csv", typeii=False)
    lines = open(f).read().splitlines()
    fixed = [lines[0]] + [",".join("-1e31" if c == "0.00" else c for c in ln.split(","))
                          for ln in lines[1:]]
    open(f, "w").write("\n".join(fixed) + "\n")
    out = _run(f)
    assert out["n_bursts"] == 1 and out["bursts"][0]["classification"] == "type III"


def test_plot_written(tmp_path, monkeypatch):
    monkeypatch.setattr("helio_agent.tools.radio.output_path", lambda n: tmp_path / n)
    out = _run(_plant(tmp_path / "p.csv"), plot=True)
    assert (tmp_path / "radio_bursts.png").read_bytes().startswith(b"\x89PNG")
    assert out["artifacts"] == [out["file"]]
