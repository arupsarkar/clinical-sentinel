"""Evaluation domain models: golden labels and scoring results.

The eval layer gets the same treatment as everything else — Pydantic
at the boundary. Golden files are human-authored JSON; parsing them
through GoldenCase means a malformed label file dies loudly at load
time, not silently mid-eval.
"""

from pydantic import BaseModel, Field


class GoldenPatient(BaseModel):
    """Expected patient fields. None means 'correct answer is absent'."""

    age_years: int | None = None
    sex: str | None = None
    initials: str | None = None


class GoldenExpected(BaseModel):
    suspect_drug: str
    patient: GoldenPatient
    reporter_category: str          # canonical: physician|pharmacist|nurse|consumer|other_hcp
    is_complete: bool
    seriousness_facts: dict[str, bool]


class GoldenCase(BaseModel):
    """One human-verified answer key. Ground truth about the SOURCE,
    authored independently of any system output (see ADR 0008)."""

    source: str
    expected: GoldenExpected
    # Field paths where ANY non-null system value is a hallucination failure.
    must_not_invent: list[str] = Field(default_factory=list)
    notes: str = ""


class FieldResult(BaseModel):
    """One field's verdict. Scorecard cell, not pass/fail gate."""

    field: str
    expected: str            # stringified for uniform reporting
    actual: str
    passed: bool
    is_hallucination: bool = False   # failed specifically by inventing data


class CaseEvalResult(BaseModel):
    """Scorecard for one extraction run against one golden case."""

    source: str
    fields: list[FieldResult]

    @property
    def passed_all(self) -> bool:
        return all(f.passed for f in self.fields)

    @property
    def hallucinations(self) -> list[FieldResult]:
        return [f for f in self.fields if f.is_hallucination]