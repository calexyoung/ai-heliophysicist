# Solar Radio Burst Analysis (type II / type III)
> Detect and classify type III electron-beam and type II shock bursts in WIND/WAVES dynamic spectra, convert their frequency drift to a source speed, and tie them to the flare and CME.

## What it is / When to use it
Radio bursts are the earliest remote signature that an eruption has released particles and driven a shock. In a dynamic spectrum (intensity vs time and frequency) emission drifts to lower frequency as the source moves outward through falling plasma density. **Type III**: electron beams on open field lines, seconds to minutes, drift rates of MHz/s in the corona, reaching kHz at 1 AU within an hour. **Type II**: CME-driven shocks, drifting slowly (tens of minutes to hours from MHz to tens of kHz). Use this skill to confirm that a flare launched a shock (type II presence), to get an independent shock speed, and to time the eruption relative to the SEP onset and coronagraph first appearance.

## Data
- **WIND/WAVES** `WI_K0_WAV` / `E_Average`: dB above background at 76 log-spaced frequencies 250 Hz to 10 MHz (TNR + RAD1 + RAD2 merged), ~3-min cadence, 1994-present. Fetch with `fetch_cdaweb_spectrogram` (default dataset/variable); columns `c<Hz>`. Higher-cadence products: `WI_H1_WAV` (RAD1/RAD2 1-min) for drift-rate work.
- Below ~20 kHz the TNR range is dominated by the local plasma line and quasi-thermal noise, not solar bursts; the tool excludes it by default (`min_freq_hz`).
- Ground-based metric coverage (e-CALLISTO, RSTN) for the coronal (25-180 MHz) part of type II bursts; STEREO/WAVES for the second vantage point. Not fetched by a tool yet.
- **Gaps are real and common in K0.** 2017-09-10 (X8.2) is entirely fill in `WI_K0_WAV`; `fetch_cdaweb_spectrogram` returns all-NaN and `radio_bursts` reports "no radio bursts". Check `n_records` and the NaN fraction before concluding there was no burst.

## Tool: `radio_bursts` (ported from helio-agent 2026-09-03)
- Active time = at least `min_channels` (8) channels above `min_freq_hz` exceed `min_db` (10 dB); active times within `gap_minutes` (15) merge. Per burst: start/end/duration, samples, peak dB/time/frequency, frequency span, inferred radial speed, classification.
- Speed: log-frequency centroid of the first vs last active sample, converted to heliocentric distance through Leblanc, Dulk & Bougeret (1998) n_e(r) assuming **fundamental** plasma emission; (r1 − r0)/Δt. Harmonic emission would halve the distances; the density model is a quiet-Sun average, so quote the speed as indicative (factor ~2).
- Classification: speed > `typeiii_min_speed_km_s` (5000) = type III; 200-5000 km/s = type II candidate; no downward drift = unclassified (AKR, noise storms, single-channel interference); a single-sample enhancement spanning ≥ 1 decade = type III (impulsive).
- **At 3-min cadence a type III group at flare onset merges with the type II that follows** into one long burst whose drift speed reflects the shock (2017-09-06 X9.3: one burst 11:58-16:19, 52 dB peak at 12:10, 6.7 MHz to 30 kHz, 2160 km/s). Lower `gap_minutes` or use `WI_H1_WAV` to separate them; the merged speed is still a usable shock speed to compare against the CDAW/DONKI CME speed.
- Lower `min_channels` (4) to catch narrow-band type II lanes; expect more unclassified fragments. Raising `min_db` suppresses the diffuse decay and can stitch a whole day into one "burst" (the 6 dB run above stretched 09:10-19:19).

## Cross-checks
- Flare timing: the type III group should start at the X-ray onset (`find_flares`), not the peak; a type II starts a few minutes after the flare peak once the shock forms (typically at 1.2-2 R☉).
- CME speed: compare `inferred_speed_km_s` of the type II candidate with the DONKI/CDAW CME speed (`search_donki kind="CME"`); agreement to a factor 1.5 is normal for a fundamental-emission Leblanc inversion.
- SEP association: a DH type II is the best single predictor of a large SEP event (Gopalswamy et al. 2008); pair with `characterize_sep` on the same day.
- In-situ arrival: if the burst is a type II and a shock arrives at L1 1-3 days later (`detect_icme`), the mean transit speed brackets the radio speed from below.
- Literature (`search_ads`) for the event's published burst timing; CDAW keeps a type II list (Wind/WAVES DH type II catalog) with start/end frequencies to compare `freq_max_hz`/`freq_min_hz`.
