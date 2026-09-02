"""Claim verification: compare a published number against a computed one.

The deterministic half of the paper-reproduction loop (pattern from
helio-agent's verify.py). The key idea: a comparison that isn't apples to
apples is REFUSED, never reported as a mismatch — a false "the paper is
wrong" is worse than no verdict. The agent supplies judgment (which claim,
which tool, which caveats); this tool supplies the honest comparison.
"""

from __future__ import annotations

import re

from helio_agent.registry import tool

# Units that must never be compared directly (same quantity, different scale
# conventions) unless identical strings.
_NORMALIZE = {
    "nanotesla": "nt", "nt": "nt",
    "km/s": "km/s", "km s-1": "km/s", "km s^-1": "km/s", "kms-1": "km/s",
    "w/m^2": "w/m^2", "w m-2": "w/m^2", "w/m2": "w/m^2", "w m^-2": "w/m^2",
    "/cm^3": "/cm^3", "cm-3": "/cm^3", "cm^-3": "/cm^3", "per cc": "/cm^3",
    "hours": "h", "hr": "h", "h": "h", "days": "d", "d": "d",
    "kelvin": "k", "k": "k", "mev": "mev", "kev": "kev", "ev": "ev",
    "degrees": "deg", "deg": "deg",
}


def _norm_unit(u: str) -> str:
    key = re.sub(r"\s+", " ", u.strip().lower())
    return _NORMALIZE.get(key, key)


@tool(family="measure")
def verify_claim(claimed_value: float, computed_value: float,
                 claimed_units: str, computed_units: str,
                 tolerance_percent: float = 10.0,
                 claim_description: str = "",
                 computed_audit_id: str = "") -> dict:
    """Verdict on a published claim vs an audit-logged computed value.

    REFUSES (no verdict) when units don't normalize to the same thing, when
    the tolerance is nonsensical, or when the computed value has no audit id
    — a comparison must be traceable or it proves nothing. Otherwise returns
    verdict 'match' or 'mismatch' with the relative difference.

    Cadence/processing caveats (1-min vs hourly, scaled vs true flux,
    provisional vs final index) are the agent's responsibility BEFORE
    calling: if the two numbers were produced differently, do not compare
    them — recompute like-for-like first (see
    skills/methods/paper_reproduction.md).
    """
    cu, pu = _norm_unit(computed_units), _norm_unit(claimed_units)
    if cu != pu:
        return {"status": "error", "verdict": "refused",
                "error": f"refusing: units differ after normalization "
                         f"({claimed_units!r} -> {pu!r} vs {computed_units!r} "
                         f"-> {cu!r}); convert first, then re-verify"}
    if not 0 < tolerance_percent <= 100:
        return {"status": "error", "verdict": "refused",
                "error": "refusing: tolerance_percent must be in (0, 100]"}
    if not computed_audit_id:
        return {"status": "error", "verdict": "refused",
                "error": "refusing: computed_value must carry the audit_id of "
                         "the tool call that produced it"}
    denom = max(abs(claimed_value), abs(computed_value), 1e-30)
    rel = abs(computed_value - claimed_value) / denom * 100
    verdict = "match" if rel <= tolerance_percent else "mismatch"
    return {"verdict": verdict,
            "claim": claim_description,
            "claimed": f"{claimed_value} {claimed_units}",
            "computed": f"{computed_value} {computed_units}",
            "relative_difference_percent": round(rel, 2),
            "tolerance_percent": tolerance_percent,
            "computed_audit_id": computed_audit_id,
            "note": ("mismatch is a finding, not a conclusion: check "
                     "revision/cadence/scaling conventions before claiming "
                     "the paper is wrong" if verdict == "mismatch" else "")}
