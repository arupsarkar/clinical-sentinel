"""Consistency runner: the same report, N times, per-field agreement.

A deterministic test asserts once; an eval samples a distribution.
This module turns 'the agent seemed stable' into a measured number —
and turns the observed missing_elements wobble into a chart instead
of an anecdote.

COST NOTE: each trial is a real agent run. N=5 on one report ≈ five
intake invocations. Run deliberately, not in a loop you forgot about.
"""

import asyncio
from collections import Counter

from pydantic import BaseModel

from clinical_sentinel.evals.models import GoldenCase
from clinical_sentinel.evals.scorer import score_extraction
from clinical_sentinel.orchestration.intake import run_intake


class FieldConsistency(BaseModel):
    """One field's behavior across N trials."""

    field: str
    pass_rate: float            # fraction of trials matching golden
    agreement_rate: float       # fraction agreeing with the modal answer
    modal_value: str            # most common answer across trials
    distinct_values: int        # how many different answers appeared


class ConsistencyReport(BaseModel):
    source: str
    trials: int
    fields: list[FieldConsistency]
    all_trials_passed: bool     # the headline: was EVERY field right EVERY time


async def run_consistency(golden: GoldenCase, report_filename: str, n: int = 5) -> ConsistencyReport:
    """N sequential intake runs scored against one golden case.

    Sequential, not parallel — simpler, and avoids hammering the API.
    """
    per_field_actuals: dict[str, list[str]] = {}
    per_field_passes: dict[str, int] = Counter()

    for _ in range(n):
        extraction = await run_intake(report_filename)
        result = score_extraction(golden, extraction)
        for f in result.fields:
            per_field_actuals.setdefault(f.field, []).append(f.actual)
            if f.passed:
                per_field_passes[f.field] += 1

    fields = []
    for name, actuals in per_field_actuals.items():
        counts = Counter(actuals)
        modal_value, modal_count = counts.most_common(1)[0]
        fields.append(FieldConsistency(
            field=name,
            pass_rate=per_field_passes[name] / n,
            agreement_rate=modal_count / n,
            modal_value=modal_value,
            distinct_values=len(counts),
        ))

    return ConsistencyReport(
        source=golden.source,
        trials=n,
        fields=fields,
        all_trials_passed=all(f.pass_rate == 1.0 for f in fields),
    )