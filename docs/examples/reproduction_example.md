# Reproduction: Worked example (deterministic)

**Paper:** doi: 10.0000/example

| Claim | Capability | Verdict |
|---|---|---|
| c1 | ready | match |

## Claim c1

The ballistic L1 propagation delay at 500 km/s is reproduced.

- Capability: `ready`
- Claimed: `50.0 minutes`
- Computed: `50.0 minutes`
- Verdict: `match` at `1.0%` tolerance
- Verification audit: `6b04e85bcb7e`

### Data identity

- Dataset: `constant-speed example`
- Instrument: `none`
- Processing Level: `derived`
- Cadence: `not applicable`
- Revision: `1`
- Time Window: `instantaneous`

### Ordered recipe

1. `propagation_delay` with `{"solar_wind_speed_kms":500.0}` (audit `25461eaa0ed1`)

### Caveats

- Deterministic input, chosen so the manifest chain can be demonstrated without archive access.
