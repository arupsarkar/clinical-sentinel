"""Severity assessment model: what the Severity Assessor RETURNS.

The agent establishes FACTS (six booleans, each with evidence);
the deterministic script produces the CLASSIFICATION. This model
captures both, keeping the fact/rule boundary visible in the data.
"""

from pydantic import BaseModel, Field

from clinical_sentinel.models.case import Seriousness


class SeriousnessFacts(BaseModel):
    """The agent's six factual determinations — the language-understanding half."""

    death: bool
    life_threatening: bool
    hospitalization: bool
    disability: bool
    congenital_anomaly: bool
    medically_important: bool


class Classification(BaseModel):
    """The script's verdict — the rulebook half. Mirrors scorer output."""

    is_serious: bool
    criteria_met: list[Seriousness] = Field(default_factory=list)


class SeverityAssessment(BaseModel):
    """Complete assessment: facts + evidence + deterministic verdict."""

    facts: SeriousnessFacts
    # Maps each TRUE criterion to the verbatim case language supporting it.
    supporting_evidence: dict[str, str] = Field(default_factory=dict)
    classification: Classification