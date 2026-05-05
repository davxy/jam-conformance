# Conformance Run Matrix (Proposed)

Date: 2026-05-05

## Goals

- Ensure that a team's Jam implementation is conformant to the M1 milestone.
- Define test programme that all teams have to satisfy with explicit parameters and acceptance criteria

## Versions

Conformance runs must use tooling matching the Gray Paper version targeted by the implementation. The accepted minimum is GP 0.7.2; later releases are accepted as their tooling rows are added below.

| GP version | Fuzzer | jam-types-py |
|------------|--------|--------------|
| 0.7.2 | [`fuzzer-gp-0.7.2`](https://github.com/paritytech/polkajam/releases/tag/fuzzer-gp-0.7.2) | [`v0.7.2`](https://github.com/davxy/jam-types-py/releases/tag/v0.7.2) |

## Test structure

- Teams have to satisfy different tests to cover as much as possible about the Jam specification.
- We use our own Fuzzer as part of this test programme as a best-effort tool to determine correct behaviour, but this is not the only test.
- The test programme is divided in different lanes and teams have to pass all of them.

- Lanes:
    * L0 -- Smoke test: minimal sanity run on the tiny spec.
    * L1 -- Happy-path import: import without mutations or Safrole.
        - L1a -- Tiny spec
        - L1b -- Full spec
    * L2 -- Mutations: import with mutation/error handling, without Safrole.
        - L2a -- Tiny spec
        - L2b -- Full spec
    * L3 -- Safrole: exercise Safrole, no mutations.
        - L3a -- `validators-management` workload
        - L3b -- empty workload

The fuzzer parameters for each lane are defined in `fuzzer_configs/`.

## Acceptance Criteria

### Known test vectors

- 100% pass of the required known vectors.
- Any mismatch is a hard conformance failure.
- Self-assessed by the implementor; no explicit assessment performed during evaluation.

### Fuzzer-driven lanes (L0–L3)

For every step of a session, the target's response must match the fuzzer's expected outcome:

- If the (possibly mutated) block is valid: the target imports it and the resulting post-state root matches the expected post-state root.
- If the (possibly mutated) block is invalid: the target rejects it with an Error response. The specific error variant is not required to match — only that the target rejects.

Every session must additionally reach its configured `max_steps`.

The wire-level message exchange (block submission, import / state-root / error responses) is defined by the fuzzer protocol; see [`../fuzz-proto/README.md`](../fuzz-proto/README.md) and [`../fuzz-proto/fuzz-v1.asn`](../fuzz-proto/fuzz-v1.asn).

## Submission

The implementor submits the target as a Docker image conforming to the [Standard Target Packaging](../fuzz-proto/README.md#standard-target-packaging) section of the fuzzer protocol. In summary:

- `linux/amd64` Docker image, kept minimal.
- Reads `JAM_FUZZ`, `JAM_FUZZ_SPEC`, `JAM_FUZZ_DATA_PATH` and `JAM_FUZZ_SOCK_PATH` from the environment (plus the optional `JAM_FUZZ_LOG_LEVEL`); refuses to start if any required variable is missing.
- Listens on the configured Unix domain socket and supports multiple fuzzer sessions in sequence, with exactly one `Initialize` message per session.

Each lane is run against the submitted image using the corresponding `fuzzer_configs/*.toml`. Resulting traces, reports and summaries are published under [`../fuzz-reports/<gp-version>/`](../fuzz-reports/); see [`../fuzz-reports/README.md`](../fuzz-reports/README.md) for the layout and team registry.

The known test vectors lane requires no submission beyond the implementor's self-assessment.

## Known Test Vectors

Run the implementation against the published JAM test vectors at https://github.com/davxy/jam-test-vectors.

## L0 -- Smoke test

Source: `fuzzer_configs/l0_tiny.toml`

| Parameter | Value |
|-----------|-------|
| jam_spec | tiny |
| profile | empty |
| max_mutations | 0 |
| max_steps | 32 |
| safrole | false |
| skip_slots | false |

## L1 -- Happy-path import

Import without mutations and without Safrole.

### L1a -- Tiny

Source: `fuzzer_configs/l1_tiny.toml`

| Parameter | Value |
|-----------|-------|
| jam_spec | tiny |
| profile | full |
| fuzzy_profile | full |
| max_mutations | 0 |
| max_work_items | 5 |
| max_steps | 100000 |
| safrole | false |
| skip_slots | false |

### L1b -- Full

Source: `fuzzer_configs/l1_full.toml`

| Parameter | Value |
|-----------|-------|
| jam_spec | full |
| profile | full |
| fuzzy_profile | full |
| max_mutations | 0 |
| max_work_items | 5 |
| max_steps | 100000 |
| safrole | false |
| skip_slots | false |

## L2 -- Mutations

Testing both happy-path import and mutation/error handling, without Safrole.

### L2a -- Tiny

Source: `fuzzer_configs/l2_tiny.toml`

| Parameter | Value |
|-----------|-------|
| jam_spec | tiny |
| profile | full |
| fuzzy_profile | full |
| max_mutations | 5 |
| mutation_ratio | 0.1 |
| max_work_items | 5 |
| max_steps | 1000000 |
| safrole | false |
| skip_slots | false |

### L2b -- Full

Source: `fuzzer_configs/l2_full.toml`

| Parameter | Value |
|-----------|-------|
| jam_spec | full |
| profile | full |
| fuzzy_profile | full |
| max_mutations | 5 |
| mutation_ratio | 0.1 |
| max_work_items | 5 |
| max_steps | 1000000 |
| safrole | false |
| skip_slots | false |

## L3 -- Safrole

Both sub-runs enable Safrole and run with `skip_slots = false`.

### L3a -- `validators-management` workload

Source: `fuzzer_configs/l3_tiny.toml`

| Parameter | Value |
|-----------|-------|
| jam_spec | tiny |
| profile | validators-management |
| fuzzy_profile | empty |
| safrole | true |
| max_mutations | 0 |
| max_work_items | 3 |
| max_steps | 100000 |
| skip_slots | false |

### L3b -- empty workload

Source: `fuzzer_configs/l3_full.toml`

| Parameter | Value |
|-----------|-------|
| jam_spec | full |
| profile | empty |
| fuzzy_profile | empty |
| safrole | true |
| max_mutations | 0 |
| max_work_items | 0 |
| max_steps | 100000 |
| skip_slots | false |

## Final Acceptance

After all test lanes pass, two additional steps are required before complete acceptance:

1. Fellowship code review
2. Final interview

## References

- Fuzzer protocol: [`../fuzz-proto/README.md`](../fuzz-proto/README.md), [`../fuzz-proto/fuzz-v1.asn`](../fuzz-proto/fuzz-v1.asn)
- JAM test vectors: https://github.com/davxy/jam-test-vectors
- JAM tiny profile: https://docs.jamcha.in/basics/chain-spec/tiny
- JAM full profile: https://docs.jamcha.in/basics/chain-spec/full
