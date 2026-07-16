"""Intake extraction model: what the Intake Agent RETURNS.

Deliberately narrower than AdverseEventCase. The agent extracts what
requires language understanding; the SYSTEM assigns identity and
timestamps. LLMs never mint case IDs, never read clocks — those are
facts the orchestrator controls deterministically.
"""

from pydantic import BaseModel, Field

from clinical_sentinel.models.case import Patient


class IntakeExtraction(BaseModel):
    """Raw extraction from one source document.

    All content fields optional: an incomplete report yields an
    incomplete extraction, and `missing_elements` makes the gaps
    first-class data instead of silent nulls.
    """

    patient: Patient = Field(default_factory=Patient)
    reporter_type: str | None = None
    suspect_drug: str | None = None
    event_description: str | None = None

    # Verbatim quotes supporting each extracted field — the agent must
    # show its work, enabling human spot-checks against the source.
    supporting_quotes: list[str] = Field(default_factory=list)

    # Which of the four minimum elements the agent could NOT find.
    missing_elements: list[str] = Field(default_factory=list)

    def is_complete(self) -> bool:
        """True when all four minimum elements were found."""
        return (
            self.patient.is_identifiable()
            and self.reporter_type is not None
            and self.suspect_drug is not None
            and self.event_description is not None
        )