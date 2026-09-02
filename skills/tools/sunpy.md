# sunpy
> The core Python library for solar data: unified search/fetch (Fido), images (Map), and time series (TimeSeries).

## What it is / When to use it
sunpy is the community standard for solar remote-sensing analysis in Python. Use it for finding/downloading solar data, loading FITS images with correct WCS/coordinates, GOES/other time series, and solar coordinate transforms. For in-situ multi-mission work, cdasws/pyspedas are usually better fits.

## How to use it
- Fido (see also vso skill):
```python
from sunpy.net import Fido, attrs as a
import astropy.units as u
q = Fido.search(a.Time('2024-05-10 06:00', '2024-05-10 06:05'),
                a.Instrument.aia, a.Wavelength(171*u.angstrom))
files = Fido.fetch(q)
```
  Fido fans out to VSO, JSOC, HEK, and scraper-based clients depending on attrs.
- Map (2D images):
```python
import sunpy.map
m = sunpy.map.Map(files[0])
m.peek()                                  # quicklook with limb/grid
sub = m.submap(bottom_left, top_right=...)  # SkyCoord-based cutouts
```
  Map carries WCS; use `astropy.coordinates.SkyCoord` with `sunpy.coordinates.frames` (Helioprojective, HeliographicStonyhurst, HeliographicCarrington) for positions; `m.plot()` + `ax.plot_coord(...)` for overlays.
- TimeSeries:
```python
from sunpy import timeseries as ts
xrs = ts.TimeSeries(goes_file)            # knows GOES XRS, EVE, NOAA indices...
df = xrs.to_dataframe()
```
- Coordinates: differential rotation / feature tracking via `sunpy.coordinates.propagate_with_solar_surface` context or RotatedSunFrame; frame transforms are astropy-native (`coord.transform_to(frame)`).

## Gotchas and judgment calls
- `Map()` on a level-1 AIA file is fine for morphology, but photometry needs `aiapy` corrections (degradation, exposure normalization) and possibly `register()` (lev1.5 alignment). Don't compare raw DN across epochs — AIA channels degrade significantly over the mission.
- Fido silently unions results from multiple clients; check `q` for which client answered and for duplicates before fetching.
- JSOC queries require `a.jsoc.Notify('<registered email>')`; unregistered addresses fail.
- Off-disk coordinates: transforming Helioprojective points off the limb to heliographic gives NaN unless you use the screen assumption (`Helioprojective.assume_spherical_screen`).
- Units are enforced (astropy Quantity) — passing bare floats to attrs like Wavelength raises; this is a feature.
- Large downloads: use `a.Sample`, and set `path=` in fetch to a real data directory; the default cache can bloat.
- TimeSeries concatenation across daily files: `ts.TimeSeries(files, concatenate=True)`.

## Cross-checks
- `m.peek()` after every load — wrong pointing/rotation is obvious to the eye.
- Compare a Fido-fetched image with Helioviewer at the same timestamp.
- Verify coordinate transforms against a known landmark (disk center, a numbered AR's SWPC-reported position).
