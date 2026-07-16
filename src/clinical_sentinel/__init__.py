"""Clinical Sentinel: multi-agent pharmacovigilance triage on the Claude Agent SDK."""

import asyncio
import sys

from clinical_sentinel.config import get_settings
from clinical_sentinel.orchestration.intake import run_intake
from clinical_sentinel.orchestration.severity import run_assessment
from clinical_sentinel.persistence.audit import AuditLog
from clinical_sentinel.persistence.case_store import CaseStore

USAGE = """usage:
  clinical-sentinel <report_filename>     intake one report from the queue
  clinical-sentinel assess <case_id>      assess seriousness of one case"""


def _intake_command(report_filename: str) -> None:
    """Intake one report: extract, display, and persist if complete."""
    extraction = asyncio.run(run_intake(report_filename))

    print(f"complete: {extraction.is_complete()}")
    print(f"drug:     {extraction.suspect_drug}")
    print(
        f"patient:  age={extraction.patient.age_years} "
        f"sex={extraction.patient.sex} initials={extraction.patient.initials}"
    )
    print(f"event:    {extraction.event_description}")
    print(f"missing:  {extraction.missing_elements or 'none'}")
    print(f"reporter: {extraction.reporter_type}")

    if extraction.is_complete():
        settings = get_settings()
        audit = AuditLog(settings.audit_dir)
        store = CaseStore(settings.case_files_dir, audit_log=audit)
        case = store.create_case(extraction, source_file=report_filename)
        print(f"case created: {case.case_id}")
    else:
        print("no case created: extraction incomplete — routed for human follow-up")

    for q in extraction.supporting_quotes:
        print(f'  quote: {q}')


def _assess_command(case_id: str) -> None:
    """Assess one persisted case against the seriousness criteria."""
    assessment = asyncio.run(run_assessment(case_id))

    print(f"serious:   {assessment.classification.is_serious}")
    print(f"criteria:  {[c.value for c in assessment.classification.criteria_met] or 'none'}")
    for criterion, quote in assessment.supporting_evidence.items():
        print(f'  {criterion}: "{quote}"')


def main() -> None:
    """CLI entry point: parse argv and dispatch to exactly one command.

    Deliberately minimal argv handling — a real CLI framework (typer)
    is workstream 7. The dispatch pattern still applies there: parse,
    route to one handler, exit; handlers never see raw argv.
    """
    args = sys.argv[1:]

    if len(args) == 2 and args[0] == "assess":
        _assess_command(args[1])
        return

    if len(args) == 1:
        _intake_command(args[0])
        return

    print(USAGE, file=sys.stderr)
    raise SystemExit(2)  # exit code 2 = usage error, Unix convention