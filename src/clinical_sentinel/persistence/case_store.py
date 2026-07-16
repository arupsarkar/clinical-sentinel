"""Case store: promote validated extractions into persisted case files.

THE SYSTEM mints case IDs and timestamps — never the LLM (Principle 3).
Case files are JSON on disk under workspace/case_files/, one file per
case, named by case ID for human browsability and audit friendliness.
"""

import json
from datetime import date
from pathlib import Path

from clinical_sentinel.models.case import AdverseEventCase
from clinical_sentinel.models.intake import IntakeExtraction
from clinical_sentinel.persistence.audit import AuditLog

class CaseStore:
    """Filesystem-backed store for adverse event cases."""

    def __init__(self, case_dir: Path, audit_log: AuditLog | None = None) -> None:
        self._case_dir = case_dir
        self._case_dir.mkdir(parents=True, exist_ok=True)
        self._audit = audit_log

    def _next_case_id(self) -> str:
        """Mint the next sequential ID: CS-<year>-<6-digit sequence>.

        Sequence = count of existing case files + 1. Simple and honest
        for a single-process demo; a real deployment would use a
        database sequence — that trade-off is documented in ADR form.
        """
        year = date.today().year
        existing = len(list(self._case_dir.glob("CS-*.json")))
        return f"CS-{year}-{existing + 1:06d}"

    def create_case(self, extraction: IntakeExtraction, source_file: str) -> AdverseEventCase:
        """Promote an extraction to a full case and persist it.

        Only COMPLETE extractions may become cases — the AdverseEventCase
        validators enforce the four minimum elements at construction, so
        an incomplete extraction fails here loudly, not downstream.
        """
        case = AdverseEventCase(
            case_id=self._next_case_id(),        # system fact: minted here
            received_date=date.today(),          # system fact: system clock
            patient=extraction.patient,
            reporter_type=extraction.reporter_type or "",  # "" fails min_length — good
            suspect_drug=extraction.suspect_drug or "",
            event_description=extraction.event_description or "",
        )

        path = self._case_dir / f"{case.case_id}.json"
        payload = case.model_dump(mode="json")
        payload["_source_file"] = source_file    # provenance: which intake doc
        path.write_text(json.dumps(payload, indent=2))
        if self._audit:
            self._audit.record(
                event_type="case_created",
                actor="system",
                detail={"case_id": case.case_id, "source_file": source_file},
            )        
        return case