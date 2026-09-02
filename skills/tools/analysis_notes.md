# Analysis notes: format and publishing
> The canonical structure for an analysis note and how to publish it as a formatted page (unmarkdown), with seven vetted templates.

## What it is / When to use it
Every completed analysis (paper reproduction, event study, one-off
investigation) ends in an `analysis.md` under
`users/<name>/analyses/<slug>/`. This skill fixes the note's structure and
the publishing path so notes are consistent, shareable, and traceable.

## Note structure (canonical)
Write the markdown in this order — a reader should get the verdict without
scrolling:

```
# <Title: what was analyzed>
**Analyst:** <user> · **Date:** YYYY-MM-DD · **Method:** <skill path> · **Status:** <complete|draft>

## Summary            2-4 sentences: the answer first, then the one caveat that matters
## Papers             table: Paper | Bibcode  (omit if not literature-driven)
## Verdicts           table: Claim | Source | Computed | Verdict  (✅ match / ⛔ blocked / ❌ mismatch)
                      + a blockquote for the finding that needs emphasis
## Method             short prose; a ```mermaid flowchart for multi-step logic
## Data & provenance  dataset IDs, record counts, AUDIT IDS for every headline
                      number, and the replay command
## Model cross-check  (if a model was run) result vs observation, assumptions
## Promotion notes    what moved to core (validation case names) vs stayed user-scoped
```

Rules: every number carries an audit id somewhere in the note; blocked/
unverified claims are listed, never omitted; math as $...$/$$...$$ and
diagrams as mermaid fences (both render only on published pages, not in the
convert API or PDFs).

## Publishing (unmarkdown MCP)
Tools: `create_document` (title, content, template_id) →
`publish_document` (id, visibility). Conventions:
- visibility "link" (unlisted) by default; "public" only on explicit request.
- title = the note's H1; let the slug auto-generate unless asked.
- After publishing, record the URL at the top of the local analysis.md.
- Updates: `update_document` on the same id keeps the URL stable.
- Google Docs / Word / email export: the "Copy for..." buttons at
  unmarkdown.com only — raw HTML pasting loses formatting.

## Template options (all verified 2026-09-02, rendered with real content)
**Default: `research`** (user decision 2026-09-02) — use it without asking.
Offer the alternatives only when the user asks for a different look or the
note's character clearly calls for one (e.g. `logbook` for an observing-log
style event study). Samples share identical content — compare side by side:

| template_id | Character | Sample |
|---|---|---|
| `research` | **DEFAULT** — DM Sans/Serif; modern academic | [sample](https://unmarkdown.com/u/calexyoung/analysis-note-sample-research) |
| `lab-report` | Source fonts; structured, scientific-report feel | [sample](https://unmarkdown.com/u/calexyoung/analysis-note-sample-lab-report) |
| `ieee` | Noto; journal-manuscript styling | [sample](https://unmarkdown.com/u/calexyoung/analysis-note-sample-ieee) |
| `apa` | APA-manuscript styling; formal reports | [sample](https://unmarkdown.com/u/calexyoung/analysis-note-sample-apa) |
| `thesis` | Source fonts; formal long-form | [sample](https://unmarkdown.com/u/calexyoung/analysis-note-sample-thesis) |
| `logbook` | IBM Plex; observing-log character, suits event studies | [sample](https://unmarkdown.com/u/calexyoung/analysis-note-sample-logbook) |
| `swiss` | Clean minimal default (free tier) | [sample](https://unmarkdown.com/u/calexyoung/analysis-note-sample-swiss) |

`theme_mode` "light"/"dark" applies to any of them. Other templates exist
(62 total; catalog at docs.unmarkdown.com/templates) — probe an id with a
tiny convert_markdown call before relying on it; unknown ids 400 cleanly.

## Gotchas and judgment calls
- convert_markdown does NOT render mermaid/KaTeX/charts — for notes
  containing them, publish and share the URL; don't paste converted HTML.
- The published page is presentation; the committed analysis.md in the repo
  remains the record of truth (with audit ids). Never let them diverge:
  update both or neither.
- API key: UNMARKDOWN_API_KEY in .env (never commit it).

## Cross-checks
- Open the published page once after publishing: check mermaid and math
  actually rendered, tables didn't overflow, and the verdict marks survived.
- `get_usage` if publishing in bulk (Pro quota: 10k calls/month).

## Data-bearing reports (added 2026-09-02, learned publishing Sun News)
- Published pages render ```chart (Chart.js JSON: type/data/options) — for
  reports, live charts beat embedded PNGs. Downsample time series first
  (10-min bins for a day; monthly for cycle plots) and use the core palette
  hexes (#0072B2 #D55E00 #009E73 #E69F00).
- **update_document does NOT update the published page** — republish
  (publish_document, same slug) after every content change or the page
  serves the stale version.
- Verify rendering with a REAL browser (playwright), not the in-app pane —
  a hidden pane can have a 0-width viewport that fakes broken charts.
- Logarithmic Chart.js axes label ticks verbosely (1.0000000000E-6);
  acceptable, but prefer linear axes where the data allows.
- Sun News web edition example: unmarkdown.com/u/calexyoung/sun-news-2026-09-02
