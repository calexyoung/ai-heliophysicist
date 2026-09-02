"""One-off tools for the 2012-07-23 extreme CME analysis (user: cayoung).

Paper-specific by design — see users/README.md for the promotion policy.
"""

from helio_agent.registry import tool


@tool(family="measure")
def sta_20120723_summary(file: str) -> dict:
    """Event summary for the 2012-07-23 STEREO-A ICME from the MAGPLASMA CSV.

    One-off: encodes this event's shock-finding convention (first |B| above
    2.5x the 12-20 UT background on Jul 23). Not general — for other events
    use the core tools directly.
    """
    import pandas as pd

    df = pd.read_csv(file, index_col="time", parse_dates=True)
    b = df["BTOTAL"]
    pre = b.loc["2012-07-23 12:00":"2012-07-23 20:00"].mean()
    late = b.loc["2012-07-23 20:00":"2012-07-23 23:59"]
    shock = late[late > 2.5 * pre].index[0]
    return {"shock_time": str(shock),
            "pre_event_b_nT": round(float(pre), 1),
            "peak_b_nT": round(float(b.max()), 2),
            "peak_b_time": str(b.idxmax()),
            "r_au": round(float(df["R"].mean()), 4),
            "l2_vp_gap_fraction":
                round(float(df.loc["2012-07-23 12:00":"2012-07-25 12:00",
                                   "Vp"].isna().mean()), 2)}
