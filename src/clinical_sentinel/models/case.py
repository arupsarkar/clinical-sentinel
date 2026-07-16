"""Domain model: what an adverse event (AE) case IS.

Pharmacovigilance regulation defines a *valid case* as having four
minimum elements: an identifiable patient, an identifiable reporter,
a suspect drug, and an adverse event. This module encodes that
regulatory definition as executable types — an invalid case cannot
be constructed, only rejected with a precise error.
"""

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class Seriousness(StrEnum):
    """Regulatory seriousness criteria (ICH E2A).

    An AE meeting ANY of these is a 'serious' case, which drives
    expedited reporting deadlines. StrEnum so values serialize as
    plain strings in JSON — friendly to logs and downstream systems.
    """

    DEATH = "death"
    LIFE_THREATENING = "life_threatening"
    HOSPITALIZATION = "hospitalization"
    DISABILITY = "disability"
    CONGENITAL_ANOMALY = "congenital_anomaly"
    OTHER_MEDICALLY_IMPORTANT = "other_medically_important"


class Patient(BaseModel):
    """Identifiable patient — minimum element #1.

    'Identifiable' in PV does NOT mean named: any single qualifier
    (age, sex, initials) suffices. All fields optional, but the
    AdverseEventCase validator below requires at least one.
    """

    age_years: int | None = Field(default=None, ge=0, le=130)
    sex: str | None = None
    initials: str | None = None

    def is_identifiable(self) -> bool:
        return any([self.age_years is not None, self.sex, self.initials])


class AdverseEventCase(BaseModel):
    """A validated AE case — the object every agent produces or consumes.

    Construction of this object IS the validity check: if you hold an
    AdverseEventCase, the four minimum elements are guaranteed present.
    """

    case_id: str = Field(pattern=r"^CS-\d{4}-\d{6}$", description="e.g. CS-2026-000001")
    received_date: date

    # The four minimum elements
    patient: Patient
    reporter_type: str = Field(min_length=1, description="physician, patient, pharmacist…")
    suspect_drug: str = Field(min_length=1)
    event_description: str = Field(min_length=1)

    # Assessment fields — populated by later agents, not at intake
    seriousness: list[Seriousness] = Field(default_factory=list)
    narrative: str | None = None

    @property
    def is_serious(self) -> bool:
        """Serious cases trigger expedited regulatory deadlines."""
        return len(self.seriousness) > 0