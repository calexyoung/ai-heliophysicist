# Solar Wind Analysis
> Read L1 plasma/field data, distinguish slow/fast wind, and recognize ICME, magnetic cloud, and shock signatures.

## What it is / When to use it
In-situ solar wind is monitored upstream of Earth at L1 by ACE, Wind, and DSCOVR. Use this skill when characterizing solar wind conditions, identifying ICMEs/shocks/stream interfaces, or attributing geomagnetic activity to a driver.

## How to use it
1. Data: OMNI merged dataset (time-shifted to bow-shock nose; see omniweb skill) for most analyses; instrument-level data (ACE SWEPAM/MAG, Wind SWE/MFI, DSCOVR) via CDAWeb when you need L1-native times or higher fidelity.
2. Typical ambient ranges at 1 AU (orientation values, not hard limits):
   - Slow wind: V ~ 300-450 km/s, n ~ 5-15 /cc, denser, variable, from streamer belt.
   - Fast wind: V ~ 500-800 km/s, n ~ 2-5 /cc, from coronal holes; hotter protons, steadier B, Alfvenic fluctuations.
   - |B| ~ 5 nT quiet; > 10-15 nT is disturbed; > 20 nT usually means ICME sheath/cloud or strong CIR.
3. ICME identification (look for several, not one):
   - Abnormally LOW proton temperature relative to the expected T(V) for that speed.
   - Low proton plasma beta (< ~0.5, often << 1 in clouds).
   - Enhanced |B| with LOW variance (smooth field).
   - Magnetic cloud subset: smooth, large-angle (> ~30-180 deg) coherent rotation of the B direction over ~1 day, low beta, enhanced |B| — flux-rope geometry.
   - Supporting: bidirectional suprathermal electrons, enhanced O7+/O6+ or Fe charge states (ACE SWICS era), declining speed profile (expansion).
4. Shock identification (fast forward shock): simultaneous sharp jumps in V, n, T, and |B| — all four up, within a minute at L1. A jump in B/n with T dropping is more likely a tangential discontinuity or stream interface, not a shock.
5. CIR/HSS: gradual density+B compression, speed rising over many hours, T rising with V (unlike ICME), B fluctuating (not smooth), followed by a long fast stream. Recurs at ~27 days.

## Gotchas and judgment calls
- ICME boundaries are genuinely ambiguous; published catalogs (Richardson & Cane list, near-Earth ICME catalog) disagree by hours. Give boundary times with stated uncertainty.
- ACE SWEPAM density/temperature degrade during strong SEP events exactly when you care most; cross-check Wind or DSCOVR.
- Not every shock has an ICME behind it at your spacecraft (flank passage); not every ICME drives a shock (slow ones).
- Fill values (-1e31 in CDF, 9999.9-style in OMNI ASCII) will silently wreck means and correlations — mask first (see troubleshooting skill).
- The geoeffective quantity is southward Bz in GSM, not |B| or speed alone (see coordinate_systems skill).

## Cross-checks
- Check the Richardson & Cane ICME list and the CfA/Harvard Wind shock database for the interval — verify via web search for current URLs.
- Driver consistency: an ICME at L1 should have a plausible CME launched 1-4 days earlier (DONKI/CDAW); a CIR should recur ~27 days earlier/later and map to a coronal hole in EUV imagery.
- Compare two L1 spacecraft (ACE vs Wind) when a feature looks instrumental.
