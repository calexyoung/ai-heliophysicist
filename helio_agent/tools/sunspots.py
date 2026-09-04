"""Raw per-station sunspot reports from NOAA SWPC (discover).

`get_solar_regions` serves SWPC's **edited** daily region summary: one
authoritative class per region. This serves the **raw station reports** that
feed it — every observatory's independent classification of every region,
about a month deep. Two things that buys:

* **Yesterday's class**, which `flare_probability` needs, because the
  McCloskey et al. (2016) rates are indexed by evolution rather than by a
  single day's class.
* **An honest uncertainty on the class itself.** Observatories disagree far
  more than a single published class suggests: over the month to
  2026-09-04, 65% of (date, region) groups carried more than one McIntosh
  class and 35% more than one Mount Wilson class. The disagreement routinely
  reaches the *Zurich* letter, the only one the flare rates use — on
  2026-09-04, AR 4524 was 'Cso' from SVI and 'Hax' from LEA, which is 18%
  against 5% for a C-class flare. A tool that silently picked one would hide
  a factor-of-three spread.

So consensus here reports the vote, never just the winner: `zurich_votes`,
`zurich_agreement`, and `tie` (with `zurich_consensus` left None) rather than
an arbitrary pick.

Gotchas
-------
* **Two different longitudes per row.** `location` is SWPC's value rotated
  forward to 2400 UT of the observation day; `report_location` is the raw
  measurement, valid at `obs_time`. Matching an image wants
  `report_location` + `obs_time`, which carries no correction to get wrong.
  Fitting one against the other over 389 reports is what pinned SWPC's
  correction epoch at 24.07 h and its rotation rate at 14.50 deg/day.
* Rolling window of roughly one month. Anything older needs a different
  archive; this feed is not history.
* Records with a null `Region` (unnumbered spot groups) are dropped and
  counted in `skipped_unnumbered`.
* `ValidSpotClass` is 0 on the rare bad report; those are excluded.
* `Quality` runs 1-4 and is the station's own confidence, not an accuracy
  measure — `min_quality` is offered but defaults to keeping everything,
  because dropping low-quality reports quietly narrows the disagreement
  this tool exists to expose.
* This is operational, real-time data (contract point 7), and the station
  reports are less processed than the edited summary. For "the" class of a
  region, prefer `get_solar_regions`; use this for history and spread.
"""

from __future__ import annotations

import collections

from helio_agent.http import cached_get
from helio_agent.registry import tool

_FEED = "https://services.swpc.noaa.gov/json/sunspot_report.json"


def _zurich(cls: str | None) -> str | None:
    z = (str(cls or "").strip()[:1] or "").upper()
    return z if z in ("A", "B", "C", "D", "E", "F", "H") else None


def consensus_from_reports(day: str, region_no: int, items: list[dict]) -> dict:
    """Vote the station reports for one region-day into a consensus.

    A tie leaves `zurich_consensus` None rather than picking arbitrarily:
    the two candidate Zurich letters can differ by a factor of three in
    flare probability, so a silent choice would fabricate confidence.
    """
    votes = collections.Counter(
        z for z in (_zurich(i["spot_class"]) for i in items) if z)
    top = votes.most_common()
    tie = len(top) > 1 and top[0][1] == top[1][1]
    winner = None if (tie or not top) else top[0][0]
    n = sum(votes.values())
    return {
        "date": day, "region": region_no, "n_reports": len(items),
        "classes": sorted({i["spot_class"] for i in items}),
        "mag_classes": sorted({i["mag_class"] for i in items if i["mag_class"]}),
        "by_observatory": {i["observatory"]: i["spot_class"] for i in items},
        "zurich_votes": dict(votes),
        "zurich_consensus": winner,
        "zurich_agreement": round(top[0][1] / n, 3) if (top and n) else None,
        "tie": tie,
        "classes_disagree": len({i["spot_class"] for i in items}) > 1,
    }


@tool(family="discover")
def get_sunspot_reports(date: str | None = None, region: int | None = None,
                        min_quality: int = 0) -> dict:
    """Raw per-observatory sunspot classifications from SWPC (~1 month deep).

    Unlike `get_solar_regions`, which gives SWPC's single edited class per
    region, this returns every station's independent report plus a consensus
    that shows the disagreement instead of hiding it.

    date: 'YYYY-MM-DD' observation date. Defaults to the latest in the feed.
      Pass 'all' for the whole window (needed to walk a region's evolution).
    region: NOAA region number to filter to (e.g. 4524).
    min_quality: drop station reports below this `Quality` (1-4). Default 0
      keeps everything — filtering narrows the observed spread, so it should
      be a deliberate act.

    Returns `dates` (every observation date in the feed), `reports` (the raw
    rows), and `consensus`: one entry per (date, region) with `n_reports`,
    the distinct `classes` and `mag_classes` with their observatories,
    `zurich_votes`, `zurich_consensus` (None on a tie), `zurich_agreement`
    (fraction backing the winner), and `tie`.

    Operational real-time data, and less processed than the edited summary:
    for a region's authoritative class use `get_solar_regions`; use this for
    yesterday's class and for how uncertain today's really is.
    """
    r = cached_get(_FEED, timeout=90, ttl_seconds=1800)
    r.raise_for_status()
    rows = r.json()

    dates = sorted({d["Obsdate"][:10] for d in rows if d.get("Obsdate")})
    if not dates:
        return {"status": "error", "error": "SWPC sunspot feed returned no dated rows"}
    if date in (None, "", "latest"):
        want = {dates[-1]}
    elif date == "all":
        want = set(dates)
    else:
        if date not in dates:
            return {"status": "error",
                    "error": f"{date} is not in the feed, which covers "
                             f"{dates[0]}..{dates[-1]} (a rolling ~1 month "
                             "window). Use 'all', or an archive for older data."}
        want = {date}

    skipped = 0
    kept = []
    for d in rows:
        if d["Obsdate"][:10] not in want:
            continue
        if d.get("Region") is None:
            skipped += 1
            continue
        if not d.get("Spotclass") or d.get("ValidSpotClass") == 0:
            continue
        if min_quality and (d.get("Quality") or 0) < min_quality:
            continue
        if region is not None and int(d["Region"]) != int(region):
            continue
        t = str(d.get("Obstime") or "").zfill(4)
        obs_time = (f"{d['Obsdate'][:10]}T{t[:2]}:{t[2:]}:00Z"
                    if len(t) == 4 and t.isdigit() else None)
        kept.append({
            "date": d["Obsdate"][:10], "region": int(d["Region"]),
            "observatory": d.get("Observatory"), "quality": d.get("Quality"),
            # `location` is SWPC's value rotated forward to 2400 UT of `date`;
            # `report_location` is what the station actually measured, valid at
            # `obs_time`. Use the latter to match an image — it needs no
            # rotation correction, so it cannot be mis-epoched.
            "location": d.get("Location"),
            "report_location": d.get("Report_Location"),
            "obs_time": obs_time,
            "spot_class": d.get("Spotclass"),
            "mag_class": d.get("Magclass"), "area": d.get("Area"),
            "number_spots": d.get("Numspot"),
        })

    groups = collections.defaultdict(list)
    for k in kept:
        groups[(k["date"], k["region"])].append(k)

    consensus = [consensus_from_reports(day, reg, items)
                 for (day, reg), items in sorted(groups.items())]

    n_dis = sum(1 for c in consensus if c["classes_disagree"])
    n_ztie = sum(1 for c in consensus if c["tie"])
    note = (f"{len(kept)} station reports over {len(want)} date(s), "
            f"{len(consensus)} region-days. {n_dis} region-day(s) "
            f"({n_dis / len(consensus):.0%}) have observatories disagreeing on "
            f"the McIntosh class; {n_ztie} disagree at the Zurich letter with "
            "no majority, so zurich_consensus is None there. Operational "
            "real-time station data — the edited summary is get_solar_regions."
            ) if consensus else "no reports matched"

    return {"dates": dates, "coverage": [dates[0], dates[-1]],
            "n_reports": len(kept), "reports": kept, "consensus": consensus,
            "skipped_unnumbered": skipped, "note": note}
