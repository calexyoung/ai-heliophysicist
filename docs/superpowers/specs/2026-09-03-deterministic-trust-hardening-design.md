# Deterministic Trust Hardening Design

## Purpose

Harden the AI Heliophysicist so its reproducibility, provenance, workspace
isolation, and operational-health guarantees are enforced by code rather than
convention. Add a structured paper-reproduction record that joins published
claims to exact data, processing steps, audited computations, caveats, and
verdicts.

This work does not change the scientific algorithms or replace the external
agent's scientific judgment. It strengthens the deterministic boundary around
that judgment.

## Scope

The implementation covers six related changes:

1. Exact audit and replay semantics for artifact and non-artifact results.
2. Workspace path containment for generated data and reports.
3. Real audit-entry validation in `verify_claim`.
4. Explicit monitor health and failure-aware CLI exit behavior.
5. Cached, replay-safe HTTP POST support.
6. A structured paper-reproduction manifest with deterministic validation.

Documentation will state precisely which tools have direct published-result
anchors and which are supporting capabilities exercised only indirectly or by
offline tests.

## Provenance Model

### Canonical results

Each successful or failed tool call will retain the existing concise
`result_summary` and additionally store a canonical, JSON-safe `result` payload.
The payload excludes the call's newly assigned `audit_id`, preventing an audit
identifier from making an otherwise identical replay differ. Dictionaries are
serialized with stable key ordering; paths and other non-JSON objects retain
the existing string representation behavior.

New audit entries will also record SHA-256 hashes for input files named by tool
arguments. File discovery is conservative: string path arguments and paths
inside lists or dictionaries are hashed only when they resolve to existing
regular files. Secrets and unrelated strings are not interpreted as files.

### Replay verdict

Replay will evaluate four independent dimensions:

- original and replay status;
- canonical result payload;
- input-file hashes before re-execution;
- output artifact hashes after re-execution.

A replay is `match` only when every available dimension matches. A changed,
missing, or newly introduced artifact is a mismatch. For older audit entries
without a full result or input hashes, replay returns `unverifiable` unless
artifact hashes provide a complete comparison. It must never infer a match from
status equality alone.

Replay remains backward compatible at the storage level: old JSONL entries can
still be read, and no migration rewrites the append-only log.

### Claim verification

`verify_claim` will require `computed_audit_id` to resolve to a real audit entry
with status `ok`. The entry's recorded result must contain the supplied
`computed_value` as a numeric leaf. This is intentionally field-agnostic for
the first version because existing tools use different output keys; the
manifest records the semantic claim and units. Missing entries, failed calls,
legacy entries without full results, and values absent from the result are
refused.

## Workspace Containment

`data_path` and `output_path` will share one resolver that:

- accepts only relative names;
- resolves the candidate against the intended workspace directory;
- rejects `..` traversal, absolute paths, and symlink escapes;
- creates the containing workspace directory only after validation.

Existing nested relative names such as `goes/{file}` remain supported when
their resolved destination stays inside the workspace. Tools may continue to
read explicitly supplied external inputs; this change governs generated
outputs only.

## HTTP Cache

Introduce a method-aware `cached_request` primitive and retain `cached_get` as
a compatibility wrapper. Cache identity includes method, URL, public query
parameters, and a canonical hash of the public request body. Credential values
and authorization headers never appear in cache metadata or keys.

Cached entries store status, redacted URL, and response bytes as today. In
`readonly` mode, both GET and POST miss without network access. ADS BibTeX and
Unmarkdown conversion will use the shared primitive. Because the Unmarkdown
request body contains user-authored Markdown, its content hash belongs in the
key while the body itself need not be stored in metadata.

## Monitor Health

A monitor cycle will classify required source calls and expose:

- `status: ok` when all required sources succeed;
- `status: degraded` when current-condition feeds fail but CME/storm tracking
  completes;
- `status: error` when CME or storm event ingestion fails, because forecast
  state cannot be trusted as current.

The response includes `failed_sources` entries containing tool name and error.
The last successful event-ingestion timestamp remains distinct from the last
attempt timestamp. State writes use a temporary sibling followed by atomic
replacement. The CLI exits nonzero for `error`; `degraded` remains visible but
returns zero so transient display-feed outages do not stop scheduled tracking.

## Paper-Reproduction Manifest

Add `helio_agent/reproduction.py` with a versioned JSON schema represented by
plain dictionaries and deterministic validators. A manifest contains:

- schema version and paper citation identifiers;
- an ordered claim list;
- claimed value and units;
- dataset, instrument, processing level, cadence, revision, and time window;
- an ordered processing recipe of tool names, arguments, and audit IDs;
- computed value, units, tolerance, verdict, and verification audit ID;
- caveats and capability state: `ready`, `method_gap`, or `blocked`.

Core operations will create a manifest, validate an existing manifest, and
render a Markdown summary. Validation checks required fields, enum values,
unique claim IDs, real audit references, successful recorded calls, recipe
order, and agreement between stored verification verdicts and their audit
records. It reports all violations in one deterministic result rather than
failing at the first problem.

The operations will be registered in the existing tool families without
introducing a seventh family:

- `create_reproduction_manifest` in `report`;
- `validate_reproduction_manifest` in `measure`;
- `render_reproduction_report` in `report`.

Manifests and reports are written through contained workspace paths and are
included as audit artifacts.

## Compatibility and Error Handling

- Existing audit fields remain present.
- Existing GET cache files remain readable; new POST entries use the same file
  envelope and a method/body-aware key.
- `cached_get` keeps its current public signature.
- Tool errors continue to return dictionaries through `run_tool`.
- Legacy replay records are reported as `unverifiable`, not silently accepted
  or destructively migrated.
- Invalid output paths and invalid manifests return explicit refusal errors
  through normal tool error handling.

## Testing

Development follows red-green-refactor cycles. Offline tests will cover:

- non-artifact result divergence, input mutation, missing/new artifacts, and
  legacy replay behavior;
- traversal, absolute path, nested safe path, and symlink escape handling;
- nonexistent, failed, unrelated-value, and valid audit IDs for claim checks;
- monitor `ok`, `degraded`, and `error` states plus atomic state replacement;
- POST cache round trips, body-sensitive keys, credential redaction, and
  readonly misses without network calls;
- valid and invalid reproduction manifests, audit-reference checks, and stable
  Markdown rendering;
- CLI exit codes and documentation/schema-lock consistency.

The full offline test suite and the existing live validation suite are the
completion gates. Live validation may expose upstream warnings, but every
scientific check must pass before completion is claimed.

## Out of Scope

- Automatically interpreting arbitrary PDFs or extracting claims without an
  agent/scientist review.
- Changing numerical methods, thresholds, or published validation tolerances.
- Migrating or rewriting historical audit logs.
- Building a database, web service, or new LLM orchestrator.
