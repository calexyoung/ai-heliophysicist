"""Per-region flare probability from the McIntosh classification (measure).

SWPC publishes flare probabilities for the **whole disk** only
(`/json/solar_probabilities.json`); there is no per-region feed. Per-region
numbers therefore have to be computed, and the method here is the historical
one: look up a sunspot group's 24-hour flaring *rate* by its McIntosh class,
then turn that rate into a probability with Poisson statistics.

Rates come from **McCloskey, Gallagher and Bloomfield (2016), Solar Physics
291, 1711 (arXiv:1607.00903), Table 5** — 24-hour flaring rates for sunspot
groups within +/-75 deg heliographic longitude, binned by the group's
*modified Zurich* class yesterday and today. Probability of at least one
flare in the window is the Poisson complement::

    P(>=1 flare) = 1 - exp(-rate * hours / 24)

Two properties of that table drive the whole design. It is indexed by
**evolution** — a (starting class -> ending class) pair, not a single class —
which is the paper's actual result: a group that grew H -> D flares at 0.89
per 24 h against 0.68 for one that was already D. And it resolves only the
**Zurich** component, the first of McIntosh's three letters.

Honest limits, all repeated in the result's `caveats`
--------------------------------------------------
* **All three McIntosh letters are read, but from three separate tables.**
  The source gives Zurich (Table 5), penumbral (Table 7) and compactness
  (Table 9) rates independently — three *marginal* distributions over the
  same groups, not three factors of a joint one. Multiplying them would be
  unfounded, so `components` reports each on its own and `component_span`
  gives the range they imply. `probability` remains the Zurich value.
* **The components can disagree by an order of magnitude.** 'Hax' spans
  4-43% for >=C1.0 (Zurich H says 5%, penumbral A says 43%); 'Hsx' spans
  4-13%. That is the honest content of marginal tables, and it is why
  'Hax' and 'Hsx' now separate at all. A single full-McIntosh number needs
  the **joint 60-class table** (Bornmann & Shaw 1994, Sol. Phys. 150, 127),
  which is not openly available — SpaceWeatherLive appears to use one, and
  quotes 25% for Hax against 10% for Hsx, the same ordering the penumbral
  component gives here.
* **Climatology, not a forecast.** These are historical averages over a class,
  carrying no knowledge of the region in front of you — not its magnetic
  complexity, not its shear, and *not its recent flaring*. A region that just
  produced an M flare gets the same number as a quiet region of the same
  class. SWPC's forecasters use all of that, which is why their whole-disk
  number will not equal the combination of these.
* **Calibrated within +/-75 deg longitude.** Pass `lon_deg` and a region
  beyond that is flagged: it sits outside the sample the rates were built
  from, and foreshortening means its class is unreliable anyway.
* **The uncertainties are large and asymmetric in effect.** Several cells are
  0.00 +/- 1.00 — a single-group bin. Those come back with
  `well_sampled: False` rather than a confident zero.
* Mount Wilson / Hale class is not used at all. A delta configuration is the
  single strongest predictor of a big flare and this method cannot see it.
"""

from __future__ import annotations

import math

from helio_agent.registry import tool

# Modified Zurich classes, in the column/row order of the source table.
_ZURICH = ("A", "B", "H", "C", "D", "E", "F")
_PENUMBRAL = ("X", "R", "S", "A", "H", "K")
_COMPACT = ("X", "O", "I", "C")

# McIntosh is a 3-letter class Zpc. The source tabulates each component
# separately (Tables 5, 7, 9) — three MARGINAL distributions over the same
# groups, not three independent factors of a joint one. They are reported
# side by side here and never multiplied; see `component_rates`.
_COMPONENTS = (("zurich", 0, _ZURICH), ("penumbral", 1, _PENUMBRAL),
               ("compactness", 2, _COMPACT))

_CITATION = ("McCloskey, Gallagher & Bloomfield 2016, Sol. Phys. 291, 1711, "
             "Table 5 (arXiv:1607.00903)")

# (rate, uncertainty) in flares per 24 h, keyed [flare level][starting class]
# then indexed by ending class in _ZURICH order. None = no groups in that bin.
_RATES_ZUR = {
    "C": {
        "A": ((0.02, 0.04), (0.09, 0.05), (0.03, 0.18), (0.25, 0.09), (0.82, 0.17), None, (0, 1)),
        "B": ((0.03, 0.04), (0.1, 0.03), (0.06, 0.17), (0.25, 0.05), (0.65, 0.08), None, None),
        "H": ((0.01, 0.08), (0.09, 0.1), (0.05, 0.03), (0.23, 0.05), (0.89, 0.13), (1.44, 0.33), (3.5, 0.71)),
        "C": ((0.03, 0.09), (0.14, 0.05), (0.05, 0.05), (0.2, 0.02), (0.66, 0.04), (1.18, 0.15), (0.88, 0.35)),
        "D": ((0, 0.33), (0.08, 0.12), (0.06, 0.24), (0.21, 0.04), (0.68, 0.02), (1.38, 0.05), (2.67, 0.29)),
        "E": (None, (0, 0.45), (0.2, 0.45), (0.2, 0.1), (0.84, 0.07), (1.41, 0.03), (2.32, 0.09)),
        "F": (None, (0, 1), None, (0.09, 0.3), (1.62, 0.28), (1.52, 0.11), (2.43, 0.05)),
    },
    "M": {
        "A": ((0, 0.04), (0, 0.05), (0, 0.18), (0, 0.09), (0.15, 0.17), None, (0, 1)),
        "B": ((0, 0.04), (0.01, 0.03), (0.03, 0.17), (0.01, 0.05), (0.1, 0.08), None, None),
        "H": ((0, 0.08), (0, 0.1), (0.01, 0.03), (0.03, 0.05), (0.22, 0.13), (0.22, 0.33), (0, 0.71)),
        "C": ((0, 0.09), (0.02, 0.05), (0.01, 0.05), (0.02, 0.02), (0.12, 0.04), (0.25, 0.15), (0.12, 0.35)),
        "D": ((0, 0.33), (0.01, 0.12), (0, 0.24), (0.02, 0.04), (0.11, 0.02), (0.3, 0.05), (0.83, 0.29)),
        "E": (None, (0, 0.45), (0, 0.45), (0.05, 0.1), (0.14, 0.07), (0.32, 0.03), (0.61, 0.09)),
        "F": (None, (0, 1), None, (0, 0.3), (0.08, 0.28), (0.33, 0.11), (0.65, 0.05)),
    },
    "X": {
        "A": ((0, 0.04), (0, 0.05), (0, 0.18), (0, 0.09), (0.03, 0.17), None, (0, 1)),
        "B": ((0, 0.04), (0, 0.03), (0, 0.17), (0, 0.05), (0, 0.08), None, None),
        "H": ((0, 0.08), (0, 0.1), (0, 0.03), (0, 0.05), (0.02, 0.13), (0, 0.33), (0, 0.71)),
        "C": ((0, 0.09), (0, 0.05), (0, 0.05), (0, 0.02), (0.01, 0.04), (0, 0.15), (0, 0.35)),
        "D": ((0, 0.33), (0, 0.12), (0, 0.24), (0, 0.04), (0.01, 0.02), (0.03, 0.05), (0, 0.29)),
        "E": (None, (0, 0.45), (0, 0.45), (0.01, 0.1), (0.01, 0.07), (0.03, 0.03), (0.05, 0.09)),
        "F": (None, (0, 1), None, (0, 0.3), (0, 0.28), (0.03, 0.11), (0.07, 0.05)),
    },
}


# Penumbral class of the largest spot (McIntosh's 2nd letter), Table 7.
_RATES_PEN = {
    "C": {
        "X": ((0.07, 0.02), (0.16, 0.06), (0.34, 0.07), (0.59, 0.06), None, None),
        "R": ((0.08, 0.05), (0.05, 0.07), (0.32, 0.08), (0.49, 0.08), None, None),
        "S": ((0.09, 0.06), (0.19, 0.07), (0.14, 0.02), (0.45, 0.04), (0.38, 0.2), (1.3, 0.22)),
        "A": ((0.11, 0.07), (0.14, 0.08), (0.22, 0.04), (0.56, 0.02), (0.82, 0.19), (1.8, 0.07)),
        "H": (None, None, (0.29, 0.2), (0.24, 0.17), (0.39, 0.09), (1.13, 0.12)),
        "K": (None, None, (0.36, 0.3), (0.81, 0.07), (1.02, 0.13), (2.01, 0.03)),
    },
    "M": {
        "X": ((0, 0.02), (0.01, 0.06), (0.02, 0.07), (0.08, 0.06), None, None),
        "R": ((0.01, 0.05), (0, 0.07), (0.02, 0.08), (0.11, 0.08), None, None),
        "S": ((0.01, 0.06), (0.01, 0.07), (0.01, 0.02), (0.09, 0.04), (0, 0.2), (0.2, 0.22)),
        "A": ((0.02, 0.07), (0.02, 0.08), (0.03, 0.04), (0.09, 0.02), (0.18, 0.19), (0.36, 0.07)),
        "H": (None, None, (0, 0.2), (0.06, 0.17), (0.05, 0.09), (0.33, 0.12)),
        "K": (None, None, (0.09, 0.3), (0.11, 0.07), (0.11, 0.13), (0.52, 0.03)),
    },
    "X": {
        "X": ((0, 0.02), (0, 0.06), (0.01, 0.07), (0, 0.06), None, None),
        "R": ((0, 0.05), (0, 0.07), (0, 0.08), (0, 0.08), None, None),
        "S": ((0, 0.06), (0, 0.07), (0, 0.02), (0, 0.04), (0, 0.2), (0, 0.22)),
        "A": ((0, 0.07), (0, 0.08), (0, 0.04), (0, 0.02), (0.04, 0.19), (0.05, 0.07)),
        "H": (None, None, (0, 0.2), (0, 0.17), (0, 0.09), (0.01, 0.12)),
        "K": (None, None, (0, 0.3), (0.01, 0.07), (0, 0.13), (0.05, 0.03)),
    },
}

# Compactness of the interior spot distribution (3rd letter), Table 9.
_RATES_COM = {
    "C": {
        "X": ((0.04, 0.02), (0.23, 0.03), (0.5, 0.41), (2, 1)),
        "O": ((0.04, 0.03), (0.32, 0.01), (1.55, 0.05), (2.67, 0.33)),
        "I": ((0, 0.71), (0.73, 0.05), (1.64, 0.03), (3.29, 0.13)),
        "C": (None, (3.67, 0.58), (1.58, 0.14), (3.86, 0.08)),
    },
    "M": {
        "X": ((0, 0.02), (0.03, 0.03), (0, 0.41), (0, 1)),
        "O": ((0.01, 0.03), (0.04, 0.01), (0.3, 0.05), (0.67, 0.33)),
        "I": ((0, 0.71), (0.11, 0.05), (0.35, 0.03), (1.07, 0.13)),
        "C": (None, (0.67, 0.58), (0.48, 0.14), (1.41, 0.08)),
    },
    "X": {
        "X": ((0, 0.02), (0, 0.03), (0, 0.41), (0, 1)),
        "O": ((0, 0.03), (0, 0.01), (0.03, 0.05), (0.11, 0.33)),
        "I": ((0, 0.71), (0, 0.05), (0.03, 0.03), (0.07, 0.13)),
        "C": (None, (0, 0.58), (0.08, 0.14), (0.19, 0.08)),
    },
}

def zurich_class(mcintosh: str | None) -> str | None:
    """First letter of a McIntosh class, if it is a valid modified Zurich class."""
    if not mcintosh:
        return None
    z = str(mcintosh).strip()[:1].upper()
    return z if z in _ZURICH else None


def poisson_probability(rate_per_day: float, hours: float) -> float:
    """P(at least one event) for a Poisson process of `rate_per_day` over `hours`."""
    return 1.0 - math.exp(-max(rate_per_day, 0.0) * hours / 24.0)


_TABLES = {"zurich": None, "penumbral": None, "compactness": None}


def mcintosh_letters(cls: str | None) -> tuple[str | None, str | None, str | None]:
    """'Hax' -> ('H', 'A', 'X'). Each letter validated against its own alphabet."""
    t = str(cls or "").strip().upper()
    z = t[0] if len(t) > 0 and t[0] in _ZURICH else None
    p = t[1] if len(t) > 1 and t[1] in _PENUMBRAL else None
    c = t[2] if len(t) > 2 and t[2] in _COMPACT else None
    return z, p, c


def component_rates(mcintosh: str, previous: str | None, level: str) -> dict:
    """Per-component (rate, sigma) for one flare level.

    Returns one entry per McIntosh letter that parses, each looked up in its
    own evolution table with its own previous letter. Entries whose bin is
    empty in the source, or whose letter is missing, are omitted with a
    reason rather than filled in.
    """
    _TABLES["zurich"] = _RATES_ZUR
    _TABLES["penumbral"] = _RATES_PEN
    _TABLES["compactness"] = _RATES_COM
    now = mcintosh_letters(mcintosh)
    prev = mcintosh_letters(previous) if previous else (None, None, None)
    out = {}
    for name, idx, alphabet in _COMPONENTS:
        letter = now[idx]
        if letter is None:
            out[name] = {"available": False,
                         "reason": f"no valid {name} letter in {mcintosh!r}"}
            continue
        start = prev[idx] or letter
        cell = _TABLES[name][level][start][alphabet.index(letter)]
        if cell is None:
            out[name] = {"available": False,
                         "reason": f"{_CITATION} has no groups for the {name} "
                                   f"transition {start} -> {letter}"}
            continue
        rate, sigma = cell
        out[name] = {"available": True, "letter": letter, "previous": start,
                     "assumed_no_evolution": prev[idx] is None,
                     "rate_per_24h": rate, "rate_uncertainty": sigma,
                     "rate_resolved": bool(rate > 0 and sigma < rate)}
    return out


@tool(family="measure")
def flare_probability(mcintosh_class: str, previous_class: str | None = None,
                      window_hours: float = 24.0,
                      lon_deg: float | None = None) -> dict:
    """C / M / X flare probability for one sunspot group from its McIntosh class.

    Poisson probabilities built on the historical 24-hour flaring rates of
    McCloskey, Gallagher & Bloomfield (2016), Sol. Phys. 291, 1711, Table 5.

    mcintosh_class: the group's class now, e.g. 'Hax', 'Cao', 'Fkc'. Only the
      first letter (modified Zurich) is used — the source table resolves that
      component alone, so 'Hsx' and 'Hax' return identical numbers.
    previous_class: the class ~24 h earlier. The table is indexed by
      evolution, so this genuinely changes the answer (H -> D flares at 0.89
      per 24 h for >=C1.0 against 0.68 for D -> D). Omit it and the tool
      assumes no evolution, i.e. the table's diagonal, and says so.
    window_hours: forecast window (24 by default).
    lon_deg: heliographic longitude, west positive. Only used to flag a region
      outside the +/-75 deg band the rates were calibrated over.

    Returns per level (`C`, `M`, `X`): rate_per_24h and its uncertainty,
    `probability`, and a `probability_range` from rate +/- sigma. Also
    `zurich`, `previous_zurich`, `assumed_no_evolution`, `well_sampled`,
    `caveats`, and `citation`.

    This is class climatology, not a forecast: it knows nothing about the
    region's magnetic complexity or its recent flaring, and ignores Hale
    class entirely — so a delta region reads the same as a simple one of the
    same Zurich type. Refuses rather than guessing when the class is not a
    valid Zurich letter or when the source table has no groups in that bin.
    """
    if window_hours <= 0 or window_hours > 72:
        return {"status": "error",
                "error": "window_hours must be > 0 and <= 72 (the source rates "
                         "are 24-hour rates; extrapolating past a few days is "
                         "not supported by the table)"}
    z = zurich_class(mcintosh_class)
    if z is None:
        return {"status": "error",
                "error": f"{mcintosh_class!r} does not start with a modified "
                         f"Zurich class; expected one of {', '.join(_ZURICH)} "
                         "(e.g. 'Hax', 'Cao', 'Fkc')"}
    assumed = previous_class is None
    if assumed:
        prev_z = z
    else:
        prev_z = zurich_class(previous_class)
        if prev_z is None:
            return {"status": "error",
                    "error": f"previous_class {previous_class!r} does not start "
                             f"with a modified Zurich class ({', '.join(_ZURICH)})"}

    col = _ZURICH.index(z)
    levels, well_sampled = {}, True
    for lvl in ("C", "M", "X"):
        cell = _RATES_ZUR[lvl][prev_z][col]
        if cell is None:
            return {"status": "error",
                    "error": f"{_CITATION} has no groups for the transition "
                             f"{prev_z} -> {z}, so there is no rate to quote. "
                             "Give a different previous_class, or omit it to "
                             "use the no-evolution diagonal."}
        rate, sigma = cell
        if sigma >= 0.3:                      # a thin bin in the source table
            well_sampled = False
        comps = component_rates(mcintosh_class, previous_class, lvl)
        avail = {k: v for k, v in comps.items() if v.get("available")}
        span = sorted(round(poisson_probability(v["rate_per_24h"], window_hours), 4)
                      for v in avail.values())
        levels[lvl] = {
            "rate_per_24h": rate,
            "rate_uncertainty": sigma,
            # Each McIntosh letter read in its own marginal table. They are
            # NOT multiplied — see the module docstring.
            "components": {k: (round(poisson_probability(v["rate_per_24h"],
                                                         window_hours), 4)
                               if v.get("available") else None)
                           for k, v in comps.items()},
            "component_rates": comps,
            "component_span": [span[0], span[-1]] if span else None,
            # resolved = the rate is separated from zero by more than 1 sigma.
            # Where it is not, the central probability is an upper-limit
            # statement, not a measurement; read probability_range instead.
            "rate_resolved": bool(rate > 0 and sigma < rate),
            "probability": round(poisson_probability(rate, window_hours), 4),
            "probability_range": [
                round(poisson_probability(rate - sigma, window_hours), 4),
                round(poisson_probability(rate + sigma, window_hours), 4)],
        }

    spans = [v["component_span"] for v in levels.values() if v["component_span"]]
    widest = max((b / max(a, 1e-6) for a, b in spans), default=1.0)
    caveats = [
        "`probability` is the modified-Zurich (first letter) value. The "
        "penumbral and compactness letters are reported alongside it in "
        "`components`, each from its own table, and are NOT combined: the "
        "source tabulates three marginal distributions over the same groups, "
        "not three factors of a joint one, so multiplying them is unfounded.",
        f"The three components span up to {widest:.0f}x in probability here. "
        "A single full-McIntosh number needs the joint 60-class table "
        "(Bornmann & Shaw 1994), which is not openly available.",
        "Class climatology, not a forecast — no knowledge of this region's "
        "magnetic complexity, shear, or recent flaring.",
        "Mount Wilson / Hale class is ignored, so a delta region scores the "
        "same as a simple region of the same Zurich class.",
    ]
    if assumed:
        caveats.append("No previous_class given, so no evolution was assumed "
                       "(the table's diagonal). Supplying yesterday's class "
                       "can change these materially.")
    unresolved = [k for k, v in levels.items() if not v["rate_resolved"]]
    if unresolved:
        caveats.append(
            f"Rate(s) for {', '.join(unresolved)} are not resolved from zero at "
            "1 sigma in the source table, so the central probability is an "
            "upper-limit statement rather than a measurement — quote "
            "probability_range, not probability.")
    if not well_sampled:
        caveats.append("At least one cell comes from a thinly populated bin "
                       "(sigma >= 0.3 flares/24 h). Indicative only.")
    outside = lon_deg is not None and abs(lon_deg) > 75
    if outside:
        caveats.append(f"Longitude {lon_deg:+.0f}° is outside the ±75° band the "
                       "rates were calibrated over; foreshortening also makes "
                       "the class itself unreliable there.")

    return {"zurich": z, "previous_zurich": prev_z,
            "assumed_no_evolution": assumed, "mcintosh_class": mcintosh_class,
            "window_hours": window_hours, "levels": levels,
            "well_sampled": well_sampled,
            "outside_calibration": bool(outside),
            "citation": _CITATION, "caveats": caveats}
