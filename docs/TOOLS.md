# Tool reference

*Generated from the live registry by `scripts/gen_docs.py` — do not edit by hand.*

61 core tools in six families. Invoke any tool with
`uv run helio-agent run <tool> '<json-kwargs>'` or `run_tool(name, **kwargs)`;
every call is audit-logged and returns a dict with `status` and `audit_id`.
Tools that cannot honestly do what was asked return `status: "error"` with a
`refusing: ...` message saying why and what to try instead.

| Family | Tools |
|---|---|
| **discover** (11) | `get_noaa_realtime`, `get_solar_regions`, `list_cdaweb_variables`, `list_pyspedas_loaders`, `list_pyspedas_missions`, `list_spacecraft`, `search_cdaweb_datasets`, `search_donki`, `search_hek_events`, `search_heliodata`, `search_vso` |
| **retrieve** (13) | `fetch_cdaweb_data`, `fetch_gfz_index`, `fetch_goes_xrs`, `fetch_hapi`, `fetch_helioviewer_image`, `fetch_kyoto_dst`, `fetch_omni`, `fetch_pyspedas`, `fetch_solar_cycle`, `fetch_spacecraft_ephemeris`, `fetch_swpc_timeseries`, `fetch_vso`, `save_json` |
| **reduce** (10) | `aia_degradation`, `compute_derived`, `correct_aia_map`, `describe_series`, `interpolate_gaps`, `load_solar_map`, `merge_series`, `resample_series`, `shift_time`, `transform_coordinates` |
| **measure** (15) | `cme_arrival`, `cross_correlate`, `extreme_value`, `extreme_value_sweep`, `find_extrema`, `find_flares`, `linear_fit`, `lomb_scargle`, `model_dst`, `plasma_parameters`, `propagation_delay`, `storm_metrics`, `superposed_epoch`, `trace_field_line`, `verify_claim` |
| **literature** (4) | `fetch_arxiv_pdf`, `get_bibtex`, `search_ads`, `search_arxiv` |
| **report** (8) | `export_html`, `plot_distribution`, `plot_orbits`, `plot_scatter`, `plot_solar_map`, `plot_stack`, `plot_timeseries`, `write_pdf_report` |

## discover

Find datasets, spacecraft, events, and imagery in the archives. Read-only; nothing here downloads bulk data.

### `get_noaa_realtime`

```python
get_noaa_realtime(product: 'str' = 'solar_wind') -> 'dict'
```

Current space-weather conditions from NOAA SWPC (operational real-time).

product: 'solar_wind' (RTSW plasma+mag at L1), 'kp' (planetary K index),
'xray' (GOES XRS latest fluxes), 'alerts' (active SWPC alerts).
Real-time operational data — not science quality; see skills/datasources/noaa_swpc.md.

*Source: `helio_agent/tools/discover.py`*

### `get_solar_regions`

```python
get_solar_regions() -> 'dict'
```

Current NOAA/SWPC numbered sunspot regions: location, magnetic class,
area, spot count, and recent flare counts. Operational daily analysis.

*Source: `helio_agent/tools/swpc.py`*

### `list_cdaweb_variables`

```python
list_cdaweb_variables(dataset: 'str') -> 'dict'
```

List the variables (names, units, descriptions) of a CDAWeb dataset ID.

*Source: `helio_agent/tools/discover.py`*

### `list_pyspedas_loaders`

```python
list_pyspedas_loaders(mission: 'str') -> 'dict'
```

List the instrument load routines a pySPEDAS mission project provides.

mission: e.g. 'mms', 'themis', 'ace', 'wind', 'psp', 'solo', 'erg', 'cluster'.

*Source: `helio_agent/tools/spedas.py`*

### `list_pyspedas_missions`

```python
list_pyspedas_missions() -> 'dict'
```

List mission projects supported by pySPEDAS (usable with fetch_pyspedas).

*Source: `helio_agent/tools/spedas.py`*

### `list_spacecraft`

```python
list_spacecraft() -> 'dict'
```

List spacecraft trackable in SSCWeb (~200), with IDs for ephemeris queries.

*Source: `helio_agent/tools/discover.py`*

### `search_cdaweb_datasets`

```python
search_cdaweb_datasets(keyword: 'str', instrument_type: 'str | None' = None, max_results: 'int' = 40) -> 'dict'
```

Search CDAWeb's ~3000 datasets by keyword (matches ID and label).

keyword: substring matched case-insensitively against dataset ID and title.
instrument_type: optional CDAWeb instrumentType filter,
    e.g. 'Magnetic Fields (space)', 'Plasma and Solar Wind', 'Particles (space)'.

*Source: `helio_agent/tools/discover.py`*

### `search_donki`

```python
search_donki(start_date: 'str', end_date: 'str', kind: 'str' = 'FLR') -> 'dict'
```

Query NASA CCMC's DONKI space-weather event database.

kind: FLR (flares), CME, CMEAnalysis, GST (geomagnetic storms),
IPS (interplanetary shocks), SEP, HSS (high speed streams), RBE, MPC.
Dates: 'YYYY-MM-DD'.

*Source: `helio_agent/tools/discover.py`*

### `search_hek_events`

```python
search_hek_events(start: 'str', end: 'str', event_type: 'str' = 'FL', max_results: 'int' = 50) -> 'dict'
```

Query the Heliophysics Event Knowledgebase for solar events.

event_type: HEK two-letter code — FL (flare), CE (CME), AR (active region),
CH (coronal hole), FI (filament), SS (sunspot).

*Source: `helio_agent/tools/discover.py`*

### `search_heliodata`

```python
search_heliodata(query: 'str', max_results: 'int' = 20) -> 'dict'
```

Freetext search of the HDRL HelioData catalog (>7800 datasets).

Uses the alpha HelioData API (api.heliophysics.net). Falls back with a
clear error if the alpha API is down; CDAWeb search still works then.

*Source: `helio_agent/tools/discover.py`*

### `search_vso`

```python
search_vso(start: 'str', end: 'str', instrument: 'str', wavelength_angstrom: 'float | None' = None, max_results: 'int' = 30) -> 'dict'
```

Search the Virtual Solar Observatory for solar imagery/data.

start/end: ISO times, e.g. '2017-09-06T11:00:00'.
instrument: e.g. 'AIA', 'HMI', 'LASCO', 'EIT', 'SECCHI', 'XRT'.
wavelength_angstrom: for narrowband imagers (AIA: 94,131,171,193,211,304,335,1600).

*Source: `helio_agent/tools/discover.py`*

## retrieve

Fetch data to the persistent workspace. Every retrieval writes a file (usually a UTC-indexed CSV with NaN fills) and returns its path.

### `fetch_cdaweb_data`

```python
fetch_cdaweb_data(dataset: 'str', variables: 'list[str]', start: 'str', end: 'str') -> 'dict'
```

Fetch time-series variables from a CDAWeb dataset into a CSV.

dataset: CDAWeb ID, e.g. 'OMNI2_H0_MRG1HR', 'AC_H2_MFI', 'WI_H0_MFI'.
variables: variable names from list_cdaweb_variables, e.g. ['DST1800'].
start/end: ISO UTC times, e.g. '2003-10-28T00:00:00Z'.

Fill values are replaced with NaN using the CDF FILLVAL attribute.

*Source: `helio_agent/tools/retrieve.py`*

### `fetch_gfz_index`

```python
fetch_gfz_index(index: 'str', start: 'str', end: 'str') -> 'dict'
```

Fetch a geomagnetic activity index from GFZ Potsdam (the Kp producer).

index: Kp (3-hourly), ap, Ap (daily), Hp30/Hp60 (30/60-min Kp-like,
open-ended above 9 - resolves storm structure Kp cannot), ap30/ap60,
SN (sunspot number), Fobs (F10.7). start/end: ISO dates or datetimes.
Keyless JSON API; status column 'def' = definitive, 'nowcast' = may revise.

*Source: `helio_agent/tools/indices.py`*

### `fetch_goes_xrs`

```python
fetch_goes_xrs(start: 'str', end: 'str') -> 'dict'
```

Fetch GOES XRS 0.5-4 and 1-8 Angstrom X-ray flux (the flare irradiance record).

Downloads science-quality XRS data via sunpy (NOAA archive) and writes a CSV
with columns xrsa (0.5-4 A) and xrsb (1-8 A) in W/m^2.

*Source: `helio_agent/tools/retrieve.py`*

### `fetch_hapi`

```python
fetch_hapi(server: 'str', dataset: 'str', parameters: 'str', start: 'str', end: 'str') -> 'dict'
```

Fetch time series from any HAPI-compliant server into a CSV.

server: e.g. 'https://cdaweb.gsfc.nasa.gov/hapi'.
parameters: comma-separated parameter names ('' for all).
Useful for sources not covered by a dedicated tool.

*Source: `helio_agent/tools/retrieve.py`*

### `fetch_helioviewer_image`

```python
fetch_helioviewer_image(date: 'str', layers: 'str' = '[SDO,AIA,AIA,171,1,100]', width: 'int' = 1024, height: 'int' = 1024, image_scale: 'float' = 2.4) -> 'dict'
```

Fetch a context image of the Sun from Helioviewer (PNG).

date: ISO time, e.g. '2017-09-06T12:02:00'.
layers: Helioviewer layer string; common choices:
    '[SDO,AIA,AIA,171,1,100]', '[SDO,AIA,AIA,304,1,100]',
    '[SOHO,LASCO,C2,white-light,1,100]', '[SDO,HMI,HMI,magnetogram,1,100]'.
image_scale: arcsec/pixel (2.4 shows full disk at 1024px; ~10 for LASCO C2 field).

Context imagery only — browse-quality JPEG2000-derived, not for photometry.

*Source: `helio_agent/tools/retrieve.py`*

### `fetch_kyoto_dst`

```python
fetch_kyoto_dst(year: 'int', month: 'int', revision: 'str' = 'auto') -> 'dict'
```

Fetch one month of hourly Dst from Kyoto WDC into a CSV.

revision: 'final', 'provisional', 'realtime', or 'auto' (try final ->
provisional -> realtime and report which one answered). Final values are
immutable; provisional/real-time get revised — always cite the revision.

*Source: `helio_agent/tools/indices.py`*

### `fetch_omni`

```python
fetch_omni(start: 'str', end: 'str', resolution: 'str' = '1hour', variables: 'list[str] | None' = None) -> 'dict'
```

Fetch OMNI near-Earth solar wind + activity indices (bow-shock-nose shifted).

resolution: '1hour' (OMNI2_H0_MRG1HR) or '1min' (OMNI_HRO_1MIN).
Default variables (1hour): B magnitude, Bz GSM, speed, density, Dst, Kp.

*Source: `helio_agent/tools/retrieve.py`*

### `fetch_pyspedas`

```python
fetch_pyspedas(mission: 'str', instrument: 'str', start: 'str', end: 'str', probe: 'str | None' = None, datatype: 'str | None' = None, variables: 'list[str] | None' = None, max_columns: 'int' = 24) -> 'dict'
```

Load data through a pySPEDAS mission loader and save it as a workspace CSV.

mission/instrument: project + load routine, e.g. ('mms','fgm'),
('themis','fgm'), ('ace','mfi'), ('psp','fields'). Discover names with
list_pyspedas_missions / list_pyspedas_loaders.
probe: for multi-probe missions ('1'-'4' MMS, 'a'-'e' THEMIS).
datatype: loader-specific product selection (see the loader's docstring).
variables: keep only these tplot variables (default: all loaded, up to
max_columns flattened columns — spectrogram-like 2-D variables are skipped).

Uses each mission's own calibration/variable logic — prefer this over raw
CDAWeb pulls for MMS, THEMIS, ERG, Cluster. Level-2 products only unless
the mission skill says otherwise.

*Source: `helio_agent/tools/spedas.py`*

### `fetch_solar_cycle`

```python
fetch_solar_cycle(start: 'str' = '2008-12', end: 'str | None' = None, include_prediction: 'bool' = False) -> 'dict'
```

Fetch NOAA's Solar Cycle Progression (monthly sunspot number + F10.7).

The observed record runs 1749-01 to the latest released month, one row per
month: ssn (international monthly SSN), smoothed_ssn (13-month smoothed,
lags ~6 months), f10.7 and smoothed_f10.7 (from 1947). NOAA's -1.0
sentinel becomes NaN. start/end: 'YYYY-MM'. Default start 2008-12 is the
cycle 24 minimum (cycles 24-25).

include_prediction: also save the SWPC prediction (predicted_ssn with
high/low bounds) to a second CSV.

Summary includes the latest monthly value and the window's smoothed
maximum (the cycle peak once smoothing has caught up).

*Source: `helio_agent/tools/swpc.py`*

### `fetch_spacecraft_ephemeris`

```python
fetch_spacecraft_ephemeris(spacecraft: 'list[str]', start: 'str', end: 'str', coordinate_system: 'str' = 'Gse') -> 'dict'
```

Fetch spacecraft trajectories from SSCWeb into a CSV (km).

spacecraft: SSCWeb IDs (lowercase), e.g. ['ace', 'dscovr', 'themisa', 'mms1', 'iss'].
coordinate_system: Gse, Gsm, Geo, Gm, Sm, GeiTod, GeiJ2000.

*Source: `helio_agent/tools/retrieve.py`*

### `fetch_swpc_timeseries`

```python
fetch_swpc_timeseries(product: 'str', start: 'str | None' = None, end: 'str | None' = None) -> 'dict'
```

Fetch a NOAA SWPC operational time series into a workspace CSV.

product:
  'xray'   - GOES primary XRS 1-min flux, last 7 days -> columns xrsa, xrsb
             (W/m^2, operational scale: use find_flares with swpc_scale=false)
  'plasma' - real-time solar wind (DSCOVR/ACE RTSW), last 3 days ->
             density (1/cm^3), speed (km/s), temperature (K)
  'mag'    - real-time IMF, last 3 days -> bx/by/bz GSM, bt (nT)
  'kp'     - planetary K index (3-hourly)
start/end: optional ISO UTC times to trim the feed's native window.

Operational nowcast data: gaps, spikes, and later revisions are normal.

*Source: `helio_agent/tools/swpc.py`*

### `fetch_vso`

```python
fetch_vso(start: 'str', end: 'str', instrument: 'str', wavelength_angstrom: 'float | None' = None, max_files: 'int' = 4) -> 'dict'
```

Download solar data files (FITS) from the VSO into the workspace.

Deliberately capped at max_files to avoid accidental bulk downloads;
raise the cap explicitly for larger pulls.

*Source: `helio_agent/tools/retrieve.py`*

### `save_json`

```python
save_json(name: 'str', payload: 'dict | list') -> 'dict'
```

Persist a JSON-able result (e.g. an event list) to the workspace for later steps.

*Source: `helio_agent/tools/retrieve.py`*

## reduce

Turn retrieved files into analysis-ready series and maps. Deterministic transforms; no science judgment embedded.

### `aia_degradation`

```python
aia_degradation(date: 'str', channels: 'list[int] | None' = None) -> 'dict'
```

AIA sensitivity degradation factors at a date (aiapy, SSW calibration).

Factor = fraction of launch (2010) sensitivity remaining; divide observed
intensity by it to get corrected intensity. date: ISO. channels: EUV
wavelengths in Angstrom (default: all seven).

*Source: `helio_agent/tools/aia.py`*

### `compute_derived`

```python
compute_derived(file: 'str', expression: 'str', out_column: 'str', out_name: 'str | None' = None) -> 'dict'
```

Add a derived column via a pandas eval expression over existing columns.

Example: expression='sqrt(BX_GSE**2 + BY_GSE**2 + BZ_GSE**2)', out_column='Bmag'.
Only numeric expressions over the file's columns are allowed (pandas.eval,
no python execution).

*Source: `helio_agent/tools/reduce.py`*

### `correct_aia_map`

```python
correct_aia_map(fits_file: 'str', out_name: 'str | None' = None) -> 'dict'
```

Apply the degradation correction to an AIA FITS file.

Divides the image by the channel's degradation factor at its observation
time and writes a corrected FITS. Use before any cross-epoch intensity
comparison; pointless for single-epoch morphology.

*Source: `helio_agent/tools/aia.py`*

### `describe_series`

```python
describe_series(file: 'str') -> 'dict'
```

Summarize a workspace time-series CSV: coverage, gaps, NaN fraction, ranges.

*Source: `helio_agent/tools/reduce.py`*

### `interpolate_gaps`

```python
interpolate_gaps(file: 'str', max_gap: 'str' = '2h', out_name: 'str | None' = None) -> 'dict'
```

Linearly interpolate NaNs, but only across gaps shorter than max_gap.

Longer gaps are left as NaN so that data absence stays visible.

*Source: `helio_agent/tools/reduce.py`*

### `load_solar_map`

```python
load_solar_map(fits_file: 'str') -> 'dict'
```

Load a solar FITS file as a sunpy Map and report its metadata (no plot).

Returns observatory, instrument, wavelength, time, scale — use
report.plot_solar_map to render it.

*Source: `helio_agent/tools/reduce.py`*

### `merge_series`

```python
merge_series(files: 'list[str]', how: 'str' = 'outer', out_name: 'str' = 'merged.csv') -> 'dict'
```

Join multiple time-series CSVs on their time index (outer join by default).

*Source: `helio_agent/tools/reduce.py`*

### `resample_series`

```python
resample_series(file: 'str', cadence: 'str', method: 'str' = 'mean', out_name: 'str | None' = None) -> 'dict'
```

Resample a time-series CSV to a uniform cadence ('1min','5min','1h','1D').

method: 'mean', 'median', 'max', 'min'. NaNs ignored within bins; empty
bins stay NaN (never interpolated silently — interpolate_gaps is explicit).

*Source: `helio_agent/tools/reduce.py`*

### `shift_time`

```python
shift_time(file: 'str', shift: 'str', out_name: 'str | None' = None) -> 'dict'
```

Shift a series' time index by a fixed offset (e.g. '45min' L1→magnetopause lag).

Use measure.propagation_delay to compute a physically motivated shift first.

*Source: `helio_agent/tools/reduce.py`*

### `transform_coordinates`

```python
transform_coordinates(file: 'str', columns: 'list[str]', from_coords: 'str', to_coords: 'str', out_name: 'str | None' = None) -> 'dict'
```

Rotate a 3-component vector time series between geocentric frames.

file: workspace CSV; columns: exactly three column names [x, y, z] in
from_coords. Frames: gei, gse, gsm, sm, geo, mag, j2000 (pySPEDAS
cotrans; dipole recomputed per sample). Output adds columns suffixed
_<to_coords>. Works for any vector (position km, field nT) — magnitude
is preserved by construction.

*Source: `helio_agent/tools/geospace.py`*

## measure

Fit, correlate, model, and quantify. These produce the science numbers — each anchored by a validation case.

### `cme_arrival`

```python
cme_arrival(v0_kms: 'float', launch_time: 'str', w_kms: 'float' = 450.0, gamma_per_km: 'float' = 2e-08, r0_rs: 'float' = 21.5, target_au: 'float' = 1.0) -> 'dict'
```

Drag-based CME arrival estimate (Vrsnak et al. 2013 DBM).

dv/dt = -gamma (v - w)|v - w|: the CME relaxes toward the ambient wind
speed w. Analytic solution integrated from r0 (default 21.5 Rs, the
DONKI CMEAnalysis reference height) to target_au.

v0_kms: CME speed at r0 (use DONKI CMEAnalysis 'speed' for type=C/S/O).
w_kms: ambient solar wind speed (350-450 slow, 550-650 in a stream).
gamma_per_km: drag parameter, typically 0.1e-7 (wide/massive CME) to
1e-7 (narrow/low-mass). An ensemble over gamma x w gives the arrival
window — typical real accuracy is +/- 10 h; never quote minutes.

*Source: `helio_agent/tools/models.py`*

### `cross_correlate`

```python
cross_correlate(file: 'str', column_a: 'str', column_b: 'str', max_lag: 'str' = '6h') -> 'dict'
```

Time-lagged cross-correlation between two columns of one merged CSV.

Positive best_lag means column_b lags column_a. Series are aligned on the
file's cadence; NaNs pairwise-dropped per lag.

*Source: `helio_agent/tools/measure.py`*

### `extreme_value`

```python
extreme_value(file: 'str', column: 'str', threshold: 'float', direction: 'str' = 'min', decluster_gap_hours: 'float' = 48.0, return_periods_years: 'list[float] | None' = None) -> 'dict'
```

Peaks-over-threshold GPD analysis with runs declustering.

file/column: workspace time-series CSV (e.g. hourly Dst, daily peak
flux). threshold: exceedance threshold in the column's units.
direction: 'min' for negative extremes (Dst), 'max' for positive
(flux, speed). decluster_gap_hours: exceedances closer than this are
one event (48 h suits geomagnetic storms; use ~12 h for flares).

Returns the GPD fit (method of moments — deterministic), the return
level for each requested return period, and the empirical event rate.
Run extreme_value_sweep to see how much the answer depends on these
conventions before quoting any return period.

*Source: `helio_agent/tools/extremes.py`*

### `extreme_value_sweep`

```python
extreme_value_sweep(file: 'str', column: 'str', thresholds: 'list[float]', direction: 'str' = 'min', decluster_gaps_hours: 'list[float] | None' = None, return_period_years: 'float' = 100.0) -> 'dict'
```

Convention sweep: the same return level across threshold x declustering
choices. A published return period is a methodological choice — this
shows the spread you should quote as its uncertainty.

*Source: `helio_agent/tools/extremes.py`*

### `find_extrema`

```python
find_extrema(file: 'str', column: 'str', mode: 'str' = 'min') -> 'dict'
```

Find the extremum of a column and when it occurred (e.g. Dst minimum).

*Source: `helio_agent/tools/measure.py`*

### `find_flares`

```python
find_flares(file: 'str', column: 'str' = 'xrsb', min_class: 'str' = 'C1.0', swpc_scale: 'bool' = True) -> 'dict'
```

Detect flares in a GOES XRS long-channel series (SWPC-style logic).

The series is first averaged to 1-minute cadence (the operational
standard). A flare starts after 3 consecutive rising minutes with flux
above min_class (SWPC uses a similar 4-minute rise test), peaks at the
local maximum, and ends when flux decays to halfway (linear) between
peak and pre-flare level. Returns start/peak/end and GOES class.

swpc_scale: science-quality GOES-8..15 netcdf files carry TRUE irradiance;
the historical/operational flare classes (and all pre-2020 literature) use
fluxes with the SWPC scaling factor applied (XRS-B x0.7). Leave True to
get classes comparable to the operational record; set False for GOES-R
(16+) products already in operational scale or for true-irradiance work.
See skills/missions/goes.md.

*Source: `helio_agent/tools/measure.py`*

### `linear_fit`

```python
linear_fit(file: 'str', x_column: 'str', y_column: 'str', order: 'int' = 1) -> 'dict'
```

Least-squares polynomial fit y(x) with parameter uncertainties.

Typical use: CME height-time -> linear speed (order=1) or acceleration
(order=2). x may be 'time' to fit against seconds since series start.

*Source: `helio_agent/tools/measure.py`*

### `lomb_scargle`

```python
lomb_scargle(file: 'str', column: 'str', min_period: 'str' = '1h', max_period: 'str' = '100D', n_freq: 'int' = 2000) -> 'dict'
```

Lomb-Scargle periodogram for (possibly gappy) time series.

Returns the top 5 peaks with periods and false-alarm probabilities.
Read skills/methods/timing_periodicity.md before interpreting.

*Source: `helio_agent/tools/measure.py`*

### `model_dst`

```python
model_dst(file: 'str', v_column: 'str', bz_column: 'str', density_column: 'str | None' = None, dst_column: 'str | None' = None, initial_dst: 'float' = 0.0, out_name: 'str | None' = None) -> 'dict'
```

Ring-current Dst nowcast from L1 solar wind (O'Brien & McPherron 2000).

dDst*/dt = Q - Dst*/tau, with injection Q = -4.4 (VBs - 0.49) nT/h for
the rectified dawn-dusk field VBs = V x Bs (mV/m; Bs = southward Bz,
else 0) above the 0.49 mV/m threshold, and decay time
tau = 2.40 exp(9.74 / (4.69 + VBs)) hours. With a density column, the
pressure correction Dst = Dst* + 7.26 sqrt(Pdyn) - 11 is applied.

file: CSV with solar wind at 1 AU / L1 (propagation delay to the
magnetopause is NOT applied here — shift_time first if driving from L1
in real time). v_column km/s, bz_column nT (GSM), density_column 1/cm^3.
dst_column: observed Dst for skill scores (corr, RMSE, min error).
Integration cadence = the file's cadence (resample to >= 5min first;
hourly is the fidelity the model was fit at).

*Source: `helio_agent/tools/models.py`*

### `plasma_parameters`

```python
plasma_parameters(density_cm3: 'float', b_nT: 'float', temperature_K: 'float | None' = None, ion: 'str' = 'p+') -> 'dict'
```

Derived plasma parameters via PlasmaPy (PyHC core package).

Inputs: number density (cm^-3), magnetic field magnitude (nT), and
optionally temperature (K). Returns Alfven speed, ion gyrofrequency and
gyroradius (needs T), plasma beta (needs T), thermal speed (needs T),
and ion inertial length. Typical slow solar wind at 1 AU:
n~5 cm^-3, B~5 nT, T~1e5 K -> v_A ~ 49 km/s, beta ~ 0.7.

*Source: `helio_agent/tools/measure.py`*

### `propagation_delay`

```python
propagation_delay(solar_wind_speed_kms: 'float', from_x_km: 'float' = 1500000.0, to_x_km: 'float' = 0.0) -> 'dict'
```

Ballistic solar-wind propagation delay between two GSE-X positions.

Defaults: L1 (~1.5e6 km upstream) to Earth. Crude — assumes radial,
constant speed; good to ~±10 min for steady wind. See skills/methods/cross_spacecraft.md.

*Source: `helio_agent/tools/measure.py`*

### `storm_metrics`

```python
storm_metrics(file: 'str', dst_column: 'str' = 'DST') -> 'dict'
```

Characterize a geomagnetic storm from a Dst/SYM-H series.

Returns minimum Dst, its time, storm classification (NOAA-style bands:
<-30 weak-ish threshold, -50 moderate, -100 intense, -250 extreme),
main-phase duration (last zero-crossing before minimum -> minimum) and
recovery estimate (time to reach half the minimum after it).

*Source: `helio_agent/tools/measure.py`*

### `superposed_epoch`

```python
superposed_epoch(file: 'str', column: 'str', epochs: 'list[str]', before: 'str' = '2D', after: 'str' = '5D', cadence: 'str' = '1h') -> 'dict'
```

Superposed epoch analysis: stack column around a list of epoch times.

Returns median, mean, and quartiles vs epoch-relative hours. Read
skills/methods/superposed_epoch.md for epoch selection guidance.

*Source: `helio_agent/tools/measure.py`*

### `trace_field_line`

```python
trace_field_line(x_gsm_re: 'float', y_gsm_re: 'float', z_gsm_re: 'float', time: 'str', kp: 'int' = 2) -> 'dict'
```

Trace the magnetic field line through a GSM point (Tsyganenko T89 + IGRF).

Position in Earth radii (GSM); time ISO UTC (sets dipole orientation);
kp 0-6 selects the T89 activity level. Returns both footpoints (GEO
latitude/longitude at r=1 Re) and whether the line is closed (both ends
reach Earth), open (one end), or not traced (neither within 30 Re).

T89 is a quiet-to-moderate empirical model — do not trust footpoints
during storm main phases; see skills/methods/coordinate_systems.md.

*Source: `helio_agent/tools/geospace.py`*

### `verify_claim`

```python
verify_claim(claimed_value: 'float', computed_value: 'float', claimed_units: 'str', computed_units: 'str', tolerance_percent: 'float' = 10.0, claim_description: 'str' = '', computed_audit_id: 'str' = '') -> 'dict'
```

Verdict on a published claim vs an audit-logged computed value.

REFUSES (no verdict) when units don't normalize to the same thing, when
the tolerance is nonsensical, or when the computed value has no audit id
— a comparison must be traceable or it proves nothing. Otherwise returns
verdict 'match' or 'mismatch' with the relative difference.

Cadence/processing caveats (1-min vs hourly, scaled vs true flux,
provisional vs final index) are the agent's responsibility BEFORE
calling: if the two numbers were produced differently, do not compare
them — recompute like-for-like first (see
skills/methods/paper_reproduction.md).

*Source: `helio_agent/tools/verify.py`*

## literature

NASA ADS and arXiv access for context and cross-checking.

### `fetch_arxiv_pdf`

```python
fetch_arxiv_pdf(arxiv_id: 'str') -> 'dict'
```

Download an arXiv paper PDF into the workspace for reading.

*Source: `helio_agent/tools/literature.py`*

### `get_bibtex`

```python
get_bibtex(bibcodes: 'list[str]') -> 'dict'
```

Fetch BibTeX entries from ADS for a list of bibcodes.

*Source: `helio_agent/tools/literature.py`*

### `search_ads`

```python
search_ads(query: 'str', max_results: 'int' = 10, sort: 'str' = 'citation_count desc') -> 'dict'
```

Search NASA ADS. query uses ADS syntax, e.g.
'GX 339-4 outburst', 'author:"Gopalswamy" year:2004-2006 CME',
'full:"superposed epoch" abs:"solar wind"'.

*Source: `helio_agent/tools/literature.py`*

### `search_arxiv`

```python
search_arxiv(query: 'str', max_results: 'int' = 10, category: 'str' = 'astro-ph.SR') -> 'dict'
```

Search arXiv (no key needed). category astro-ph.SR = solar/stellar;
physics.space-ph = space physics.

*Source: `helio_agent/tools/literature.py`*

## report

Publication-styled figures, statistical plots, PDF reports, and self-hosted HTML export.

### `export_html`

```python
export_html(markdown_file: 'str', template_id: 'str' = 'research', theme_mode: 'str' = 'light', title: 'str | None' = None, embed_assets: 'bool' = False, engine: 'str' = 'unmarkdown', out_name: 'str | None' = None) -> 'dict'
```

Export a markdown file as a standalone, self-hostable HTML page.

Applies an unmarkdown visual template (default: 'research', the
analysis-note standard — see skills/tools/analysis_notes.md) with all
styles inlined, and wires Mermaid, KaTeX, and Chart.js to render
client-side. The file needs no unmarkdown.com hosting: serve it from any
web server or open it locally.

embed_assets=False (default): rendering libraries load from SRI-pinned
CDNs — small file, network needed at view time. embed_assets=True:
the libraries are downloaded once (shared HTTP cache), each verified
against its pinned sha384, and inlined — a ~4 MB fully-offline page
(KaTeX fonts still prefer the CDN when online; offline math falls back
to system fonts).

engine: "unmarkdown" (default) applies a hosted visual template via the
unmarkdown convert API (needs UNMARKDOWN_API_KEY); "local" converts
entirely on this machine (markdown-it-py + the built-in publication
stylesheet) — no unmarkdown.com involvement, no key, works offline
end-to-end when combined with embed_assets=True. template_id is ignored
for engine="local".

*Source: `helio_agent/tools/export.py`*

### `plot_distribution`

```python
plot_distribution(file: 'str', columns: 'list[str]', kind: 'str' = 'violin', title: 'str' = '', y_label: 'str' = '', log_y: 'bool' = False, out_name: 'str' = 'distribution.png') -> 'dict'
```

Statistical distribution plot (seaborn): 'violin', 'box', or 'hist'.

Compares the distributions of one or more numeric columns from a
workspace CSV — e.g. solar wind speed by interval, or Bz in storm vs
quiet times (merge_series first to get the columns side by side).

*Source: `helio_agent/tools/report.py`*

### `plot_orbits`

```python
plot_orbits(file: 'str', plane: 'str' = 'xy', units: 'str' = 'Re', title: 'str' = '', out_name: 'str' = 'orbits.png') -> 'dict'
```

Plot spacecraft trajectories from an ephemeris CSV (fetch_spacecraft_ephemeris).

plane: 'xy', 'xz', or 'yz' (GSE/GSM axes). units: 'Re' (Earth radii) or 'km'.
Earth drawn at origin when units='Re'.

*Source: `helio_agent/tools/report.py`*

### `plot_scatter`

```python
plot_scatter(file: 'str', x_column: 'str', y_column: 'str', fit: 'bool' = False, title: 'str' = '', x_label: 'str' = '', y_label: 'str' = '', log_x: 'bool' = False, log_y: 'bool' = False, out_name: 'str' = 'scatter.png') -> 'dict'
```

Scatter plot of two columns with optional linear fit + 95% CI band
(seaborn regplot). Open markers, publication style.

Typical use: solar wind speed vs |B|, Kp vs Bz, flare peak flux vs
duration. Reports Pearson r alongside the figure.

*Source: `helio_agent/tools/report.py`*

### `plot_solar_map`

```python
plot_solar_map(fits_file: 'str', out_name: 'str' = 'solar_map.png', clip_percent: 'float' = 99.5) -> 'dict'
```

Render a solar FITS file (AIA/HMI/LASCO/...) with the proper colormap.

*Source: `helio_agent/tools/report.py`*

### `plot_stack`

```python
plot_stack(files_columns: 'list[dict]', title: 'str' = '', event_times: 'list[str] | None' = None, out_name: 'str' = 'stackplot.png') -> 'dict'
```

Multi-panel stacked time-series plot (the standard space-physics figure).

files_columns: list of {"file": path, "column": name, "label": ylabel,
"log": bool} — one panel per entry, shared time axis.

*Source: `helio_agent/tools/report.py`*

### `plot_timeseries`

```python
plot_timeseries(file: 'str', columns: 'list[str] | None' = None, title: 'str' = '', log_y: 'bool' = False, event_times: 'list[str] | None' = None, event_labels: 'list[str] | None' = None, series_labels: 'list[str] | None' = None, y_label: 'str' = '', out_name: 'str' = 'timeseries.png') -> 'dict'
```

Single-panel time-series plot of one or more columns from a workspace CSV.

series_labels: legend names for the plotted columns, in the same order
(e.g. ["Monthly SSN", "13-month smoothed"]) — finished figures should
never show raw column names. y_label: axis label with units.

*Source: `helio_agent/tools/report.py`*

### `write_pdf_report`

```python
write_pdf_report(title: 'str', sections: 'list[dict]', out_name: 'str' = 'report.pdf') -> 'dict'
```

Assemble a PDF report from text sections and figure files.

sections: list of {"heading": str, "text": str, "image": optional path}.
Every numeric claim in the text must trace to an audit-logged tool result.

*Source: `helio_agent/tools/report.py`*

