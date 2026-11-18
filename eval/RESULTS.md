# Eval Results

Findings from the consistency and accuracy measurement layer. The eval
harness runs the intake agent N times on the same report and scores each
run against a human-verified golden label (`eval/golden/*.json`).

## Methodology

Two metrics per field, measured independently:

- **pass_rate** — fraction of trials matching the golden label (correctness)
- **agreement_rate** — fraction of trials agreeing with the modal answer
  (stability, regardless of correctness)

The 2×2 of these rates diagnoses the fix:

| pass | agree | Diagnosis | Fix |
|------|-------|-----------|-----|
| high | high  | Correct and stable | — |
| low  | high  | Stably wrong | Content fix (prompt, normalization map) |
| low  | low   | Unstable | Constraint fix (schema, prompt specificity) |
| high | low   | Mostly right, occasionally wrong | Tighten constraint |

## Finding: drug-name normalization instability (report_002)

**Source:** `report_002.txt` — a consumer email containing the misspelling
"Cardioflex" for the catalog drug Cardiofex.

**N=5 trials, scored against `eval/golden/report_002.json`:**

```
field                   pass  agree  #vals  modal
suspect_drug             80%    80%      2  Cardiofex
patient.age_years       100%   100%      1  None
patient.sex             100%   100%      1  female
patient.initials        100%   100%      1  None
reporter_category       100%   100%      1  consumer
is_complete             100%   100%      1  True
all trials passed: False
```

**What happened:** Four of five runs correctly normalized "Cardioflex" to
the catalog name "Cardiofex." One run returned the verbatim source
spelling. The single-run scorecard on the same report said "all passed:
True" — the N=5 table said otherwise.

**Why it matters:** `suspect_drug` is the most load-bearing field in
the system — it determines which product safety database the case routes
to. An 80% consistency rate on the most important field, invisible to
every manual check and every single-run test, is exactly the class of
failure that motivates statistical evaluation of probabilistic systems.

**Statistical note:** 80% from N=5 is an anecdote with a decimal
point — the 95% confidence interval spans roughly 30%–97%. Five trials
were the right N to surface the first instability; they are the wrong N
to certify a deployment. Observing failures at a 1% rate requires
~300 clean trials.

## Hallucination check (report_002)

The golden label marks `patient.age_years` and `patient.initials` as
`must_not_invent` — the source document contains neither. Across all
five trials, neither field was hallucinated: age remained `None`,
initials remained `None`. The eval harness scores any non-null value
on a `must_not_invent` field as `is_hallucination=True`, a distinct
failure class separated from ordinary wrongness.

## Control case (report_003)

`report_003.txt` is a clean, structured form where every field is
explicit in the source. Deviations here are pure extraction error,
not ambiguity. Used to establish a baseline before testing the harder
cases.

## Reproducing

```bash
uv run clinical-sentinel eval report_002.txt   # N=5 consistency run
```

Archived runs with timestamps live in `workspace/evals/`. Golden
fixtures are human-authored and independently verified against source
text — never bootstrapped from system output.
