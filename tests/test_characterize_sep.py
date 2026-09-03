"""Offline tests for characterize_sep on planted proton-flux CSVs.

Mirrors helio-agent's test_sep: an hourly window with a triangular >10 MeV
enhancement peaking at 300 pfu (S2) and a >30 MeV channel at 0.1x.
"""

from helio_agent.registry import run_tool
from helio_agent.tools.sep import (
    AU_KM,
    parker_footpoint_lon_deg,
    parker_spiral_length_km,
    proton_speed_km_s,
    s_scale,
)

BACKGROUND = 0.5
PEAK = 300.0
EVENT_ROWS = range(30, 61)  # 2024-05-11T06 .. 2024-05-12T12 (30 h)


def _stamp(i):
    day, hour = divmod(i, 24)
    return f"2024-05-{10 + day:02d}T{hour:02d}:00:00"


def _plant(path, *, event_rows=EVENT_ROWS, second_event=()):
    lines = ["time,P10,P30"]
    for i in range(96):
        if i in event_rows or i in second_event:
            base = event_rows if i in event_rows else second_event
            k, n = list(base).index(i), len(base)
            f10 = 10.0 + (PEAK - 10.0) * (1 - abs(2 * k / (n - 1) - 1))  # triangle
        else:
            f10 = BACKGROUND
        lines.append(f"{_stamp(i)},{f10:.3f},{f10 * 0.1:.3f}")
    path.write_text("\n".join(lines) + "\n")
    return str(path)


def _run(file, **kw):
    kw.setdefault("plot", False)
    return run_tool("characterize_sep", file=file, flux_10mev_column="P10",
                    flux_30mev_column="P30", **kw)


def test_s_scale_ladder():
    assert s_scale(5.0) is None
    assert s_scale(10.0) == "S1"
    assert s_scale(150.0) == "S2"
    assert s_scale(2e3) == "S3"
    assert s_scale(5e4) == "S4"
    assert s_scale(1e5) == "S5"


def test_finds_planted_event(tmp_path):
    out = _run(_plant(tmp_path / "p.csv"))
    assert out["status"] == "ok" and out["n_events"] == 1
    sep = out["sep"]
    assert sep["onset"].startswith("2024-05-11 06") and sep["end"].startswith("2024-05-12 12")
    assert sep["duration_hours"] == 30.0
    assert sep["peak_10mev"]["value"] == PEAK
    assert sep["peak_10mev"]["time"].startswith("2024-05-11 21")
    assert sep["s_scale"] == "S2"  # 300 pfu: at/above 100, below 1000
    assert sep["peak_30mev"]["value"] == round(PEAK * 0.1, 2)
    assert sep["hardness_ratio"] == 0.1
    assert out["cadence_s"] == 3600.0
    assert sep["fluence_10mev"] > PEAK * 3600  # sum(flux) * cadence over the event
    assert "S2 radiation storm" in out["note"]


def test_quiet_fluxes_find_nothing(tmp_path):
    out = _run(_plant(tmp_path / "q.csv", event_rows=()))
    assert out["sep"] is None and out["n_events"] == 0 and out["physics"] is None
    assert "no SEP event" in out["note"]


def test_two_injections_first_is_primary(tmp_path):
    out = _run(_plant(tmp_path / "d.csv", event_rows=range(10, 25),
                      second_event=range(60, 80)))
    assert out["n_events"] == 2
    assert out["sep"]["onset"].startswith("2024-05-10 10")
    assert "first of 2 qualifying events" in out["note"]


def test_gap_merges_decay_dips(tmp_path):
    # two humps 6 h apart merge at the default 12 h gap, split at 3 h
    f = _plant(tmp_path / "g.csv", event_rows=range(10, 20), second_event=range(26, 36))
    assert _run(f)["n_events"] == 1
    assert _run(f, gap_hours=3.0)["n_events"] == 2


def test_physics_constants():
    # 10 MeV protons run at ~0.145c, 30 MeV at ~0.247c — dispersion follows
    assert proton_speed_km_s(10.0) < proton_speed_km_s(30.0)
    assert 0.144 < proton_speed_km_s(10.0) / 299_792.458 < 0.146
    assert 0.246 < proton_speed_km_s(30.0) / 299_792.458 < 0.248
    # the 450 km/s Parker spiral is ~1.14 AU long, footpoint near W55
    assert 1.12 < parker_spiral_length_km(450.0) / AU_KM < 1.15
    assert 54.0 < parker_footpoint_lon_deg(450.0) < 55.5
    # faster wind: straighter spiral, footpoint closer to disk center
    assert parker_footpoint_lon_deg(700.0) < parker_footpoint_lon_deg(450.0)
    assert parker_spiral_length_km(700.0) < parker_spiral_length_km(450.0)


def test_onset_physics_with_flare_context(tmp_path):
    # flare peaks 2 h before the planted onset (05-11T06:00), from W60 —
    # 5.4 deg from the 450 km/s Parker footpoint
    out = _run(_plant(tmp_path / "f.csv"), flare_peak_time="2024-05-11T04:00:00Z",
               flare_class="X2.0", flare_lon_deg=60.0)
    ph = out["physics"]
    assert ph is not None
    assert ph["onset_delay_hours"] == 2.0
    # free-streaming 10 MeV expectation ~0.95 h (spiral transit - light travel)
    assert 0.9 < ph["expected_delay_hours_10mev"] < 1.0
    assert ph["expected_delay_hours_30mev"] < ph["expected_delay_hours_10mev"]
    # planted >30 MeV channel is 0.1x the >10 — both cross at the same sample
    assert ph["onset_30mev"] == out["sep"]["onset"]
    assert ph["dispersion_minutes"] == 0.0
    assert ph["connection_angle_deg"] == 5.4
    assert ph["well_connected"] is True
    assert "X2.0 flare" in out["note"] and "well connected" in out["note"]


def test_naive_and_aware_flare_times_agree(tmp_path):
    f = _plant(tmp_path / "tz.csv")
    a = _run(f, flare_peak_time="2024-05-11T04:00:00Z", flare_lon_deg=60.0)["physics"]
    b = _run(f, flare_peak_time="2024-05-11T04:00:00", flare_lon_deg=60.0)["physics"]
    assert a == b and a["onset_delay_hours"] == 2.0


def test_bad_flare_time_refuses_by_name(tmp_path):
    out = _run(_plant(tmp_path / "bad.csv"), flare_peak_time="last Tuesday")
    assert out["status"] == "error"
    assert "flare_peak_time" in out["error"] and "last Tuesday" in out["error"]


def test_bad_column_refuses(tmp_path):
    f = _plant(tmp_path / "c.csv")
    out = run_tool("characterize_sep", file=f, flux_10mev_column="nope", plot=False)
    assert out["status"] == "error" and "nope" in out["error"]


def test_all_fill_refuses(tmp_path):
    p = tmp_path / "fill.csv"
    p.write_text("time,P10\n" + "\n".join(f"{_stamp(i)}," for i in range(24)) + "\n")
    out = run_tool("characterize_sep", file=str(p), flux_10mev_column="P10", plot=False)
    assert out["status"] == "error" and "all fill" in out["error"]


def test_plot_written(tmp_path, monkeypatch):
    monkeypatch.setattr("helio_agent.tools.sep.output_path", lambda n: tmp_path / n)
    out = _run(_plant(tmp_path / "plot.csv"), plot=True,
               flare_peak_time="2024-05-11T04:00:00Z")
    assert out["file"].endswith("sep.png")
    assert (tmp_path / "sep.png").read_bytes().startswith(b"\x89PNG")
    assert out["artifacts"] == [out["file"]]
