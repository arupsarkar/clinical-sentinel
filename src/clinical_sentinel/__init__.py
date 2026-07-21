"""Clinical Sentinel: multi-agent pharmacovigilance triage on the Claude Agent SDK."""

import asyncio
import json
import sys

from clinical_sentinel.config import get_settings
from clinical_sentinel.orchestration.intake import run_intake
from clinical_sentinel.orchestration.severity import run_assessment
from clinical_sentinel.persistence.audit import AuditLog
from clinical_sentinel.persistence.case_store import CaseStore
from clinical_sentinel.orchestration.reporting import run_draft

USAGE = """usage:
  clinical-sentinel <report_filename>     intake one report from the queue
  clinical-sentinel assess <case_id>      assess seriousness of one case
  clinical-sentinel draft <case_id>       draft regulatory report (pending review)
  clinical-sentinel approve <case_id>     approve a pending draft (human gate)"""


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

    # Persist the assessment next to its case — the reporter consumes both.
    settings = get_settings()
    path = settings.case_files_dir / f"{case_id}-assessment.json"
    path.write_text(assessment.model_dump_json(indent=2))
    AuditLog(settings.audit_dir).record(
        event_type="assessment_recorded",
        actor="system",
        detail={"case_id": case_id, "is_serious": assessment.classification.is_serious},
    )
    print(f"assessment recorded: {path.name}")        

def _draft_command(case_id: str) -> None:
    """Draft a regulatory report; lands in pending_review/, never beyond."""
    draft = asyncio.run(run_draft(case_id))
    print(f"draft:     pending_review/{draft.case_id}-draft.json")
    print(f"expedited: {draft.is_expedited}  deadline: {draft.reporting_deadline}")
    print("status:    PENDING HUMAN REVIEW — use 'approve' after reading the draft")


def _approve_command(case_id: str) -> None:
    """THE HUMAN GATE: promote a reviewed draft. Only humans run this.

    The approval is itself an audited event with actor 'human:cli' —
    the third actor type in the trail, completing the cast: agents
    act, the system acts, and humans own the consequential step.
    """
    settings = get_settings()
    src = settings.workspace_dir / "pending_review" / f"{case_id}-draft.json"
    if not src.exists():
        print(f"no pending draft for {case_id}", file=sys.stderr)
        raise SystemExit(1)

    draft = json.loads(src.read_text())
    draft["status"] = "approved"
    approved_dir = settings.workspace_dir / "approved_reports"
    approved_dir.mkdir(exist_ok=True)
    (approved_dir / f"{case_id}-report.json").write_text(json.dumps(draft, indent=2))
    src.unlink()  # a draft cannot be both pending and approved

    AuditLog(settings.audit_dir).record(
        event_type="report_approved",
        actor="human:cli",
        detail={"case_id": case_id},
    )
    print(f"approved:  {case_id} — recorded with actor 'human:cli'")

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

    if len(args) == 2 and args[0] == "draft":
        _draft_command(args[1])
        return

    if len(args) == 2 and args[0] == "approve":
        _approve_command(args[1])
        return

    if len(args) == 1:
        _intake_command(args[0])
        return

    print(USAGE, file=sys.stderr)
    raise SystemExit(2)  # exit code 2 = usage error, Unix convention