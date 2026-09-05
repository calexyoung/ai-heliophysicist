"""Offline tests for detect_icme on planted solar-wind CSVs.

Mirrors helio-agent's test_detect_icme: an hourly window with a planted
shock, sheath and cold ejecta carrying a smooth field rotation.
"""

import math

import pytest

from helio_agent.registry import run_tool
from helio_agent.tools.icme import expected_temperature_k

AMBIENT_V, ICME_V, HOURS = 400.0, 700.0, 96
ICME_ROWS = range(40, 65)  # 2024-05-11T16 .. 2024-05-12T16 (24 h)
SHEATH_ROWS = range(30, 40)


def _stamp(i):
    day, hour = divmod(i, 24)
    return f"2024-05-{10 + day:02d}T{hour:02d}:00:00"


def _plant(path, *, icme_rows=ICME_ROWS, cold_rows=(), sheath_rows=(),
           sheath_bz=-20.0, angle_fn=None):
    lines = ["time,V,N,T,BY,BZ"]
    for i in range(HOURS):
        inside, in_sheath = i in icme_rows, i in sheath_rows
        v = ICME_V if (inside or in_sheath) else AMBIENT_V
        if inside:
            t = 0.2 * expected_temperature_k(v)
        elif i in cold_rows:
            t = 0.3 * expected_temperature_k(v)
        else:
            t = expected_temperature_k(v)
        if in_sheath:
            by, bz = 2.0, sheath_bz
        elif inside and angle_fn is not None:
            th = math.radians(angle_fn(list(icme_rows).index(i), len(icme_rows)))
            by, bz = 15.0 * math.sin(th), 15.0 * math.cos(th)
        else:
            by, bz = (2.0 if i % 2 else -2.0), 2.0
        # A sheath is COMPRESSED plasma: density and field both step up
        # behind the shock. The planted sheath needs that, or it is not a
        # shock at all and the detector is right to reject it — which is how
        # the ejecta-driven fixture used to sneak past a speed-only test.
        n = 15.0 if in_sheath else (10.0 if inside else 5.0)
        lines.append(f"{_stamp(i)},{v},{n},{t:.0f},{by:.3f},{bz:.3f}")
    path.write_text("\n".join(lines) + "\n")
    return str(path)


def smooth(k, n):
    return -80.0 + 160.0 * k / (n - 1)


def southward(k, n):
    return 100.0 + 160.0 * k / (n - 1)


def ragged(k, n):
    return 60.0 if k % 2 else -60.0


def _run(file, **kw):
    kw.setdefault("plot", False)
    # density_column matters: the shock test wants compression in plasma or
    # field, and a sheath whose Bz is deliberately weak has only the density
    # to show it.
    kw.setdefault("density_column", "N")
    return run_tool("detect_icme", file=file, speed_column="V", temperature_column="T",
                    by_column="BY", bz_column="BZ", **kw)


def test_finds_planted_magnetic_cloud(tmp_path):
    out = _run(_plant(tmp_path / "w.csv", angle_fn=smooth))
    assert out["status"] == "ok" and out["n_intervals"] == 1
    icme = out["icme"]
    assert icme["start"].startswith("2024-05-11 16") and icme["end"].startswith("2024-05-12 16")
    assert icme["duration_hours"] == 24.0
    assert abs(icme["min_temp_ratio"] - 0.2) < 0.01
    assert icme["mean_speed_kms"] == ICME_V
    assert icme["magnetic_cloud"] is True
    assert 150.0 <= icme["rotation_deg"] <= 170.0 and icme["rotation_r2"] > 0.95
    assert icme["max_b_perp_nT"] == 15.0
    assert out["shock_time"].startswith("2024-05-11 16")
    assert "magnetic cloud" in out["note"]


def test_quiet_wind_finds_nothing(tmp_path):
    out = _run(_plant(tmp_path / "q.csv", icme_rows=()))
    assert out["icme"] is None and out["n_intervals"] == 0 and out["shock_time"] is None
    assert out["closest"]["start"] is None
    assert out["closest"]["min_temp_ratio"] == pytest.approx(1.0, abs=0.01)
    assert out["closest"]["ratio_short"] == pytest.approx(0.5, abs=0.01)
    assert "no ICME signature" in out["note"]


def test_short_dip_reports_near_miss_and_relaxed_gate_finds_it(tmp_path):
    f = _plant(tmp_path / "s.csv", icme_rows=range(40, 44))  # 3 h
    out = _run(f)
    assert out["icme"] is None
    c = out["closest"]
    assert c["duration_hours"] == 3.0 and c["hours_short"] == 3.0
    assert c["min_temp_ratio"] == pytest.approx(0.2, abs=0.01)
    assert "3 h short" in out["note"]
    found = _run(f, min_hours=2.5)
    assert found["icme"]["duration_hours"] == 3.0 and found["closest"] is None


def test_ragged_field_is_not_a_cloud(tmp_path):
    out = _run(_plant(tmp_path / "r.csv", angle_fn=ragged))
    assert out["icme"]["magnetic_cloud"] is False and out["icme"]["rotation_r2"] < 0.5
    assert "no flux-rope signature" in out["note"]


def test_shock_gates_cold_slow_wind(tmp_path):
    out = _run(_plant(tmp_path / "c.csv", cold_rows=range(5, 26), angle_fn=smooth))
    assert out["shock_time"].startswith("2024-05-11 16") and out["n_intervals"] == 1
    assert out["icme"]["start"].startswith("2024-05-11 16")
    assert "pre-shock cold-slow-wind interval(s) ignored" in out["note"]


def test_without_field_skips_cloud_check(tmp_path):
    f = _plant(tmp_path / "n.csv", angle_fn=smooth)
    out = run_tool("detect_icme", file=f, speed_column="V", temperature_column="T", plot=False)
    assert out["icme"]["magnetic_cloud"] is None and "check skipped" in out["note"]


def test_sheath_driven_storm_is_flagged(tmp_path):
    out = _run(_plant(tmp_path / "sh.csv", sheath_rows=SHEATH_ROWS, angle_fn=smooth))
    assert out["shock_time"].startswith("2024-05-11 06")
    assert out["sheath"]["start"] == out["shock_time"]
    assert out["sheath"]["end"] == out["icme"]["start"]
    assert out["sheath"]["duration_hours"] == 10.0
    assert out["sheath"]["field"]["bz_min_nT"] == -20.0
    assert out["driver"] == "sheath" and "SHEATH-DRIVEN" in out["note"]


def test_ejecta_credited_when_it_carries_the_field(tmp_path):
    out = _run(_plant(tmp_path / "ej.csv", sheath_rows=SHEATH_ROWS, sheath_bz=-0.5,
                      angle_fn=southward))
    assert out["driver"] == "ejecta" and "ejecta-driven" in out["note"]


def test_bad_column_refuses(tmp_path):
    f = _plant(tmp_path / "b.csv")
    out = run_tool("detect_icme", file=f, speed_column="nope", temperature_column="T")
    assert out["status"] == "error" and "nope" in out["error"]
    out = run_tool("detect_icme", file=f, speed_column="V", temperature_column="T",
                   by_column="BY")
    assert out["status"] == "error"


def test_plot_written(tmp_path, monkeypatch):
    from helio_agent import workspace
    monkeypatch.setattr(workspace, "output_path", lambda n: tmp_path / n)
    monkeypatch.setattr("helio_agent.tools.icme.output_path", lambda n: tmp_path / n)
    out = _run(_plant(tmp_path / "p.csv", angle_fn=smooth), plot=True)
    assert (tmp_path / "icme.png").read_bytes().startswith(b"\x89PNG")
