# Paper reproduction
> Reproduce a paper's numbers with the tool layer, refusing dishonest comparisons.

## What it is / When to use it
The loop for checking a published result against this system's tools — for
literature validation, for extending a study, or for testing the tool layer
itself. Modeled on helio-agent's reproduce → verify → critique pipeline; here
the LLM agent performs extraction and triage, and `verify_claim` performs the
comparison.

## How to use it
1. **Extract claims.** Read the paper (fetch_arxiv_pdf / ADS). List each
   numeric claim as: value, units, the dataset it came from (mission,
   instrument, cadence, processing level, index revision), and the method.
2. **Triage each claim** against capability, honestly:
   - `ready`: dataset reachable by a tool (check coverage!), method exists.
   - `method_gap`: data reachable but no tool computes the quantity — say so;
     propose a tool + validation case rather than improvising.
   - `blocked`: data not publicly reachable. Stop for that claim.
3. **Recompute like-for-like.** Match the paper's cadence, window, dataset
   version, and conventions (GOES scaling! Dst revision! degradation
   correction for AIA intensities!). If you cannot match a convention, note
   it and widen the tolerance with a reason.
4. **Verify** with `verify_claim(claimed, computed, units, tolerance,
   computed_audit_id=...)`. It refuses unit mismatches and untraceable
   values; a `mismatch` verdict is a finding to investigate, never an
   immediate "the paper is wrong".
5. **Report**: per claim — verdict, relative difference, audit ids, and any
   convention caveats. Unverified claims are listed as unverified, not
   omitted.

## Gotchas and judgment calls
- The most common false mismatch sources: GOES SWPC scaling (x0.7), Dst
  revision (final vs provisional vs pre-1957 differences), OMNI time
  shifting, AIA degradation, instrument-era differences, provisional
  catalogs revised after publication.
- Papers round; a claim of "-383 nT" verified at tolerance 1% is honest,
  at 0.01% is theater.
- Tolerance defaults to 10%; tighten only when the paper's precision and
  your convention match justify it, and record why.

## Cross-checks
- Where possible verify one claim from two independent data paths (e.g.
  Kyoto Dst and OMNI's Dst copy) before trusting either comparison.
- validation/run_validation.py is the standing reproduction suite; a paper
  reproduced end-to-end deserves a permanent case there.
