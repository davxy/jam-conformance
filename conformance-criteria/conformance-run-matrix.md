# Conformance Run Matrix (Proposed)

Date: 2026-03-02

## Goals

- Ensure that a team's Jam implementation is conformant to the M1 milestone.
- Define test programme that all teams have to satisfy with explicit parameters and acceptance criteria

## Test structure

- Teams have to satisfy different tests to cover as much as possible about the Jam specification.
- We use our own Fuzzer as part of this test programme as a best-effort tool to determine correct behaviour, but this is not the only test.
- The test programme is divided in different lanes and teams have to pass all of them. 

- Lanes:
    * [L1 - Minimum behaviour conformance]: run implementation against all published and well-known Test-Vectors. 
        - Teams have to pass all known (and applicable to M1) JAM test-vectors.
        - This ensures that teams don't break any well-known behaviour conditions. 
    * [L2 - Happy Path]: run implementation for a large number of steps (100k or 1M?) without mutations. 
        - This ensures that teams can import well-formed blocks one after another, with Work-Packages exercising two different services (Bootstrap and Fuzzing)
        - Teams have to import all blocks without error.
        - Use seeds that have not yet been used in published reports or traces.
        - Also, if we want smaller seeds (for example 1 byte) only 42 has been used, so we can pick any other numbers.
    * [L3 - Bad block detection - mutations]: run several shorter runs (for 10k steps?) using only mutations to intentionally generate possible error conditions. 
        - Teams have to reach the same response as our Fuzzer
        - This ensures teams can detect error conditions and not import bad blocks.
    * [L4 - (Optional) Exploratory Error]: run against selected traces or parameter combinations that in the past have highlighted selected mismatch categories from some teams.
        - Although teams may react differently to the same trace, these runs will be known to have generated particular classes in the past.
        - This test demonstrates teams have corrected against such known mismatches
        - There is no guarantee that these runs will ever trigger the same mismatch category that was seen in the past.

## L1 — Known Test Vectors

### Parameters

- ???

### Acceptance Criteria

- 100% pass of required known vectors.
- Any mismatch is a hard conformance failure.

## L2 — Happy Path

### Parameters

- profile: full
- fuzzy_profile: full
- max_mutations: 0
- mutation_ratio: 0.0
- max_work_items: 3
- max_steps: 100000
- safrole: false
- seeds: 10 pre-determined seeds (if 100k steps); 1 pre-determined seed (if 1M steps)

### Execution

- Run each team with all seeds.

### Acceptance Criteria

- No import mismatch (`exp == got` every step)
- No state diff
- Session reaches `max_steps`

---

## L3B — Mutations

### Parameters

- profile: empty
- max_mutations: 3 / 5 / 10 (run each)
- mutation_ratio: 0.1
- max_work_items: 5 and 16
- max_steps: 10000
- safrole: false
- seed: 42

### Known evidence samples

- [fuzz-reports/baseline_traces_0.7.1/reports/fastroll/1761651767/report.json](../fuzz-reports/baseline_traces_0.7.1/reports/fastroll/1761651767/report.json)
- [fuzz-reports/baseline_traces_0.7.1/reports/fastroll/1761651837/report.json](../fuzz-reports/baseline_traces_0.7.1/reports/fastroll/1761651837/report.json)
- [fuzz-reports/0.7.1/archive_reports/fastroll/1761585612/report.json](../fuzz-reports/0.7.1/archive_reports/fastroll/1761585612/report.json)

### Acceptance Criteria

- Fuzzer must emit known reject class.
- Team behavior must match the Fuzzer's

## L3B (2) — Mutations 

### Parameters

- profile: full
- fuzzy_profile: full
- max_mutations: 5
- mutation_ratio: 0.1
- max_work_items: 5
- max_steps: 10000
- safrole: false
- seeds: 10 (mix of known + new)

### Note

In current historical reports, there is no strong prior for `profile=full` with `max_mutations>0` yielding `exp != ok`.
Treat this lane as exploratory discovery and triage.

### Acceptance Criteria

- Not a hard failure lane by itself.
- Any divergence must be reproducible on rerun with same seed/config.

