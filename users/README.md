# User profiles

Per-user space for one-off work, so the shared core stays general and the
repo stays shareable. Activate a profile by setting `HELIO_AGENT_USER=<name>`
(env var or `.env`); create one by copying `users/_template/`.

## What goes where — the promotion policy

**Core** (`helio_agent/`, `skills/`, `validation/`) — anything of general
use: a new data source, mission, method, analysis tool, or Python package
dependency. The bar for core: it gets a validation case anchored to a
published/known result, a skill note if there is craft to record, and a
schema-lock entry. *If reproducing a paper required building it, and the
next paper could use it too, it is core.*

**User** (`users/<name>/`) — one-off work: a single paper's reproduction,
an analysis for one talk or article, event-specific scripts, personal
report templates. Results (figures, PDFs, analysis notes) live and are
committed here; bulk downloaded data is not (gitignored).

When user work grows up — a one-off script proves generally useful —
promote it: move it into core, add the validation case, regenerate the
schema lock, note it in the relevant skill. Promotion is a normal commit,
reviewed like any core change.

## Layout of a profile

```
users/<name>/
  tools/       one-off tools (*.py, auto-loaded when the profile is active,
               tagged [user:<name>] in `helio-agent list`; may not shadow
               core tool names; excluded from the core schema lock)
  skills/      one-off skills (paper-specific recipes, personal conventions)
  analyses/    committed results: one directory per analysis with its
               figures, PDFs, and an analysis.md stating claims, verdicts,
               and audit ids
  workspace/   data/ outputs/ logs/ — the active workspace when the profile
               is selected (data/ and logs/ are gitignored; outputs you
               want to keep should be copied into analyses/)
```

The HTTP cache stays global (`workspace/cache/`) — archive responses are
user-independent and sharing them saves everyone's bandwidth.

## Rules that still apply

The CLAUDE.md contract is user-agnostic: user tools compute, the agent
judges; no fabricated numbers; refuse with a reason; audit-log everything
(the audit trail is per-profile, under `users/<name>/workspace/logs/`).
A user tool without a validation anchor is a draft — label its results
accordingly in the analysis notes.
