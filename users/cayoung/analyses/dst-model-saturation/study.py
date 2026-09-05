"""Does the Dst model really saturate on the deepest storms?

The October 2024 analysis observed that `model_dst` missed May 2024's peak by
163 nT and October's by 43.5 nT, and explained it as the O'Brien-McPherron
coupling function saturating outside its calibrated range. That is a causal
claim from TWO events — the same shape as the sheath-driver claim that did not
survive being tested against forty.

So test it the same way. Reuses the storm sample and the cached OMNI 1-min
files from ../sheath-vs-ejecta/ (same declustered peaks of hourly Dst below
-200 nT), runs `model_dst` on each, and asks whether the peak error grows
with storm depth.

    HELIO_AGENT_USER=cayoung uv run python .../study.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SRC = HERE.parent / "sheath-vs-ejecta" / "results.json"
STATE = HERE / "results.json"
sys.path.insert(0, str(ROOT))


def main() -> int:
    from helio_agent.registry import run_tool

    src = json.loads(SRC.read_text())
    st = json.loads(STATE.read_text()) if STATE.exists() else {}

    def R(key, tool, **kw):
        if key in st:
            return st[key]
        print(f"  RUN {key} ({tool})", flush=True)
        r = run_tool(tool, **kw)
        if r.get("status") == "error":
            print(f"     FAIL {str(r.get('error'))[:90]}", flush=True)
        st[key] = r
        STATE.write_text(json.dumps(st, indent=1, default=str))
        return r

    storms = [s for s in src["sample"]["events"]
              if int(str(s["time"])[:4]) >= 1995]
    print(f"{len(storms)} storms from 1995 on")

    rows = []
    for n, s in enumerate(storms, 1):
        tag = str(s["time"])[:10].replace("-", "")
        omni = src.get(f"omni_{tag}", {})
        if not omni.get("file"):
            continue
        print(f"[{n}/{len(storms)}] {s['time'][:16]} Dst {s['value']:.0f}",
              flush=True)
        # model_dst wants hourly input; the cached OMNI is 1-min.
        h = R(f"hourly_{tag}", "resample_series", file=omni["file"],
              cadence="1h", out_name=f"dstsat_{tag}_1h.csv")
        if not h.get("file"):
            continue
        m = R(f"model_{tag}", "model_dst", file=h["file"],
              v_column="flow_speed", bz_column="BZ_GSM",
              density_column="proton_density", dst_column="SYM_H")
        if m.get("status") != "ok":
            continue
        sk = m.get("skill") or {}
        rows.append({
            "time": str(s["time"]), "dst_hourly_kyoto": s["value"],
            "obs_min": sk.get("obs_min_nT"),
            "model_min": m.get("model_min_nT"),
            "min_error": sk.get("min_error_nT"),
            "corr": sk.get("corr"), "rmse": sk.get("rmse_nT"),
        })

    st["_rows"] = rows
    STATE.write_text(json.dumps(st, indent=1, default=str))

    good = [r for r in rows if isinstance(r.get("min_error"), (int, float))
            and isinstance(r.get("obs_min"), (int, float))]
    print(f"\n{len(good)} storms modelled")
    print(f"{'date':12s} {'obs_min':>8s} {'model':>8s} {'err':>7s} "
          f"{'err/depth':>9s} {'corr':>6s}")
    for r in sorted(good, key=lambda x: x["obs_min"]):
        frac = abs(r["min_error"] / r["obs_min"]) if r["obs_min"] else 0
        print(f"{r['time'][:10]:12s} {r['obs_min']:8.0f} {r['model_min']:8.0f} "
              f"{r['min_error']:7.1f} {frac:9.2f} {r['corr']:6.3f}")

    # The claim under test: deeper storms are under-predicted by more.
    for lo, hi, lab in ((-10000, -300, "obs <= -300"),
                        (-300, -250, "-300..-250"),
                        (-250, 0, "shallower than -250")):
        g = [r for r in good if lo <= r["obs_min"] < hi]
        if not g:
            continue
        errs = [r["min_error"] for r in g]
        fracs = [abs(r["min_error"] / r["obs_min"]) for r in g]
        print(f"\n{lab:22s} n={len(g):2d}  median error "
              f"{sorted(errs)[len(errs)//2]:6.1f} nT  "
              f"median error/depth {sorted(fracs)[len(fracs)//2]:.2f}")
    return 0




def symh_vs_dst() -> int:
    """Is the 1-min SYM-H minimum ALWAYS deeper than the hourly Dst minimum?

    The October analysis asserts "Dst is always the shallower number".
    That is a universal claim; test it on the 1-MINUTE SYM-H minima, not on
    hourly means (an hourly mean averages the peak away, which is a different
    comparison and would not test the claim).
    """
    from helio_agent.registry import run_tool

    src = json.loads(SRC.read_text())
    st = json.loads(STATE.read_text()) if STATE.exists() else {}
    out = []
    for s in src["sample"]["events"]:
        if int(str(s["time"])[:4]) < 1995:
            continue
        tag = str(s["time"])[:10].replace("-", "")
        omni = src.get(f"omni_{tag}", {})
        if not omni.get("file"):
            continue
        key = f"symh1m_{tag}"
        if key not in st:
            print(f"  RUN {key}", flush=True)
            st[key] = run_tool("find_extrema", file=omni["file"],
                               column="SYM_H", mode="min")
            STATE.write_text(json.dumps(st, indent=1, default=str))
        r = st[key]
        if r.get("status") != "ok":
            continue
        out.append({"time": str(s["time"]), "dst": s["value"],
                    "symh_1min": r["value"], "diff": r["value"] - s["value"]})
    st["_symh_vs_dst"] = out
    STATE.write_text(json.dumps(st, indent=1, default=str))
    viol = [r for r in out if r["diff"] > 0]
    print(f"\n{len(out)} storms; SYM-H(1-min) deeper than Dst in "
          f"{len(out) - len(viol)}, shallower in {len(viol)}")
    for r in sorted(out, key=lambda x: x["diff"]):
        mark = "  <-- Dst deeper" if r["diff"] > 0 else ""
        print(f"  {r['time'][:10]}  Dst {r['dst']:6.0f}  "
              f"SYM-H {r['symh_1min']:7.1f}  diff {r['diff']:6.1f}{mark}")
    return 0


if __name__ == "__main__":
    import sys as _s
    raise SystemExit(symh_vs_dst() if "--symh" in _s.argv else main())
