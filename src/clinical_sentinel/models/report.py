"""Regulatory report draft model.

Principle 3 reprise: the DEADLINE is a system fact — computed from the
case's received date and the deterministic seriousness verdict, never
by the LLM. The agent contributes exactly one thing: the narrative.
"""

from datetime import date

from pydantic import BaseModel, Field


class ReportNarrative(BaseModel):
    """What the reporter agent RETURNS: language work only."""

    narrative: str = Field(min_length=1, description="Regulatory case narrative")


class RegulatoryDraft(BaseModel):
    """The assembled draft awaiting HUMAN review. System-owned facts + narrative."""

    case_id: str
    is_expedited: bool                    # serious ⇒ expedited timeline
    reporting_deadline: date | None       # received_date + 15 days if expedited
    narrative: str
    status: str = "pending_review"        # → "approved" only via human command