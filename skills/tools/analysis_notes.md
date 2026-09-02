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
Ask the user which format, or use their stated default. Samples below share
identical content — compare side by side:

| template_id | Character | Sample |
|---|---|---|
| `research` | DM Sans/Serif; modern academic; good default for reproductions | [sample](https://unmarkdown.com/u/calexyoung/analysis-note-sample-research) |
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
