"""Offline tests for timezone handling in merge_series.

Workspace CSVs are naive UTC by convention, but HAPI servers return offset
timestamps, so a model series can arrive tz-aware. pandas refuses to join a
tz-aware index to a naive one — that is what turned a routine
model-vs-observation merge into a hand-edit on 2026-09-04.
"""

import pandas as pd
import pytest

from helio_agent.registry import run_tool
from helio_agent.tools.reduce import to_naive_utc
from helio_agent.workspace import data_path


def write(name, index, **cols):
    df = pd.DataFrame(cols, index=pd.DatetimeIndex(index, name="time"))
    p = data_path(name)
    df.to_csv(p, index_label="time")
    return str(p)


def test_to_naive_utc_leaves_naive_alone():
    df = pd.DataFrame({"a": [1.0]}, index=pd.DatetimeIndex(["2024-05-11 02:00"]))
    out, from_tz = to_naive_utc(df)
    assert from_tz is None
    assert out.index.tz is None
    assert out.index[0] == pd.Timestamp("2024-05-11 02:00")


def test_to_naive_utc_strips_utc():
    df = pd.DataFrame({"a": [1.0]},
                      index=pd.DatetimeIndex(["2024-05-11 02:00+00:00"]))
    out, from_tz = to_naive_utc(df)
    assert from_tz == "UTC"
    assert out.index.tz is None
    assert out.index[0] == pd.Timestamp("2024-05-11 02:00")


def test_to_naive_utc_converts_a_non_utc_zone_rather_than_reinterpreting():
    """A +02:00 stamp is 2 hours EARLIER in UTC. Dropping the offset without
    converting would silently shift the series."""
    df = pd.DataFrame({"a": [1.0]},
                      index=pd.DatetimeIndex(["2024-05-11 04:00+02:00"]))
    out, from_tz = to_naive_utc(df)
    assert out.index[0] == pd.Timestamp("2024-05-11 02:00")
    assert from_tz is not None


def test_merge_joins_tz_aware_with_naive_on_the_right_timestamps():
    naive = write("_tz_naive.csv", ["2024-05-11 01:00", "2024-05-11 02:00"],
                  obs=[-300.0, -436.0])
    aware = write("_tz_aware.csv",
                  ["2024-05-11 01:00+00:00", "2024-05-11 02:00+00:00"],
                  model=[-220.0, -308.0])
    r = run_tool("merge_series", files=[naive, aware], out_name="_tz_merged.csv")
    assert r["status"] == "ok", r.get("error")
    df = pd.read_csv(r["file"], index_col=0, parse_dates=True)
    assert list(df.columns) == ["obs", "model"]
    assert len(df) == 2
    row = df.loc[pd.Timestamp("2024-05-11 02:00")]
    assert row["obs"] == -436.0 and row["model"] == -308.0


def test_merge_reports_every_conversion():
    naive = write("_tz_naive2.csv", ["2024-05-11 01:00"], obs=[1.0])
    aware = write("_tz_aware2.csv", ["2024-05-11 01:00+00:00"], model=[2.0])
    r = run_tool("merge_series", files=[naive, aware], out_name="_tz_merged2.csv")
    assert len(r["tz_normalized"]) == 1
    assert r["tz_normalized"][0]["file"] == "_tz_aware2.csv"
    assert "naive UTC" in r["note"]


def test_merge_says_nothing_when_nothing_was_converted():
    a = write("_tz_n1.csv", ["2024-05-11 01:00"], x=[1.0])
    b = write("_tz_n2.csv", ["2024-05-11 01:00"], y=[2.0])
    r = run_tool("merge_series", files=[a, b], out_name="_tz_merged3.csv")
    assert r["tz_normalized"] == [] and r["note"] is None


def test_merge_refuses_duplicate_columns():
    a = write("_tz_d1.csv", ["2024-05-11 01:00"], dst=[1.0])
    b = write("_tz_d2.csv", ["2024-05-11 01:00"], dst=[2.0])
    r = run_tool("merge_series", files=[a, b], out_name="_tz_merged4.csv")
    assert r["status"] == "error"
    assert "dst" in r["error"] and "rename upstream" in r["error"]


def test_merge_refuses_an_empty_file_list():
    r = run_tool("merge_series", files=[], out_name="_tz_merged5.csv")
    assert r["status"] == "error"
    assert "at least one file" in r["error"]


@pytest.mark.parametrize("how", ["outer", "inner"])
def test_merge_respects_join_mode_across_timezones(how):
    naive = write("_tz_j1.csv", ["2024-05-11 01:00", "2024-05-11 02:00"],
                  obs=[1.0, 2.0])
    aware = write("_tz_j2.csv", ["2024-05-11 02:00+00:00"], model=[9.0])
    r = run_tool("merge_series", files=[naive, aware], how=how,
                 out_name=f"_tz_merged_{how}.csv")
    df = pd.read_csv(r["file"], index_col=0, parse_dates=True)
    assert len(df) == (2 if how == "outer" else 1)
