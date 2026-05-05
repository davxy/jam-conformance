# Conformance Run Matrix (Proposed)

Date: 2026-05-05

## Goals

- Ensure that a team's Jam implementation is conformant to the M1 milestone.
- Define test programme that all teams have to satisfy with explicit parameters and acceptance criteria

## Test structure

- Teams have to satisfy different tests to cover as much as possible about the Jam specification.
- We use our own Fuzzer as part of this test programme as a best-effort tool to determine correct behaviour, but this is not the only test.
- The test programme is divided in different lanes and teams have to pass all of them.

- Lanes:
    * L0 -- Smoke test: minimal sanity run on the tiny spec.
    * L1 -- Happy-path import: import without mutations or Safrole.
        - L1a -- Tiny spec
        - L1b -- Full spec
    * L2 -- Mutations: happy-path import together with mutation/error handling, without Safrole.
        - L2a -- Tiny spec
        - L2b -- Full spec
    * L3 -- Safrole: exercise Safrole, no mutations.
        - L3a -- `validators-management` workload
        - L3b -- empty workload

The fuzzer parameters for each lane are defined in `fuzzer_configs/`.

## Known Test Vectors

Run implementation against all published and well-known test vectors.

### Acceptance Criteria

- 100% pass of required known vectors.
- Any mismatch is a hard conformance failure.
- Self-assessed by the implementor; no explicit assessment performed during evaluation.

## L0 -- Smoke test

Source: `fuzzer_configs/l0_tiny.toml`

| Parameter | Value |
|-----------|-------|
| jam_spec | tiny |
| profile | empty |
| max_mutations | 0 |
| max_steps | 100 |
| safrole | false |
| skip_slots | false |

### Acceptance Criteria

- Target accepts trace input and produces matching state roots.
- Session reaches `max_steps`.

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
| seeds | 10 random |

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
| seeds | 10 random |

### Acceptance Criteria (L1a/L1b)

- Expected state root matches target state root on every step.
- Session reaches `max_steps`.

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
| seeds | 10 random |

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
| seeds | 10 random |

### Acceptance Criteria (L2a/L2b)

- Expected state root matches target state root on every step.
- Session reaches `max_steps`.

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
| seeds | 10 random |

### L3b -- empty workload

Source: `fuzzer_configs/l3_full.toml`

| Parameter | Value |
|-----------|-------|
| jam_spec | tiny |
| profile | empty |
| fuzzy_profile | empty |
| safrole | true |
| max_mutations | 0 |
| max_work_items | 0 |
| max_steps | 100000 |
| skip_slots | false |
| seeds | 10 random |

### Acceptance Criteria (L3a/L3b)

- Expected state root matches target state root on every step.
- Session reaches `max_steps`.

## Final Acceptance

After all test lanes pass, two additional steps are required before complete acceptance:

1. Fellowship code review
2. Final interview

## References

- JAM tiny profile: https://docs.jamcha.in/basics/chain-spec/tiny
- JAM full profile: https://docs.jamcha.in/basics/chain-spec/full
