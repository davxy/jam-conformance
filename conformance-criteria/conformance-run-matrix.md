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
    * [L2 - Happy Path]: run implementation for a large number of steps (100k or 1M?) without mutations or fuzzing. 
        - This ensures that teams can import well-formed blocks one after another. 
        - Teams have to import all blocks without error.
        - Use seeds that have not yet been used in published reports or traces.
        - Also, if we want smaller seeds (for example 1 byte) only 42 has been used, so we can pick any other numbers.
    * [L3A - Bad block detection - fuzzing]: run several shorter runs (for 10k steps?) using only fuzzing to intentionally generate possible error conditions. 
        - Teams have to reach the same response as our Fuzzer
        - This ensures teams can detect error conditions and not import bad blocks.
        - May use own seed
    * [L3B - Bad block detection - mutations]: run several shorter runs (for 10k steps?) using only mutatiosn to intentionally generate possible error conditions. 
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

## L3A — Fuzzing (Fuzzy, No Mutations)

### Parameters

- profile: fuzzy
- fuzzy_profile: rand/full (?)
- max_mutations: 0
- mutation_ratio: 0.1 (inactive because max_mutations = 0)
- max_work_items: 1
- max_steps: 10000
- safrole: false
- seed: 42

### Known evidence samples

- [fuzz-reports/0.7.1/reports/jampy/1761651476/report.json](../fuzz-reports/0.7.1/reports/jampy/1761651476/report.json)
- [fuzz-reports/0.7.1/reports/jampy/1761651616/report.json](../fuzz-reports/0.7.1/reports/jampy/1761651616/report.json)
- [fuzz-reports/0.7.1/reports/jampy/1761651837/report.json](../fuzz-reports/0.7.1/reports/jampy/1761651837/report.json)

### Acceptance Criteria

- Fuzzer produces at least one reject class from known set (e.g., InvalidEpochMark, bad offenders mark, report-slot-future).
- Team response must map to expected accept/reject class for that step.

### (Optional) Additional sweep for instruction-family coverage

Run short repeats across fuzzy profiles:

- fuzzy_profile in: mem-check, storage, preimages, management, services
- max_steps: 5000 each
- seeds: 3 per fuzzy_profile
- keep max_mutations = 0

### Acceptance Criteria

- At least one fuzzer-side reject is generated for the lane.
- Coverage target: each selected fuzzy_profile executed at least 3 seeds.

## L3B (1) — Mutations

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

