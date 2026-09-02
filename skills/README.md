# Skills: durable knowledge, written down

Craft knowledge the agent must read before acting — recipes, calibration
quirks, failure signatures, judgment calls the documentation never states.
Modeled on the AI Astrophysicist's skills library.

## Layout

- `missions/` — how to work with each mission's data (instruments, dataset
  IDs, cadences, gotchas, validation anchors).
- `methods/` — how to do each kind of analysis (flare analysis, CME analysis,
  superposed epoch, timing, ...), mission-independent.
- `datasources/` — how each archive/service works (CDAWeb, OMNI, SSCWeb, VSO,
  Helioviewer, HEK, DONKI, HAPI, HelioData, NOAA SWPC, low-latency feeds).
- `tools/` — software reference (sunpy, pyspedas, CDF handling, plotting
  conventions).

## Composition rule

An analysis reads the **method** skill plus the **mission** skill(s) plus the
**datasource** skill for wherever the data comes from. Example: "flare
analysis of the 2017-09-06 event" → `methods/flare_analysis.md` +
`missions/goes.md` + `missions/sdo.md` + `datasources/hek.md`.

## Living documents

Extend a skill every time something new is learned (a failure signature, a
dataset quirk); rewrite it in place when reality disagrees with it. A wrong
skill is worse than a missing one — fix it the moment a tool result proves
it wrong.
