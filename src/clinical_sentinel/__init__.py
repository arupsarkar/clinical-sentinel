"""Clinical Sentinel: multi-agent pharmacovigilance triage on the Claude Agent SDK."""

import asyncio
import json
import sys

from clinical_sentinel._trace import trace
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
  clinical-sentinel approve <case_id>     approve a pending draft (human gate)
  clinical-sentinel eval <report_filename> run the N=5 consistency eval for one report against its golden label"""


def _intake_command(report_filename: str) -> None:
    """Intake one report: extract, display, and persist if complete."""
    trace("SYSTEM", "_intake_command", f"start — report={report_filename}")
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
        trace("SYSTEM", "_intake_command", "extraction complete — persisting via CaseStore")
        settings = get_settings()
        audit = AuditLog(settings.audit_dir)
        store = CaseStore(settings.case_files_dir, audit_log=audit)
        case = store.create_case(extraction, source_file=report_filename)
        print(f"case created: {case.case_id}")
    else:
        trace("SYSTEM", "_intake_command", "extraction incomplete — no case created")
        print("no case created: extraction incomplete — routed for human follow-up")

    for q in extraction.supporting_quotes:
        print(f'  quote: {q}')


def _assess_command(case_id: str) -> None:
    """Assess one persisted case against the seriousness criteria."""
    trace("SYSTEM", "_assess_command", f"start — case_id={case_id}")
    assessment = asyncio.run(run_assessment(case_id))

    print(f"serious:   {assessment.classification.is_serious}")
    print(f"criteria:  {[c.value for c in assessment.classification.criteria_met] or 'none'}")
    for criterion, quote in assessment.supporting_evidence.items():
        print(f'  {criterion}: "{quote}"')

    # Persist the assessment next to its case — the reporter consumes both.
    settings = get_settings()
    path = settings.case_files_dir / f"{case_id}-assessment.json"
    path.write_text(assessment.model_dump_json(indent=2))
    trace("STORAGE", "_assess_command", f"wrote {path.name}")
    AuditLog(settings.audit_dir).record(
        event_type="assessment_recorded",
        actor="system",
        detail={"case_id": case_id, "is_serious": assessment.classification.is_serious},
    )
    print(f"assessment recorded: {path.name}")        

def _draft_command(case_id: str) -> None:
    """Draft a regulatory report; lands in pending_review/, never beyond."""
    trace("SYSTEM", "_draft_command", f"start — case_id={case_id}")
    draft = asyncio.run(run_draft(case_id))
    trace("SYSTEM", "_draft_command", "draft parked in pending_review/ — awaiting human")
    print(f"draft:     pending_review/{draft.case_id}-draft.json")
    print(f"expedited: {draft.is_expedited}  deadline: {draft.reporting_deadline}")
    print("status:    PENDING HUMAN REVIEW — use 'approve' after reading the draft")


def _approve_command(case_id: str) -> None:
    """THE HUMAN GATE: promote a reviewed draft. Only humans run this.

    The approval is itself an audited event with actor 'human:cli' —
    the third actor type in the trail, completing the cast: agents
    act, the system acts, and humans own the consequential step.
    """
    trace("HUMAN", "_approve_command", f"human gate opened for {case_id}")
    settings = get_settings()
    src = settings.workspace_dir / "pending_review" / f"{case_id}-draft.json"
    if not src.exists():
        trace("SYSTEM", "_approve_command", f"no pending draft at {src} — exit 1")
        print(f"no pending draft for {case_id}", file=sys.stderr)
        raise SystemExit(1)

    draft = json.loads(src.read_text())
    draft["status"] = "approved"
    approved_dir = settings.workspace_dir / "approved_reports"
    approved_dir.mkdir(exist_ok=True)
    approved_path = approved_dir / f"{case_id}-report.json"
    approved_path.write_text(json.dumps(draft, indent=2))
    trace("STORAGE", "_approve_command", f"wrote approved_reports/{approved_path.name}")
    src.unlink()  # a draft cannot be both pending and approved
    trace("STORAGE", "_approve_command", f"deleted pending_review/{src.name}")

    AuditLog(settings.audit_dir).record(
        event_type="report_approved",
        actor="human:cli",
        detail={"case_id": case_id},
    )
    print(f"approved:  {case_id} — recorded with actor 'human:cli'")

def _format_consistency_report_as_table(report) -> str:
    """Render a ConsistencyReport as the terminal table — as a string.

    Single source of truth for the layout: stdout AND the disk file
    are built from this same function, so the two can never drift.
    Change the columns here, both places update in lockstep.
    """
    lines = [
        f"source: {report.source}   trials: {report.trials}",
        f"{'field':<22} {'pass':>5} {'agree':>6} {'#vals':>6}  modal",
    ]
    for f in report.fields:
        lines.append(
            f"{f.field:<22} {f.pass_rate:>5.0%} {f.agreement_rate:>6.0%} "
            f"{f.distinct_values:>6}  {f.modal_value}"
        )
    lines.append(f"all trials passed: {report.all_trials_passed}")
    return "\n".join(lines)


def _eval_command(report_filename: str) -> None:
    """Run the N=5 consistency eval for one report against its golden label."""
    from datetime import datetime, timezone
    from pathlib import Path
    from clinical_sentinel.evals.models import GoldenCase
    from clinical_sentinel.evals.consistency import run_consistency

    trace("EVAL", "_eval_command", f"start — report={report_filename}")
    golden_path = Path("eval/golden") / report_filename.replace(".txt", ".json")
    trace("STORAGE", "_eval_command", f"reading golden {golden_path}")
    trace("VALIDATOR", "GoldenCase.model_validate_json", "validating golden label file")
    golden = GoldenCase.model_validate_json(golden_path.read_text())
    trace("EVAL", "_eval_command", f"golden loaded — must_not_invent={golden.must_not_invent or 'none'}")
    report = asyncio.run(run_consistency(golden, report_filename, n=5))
    trace(
        "EVAL",
        "_eval_command",
        f"final headline — all_trials_passed={report.all_trials_passed}",
    )

    # Render once, use twice — terminal and disk share the exact layout.
    table = _format_consistency_report_as_table(report)
    print(table)

    # Archive under workspace/ — same trust zone as case_files/, audit/,
    # pending_review/, approved_reports/. Golden fixtures live OUTSIDE
    # workspace (they are dev artifacts, not runtime state); eval outputs
    # are runtime state, so they belong inside. Timestamped per-run so
    # history is preserved and runs are diffable across time.
    evals_dir = get_settings().workspace_dir / "evals"
    evals_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")           # sortable, filesystem-safe
    report_stem = report_filename.replace(".txt", "")
    out_path = evals_dir / f"{report_stem}-{stamp}.txt"
    # Header carries the context the terminal implicitly has but a file does not.
    header = (
        f"# Consistency eval\n"
        f"# report:            {report_filename}\n"
        f"# golden:            {golden_path}\n"
        f"# generated (UTC):   {now.isoformat(timespec='seconds')}\n"
        f"# all_trials_passed: {report.all_trials_passed}\n"
        f"#\n"
    )
    out_path.write_text(header + table + "\n")
    trace("STORAGE", "_eval_command", f"wrote {out_path}")
    print(f"saved:  {out_path}")

def main() -> None:
    """CLI entry point: parse argv and dispatch to exactly one command.

    Deliberately minimal argv handling — a real CLI framework (typer)
    is workstream 7. The dispatch pattern still applies there: parse,
    route to one handler, exit; handlers never see raw argv.
    """
    args = sys.argv[1:]
    trace("HUMAN", "main", f"argv={args}")

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

    if len(args) == 2 and args[0] == "eval":
        _eval_command(args[1])
        return

    print(USAGE, file=sys.stderr)
    raise SystemExit(2)  # exit code 2 = usage error, Unix convention