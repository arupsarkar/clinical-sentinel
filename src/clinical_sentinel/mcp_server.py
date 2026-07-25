"""MCP server: Clinical Sentinel as an operator console surface.

Exposes the pipeline as MCP tools so any MCP client — Claude Code for
the demo — can operate the system conversationally. Design decisions
(ADR 0009):

1. NO approve tool. The human gate (Principle 7) survives into this
   surface by omission: the MCP layer physically cannot promote a
   draft. Approval remains a human-only CLI action.
2. stdio transport: the client launches this server as a subprocess;
   no ports, no hosting — right-sized for a local operator console.
3. Tools RETURN text, never print. stdio transport owns stdout for
   protocol frames; anything we print corrupts the stream. (Our trace
   module writes to stderr, so CS_TRACE stays safe.)
4. Every tool invocation is itself audited (actor: operator:mcp) —
   the trail now shows WHO ASKED, not just what happened.
"""

import json

from mcp.server.fastmcp import FastMCP

from clinical_sentinel.config import get_settings
from clinical_sentinel.orchestration.intake import run_intake
from clinical_sentinel.orchestration.reporting import run_draft
from clinical_sentinel.orchestration.severity import run_assessment
from clinical_sentinel.persistence.audit import AuditLog
from clinical_sentinel.persistence.case_store import CaseStore

mcp = FastMCP("clinical-sentinel")


def _audit_operator(tool: str, detail: dict) -> None:
    """Record that an MCP operator invoked a tool — the surface is audited too."""
    settings = get_settings()
    AuditLog(settings.audit_dir).record(
        event_type="operator_tool_invoked",
        actor="operator:mcp",
        detail={"tool": tool, **detail},
    )


@mcp.tool()
async def clinical_sentinel_intake(report_filename: str) -> str:
    """Process one raw adverse event report from the intake queue.

    Extracts structured case data via the intake-specialist agent,
    validates it at the schema boundary, and — if the four regulatory
    minimum elements are present — persists a case with a
    system-minted ID. Incomplete extractions do NOT create a case.

    Args:
        report_filename: file name inside workspace/intake_queue/,
            e.g. 'report_002.txt'
    """
    _audit_operator("clinical_sentinel_intake", {"report": report_filename})

    # NOTE: await directly — we are inside the server's event loop;
    # asyncio.run() here would crash with 'loop already running'.
    extraction = await run_intake(report_filename)

    lines = [
        f"complete: {extraction.is_complete()}",
        f"drug: {extraction.suspect_drug}",
        f"patient: age={extraction.patient.age_years} "
        f"sex={extraction.patient.sex} initials={extraction.patient.initials}",
        f"reporter: {extraction.reporter_type}",
        f"event: {extraction.event_description}",
        f"missing: {extraction.missing_elements or 'none'}",
    ]

    if extraction.is_complete():
        settings = get_settings()
        store = CaseStore(
            settings.case_files_dir,
            audit_log=AuditLog(settings.audit_dir),
        )
        case = store.create_case(extraction, source_file=report_filename)
        lines.append(f"case_created: {case.case_id}")
    else:
        lines.append(
            "case_created: NONE — extraction incomplete, routed for human follow-up"
        )

    lines.append(f"supporting_quotes: {len(extraction.supporting_quotes)}")
    return "\n".join(lines)


@mcp.tool()
async def clinical_sentinel_assess(case_id: str) -> str:
    """Assess a persisted case against ICH E2A seriousness criteria.

    The severity-assessor agent establishes six factual answers from
    the case text; a deterministic script applies the regulatory
    rulebook. The assessment is persisted next to the case.

    Args:
        case_id: e.g. 'CS-2026-000001'
    """
    _audit_operator("clinical_sentinel_assess", {"case_id": case_id})

    assessment = await run_assessment(case_id)

    # Persist alongside the case (mirrors the CLI path — reporter needs it)
    settings = get_settings()
    path = settings.case_files_dir / f"{case_id}-assessment.json"
    path.write_text(assessment.model_dump_json(indent=2))
    AuditLog(settings.audit_dir).record(
        event_type="assessment_recorded",
        actor="system",
        detail={"case_id": case_id,
                "is_serious": assessment.classification.is_serious},
    )

    criteria = [c.value for c in assessment.classification.criteria_met]
    evidence = "\n".join(
        f"  {criterion}: \"{quote}\""
        for criterion, quote in assessment.supporting_evidence.items()
    )
    return (
        f"serious: {assessment.classification.is_serious}\n"
        f"criteria_met: {criteria or 'none'}\n"
        f"evidence:\n{evidence or '  (none)'}\n"
        f"assessment_recorded: {path.name}"
    )


@mcp.tool()
async def clinical_sentinel_draft(case_id: str) -> str:
    """Draft the regulatory report narrative for an ASSESSED case.

    The read-only regulatory-reporter agent writes the narrative; the
    SYSTEM computes the expedited flag and the 15-day deadline from the
    deterministic severity verdict. The draft lands in pending_review/.

    IMPORTANT: there is deliberately no approve tool on this server.
    Promotion out of pending_review/ is a human-only CLI action
    ('clinical-sentinel approve <case_id>') — tell the operator so if
    they ask you to approve.

    Args:
        case_id: an assessed case, e.g. 'CS-2026-000001'
    """
    _audit_operator("clinical_sentinel_draft", {"case_id": case_id})

    draft = await run_draft(case_id)
    return (
        f"draft: pending_review/{draft.case_id}-draft.json\n"
        f"is_expedited: {draft.is_expedited}\n"
        f"reporting_deadline: {draft.reporting_deadline}\n"
        f"status: PENDING HUMAN REVIEW — approval is a human-only CLI "
        f"action and cannot be performed through this interface"
    )


@mcp.tool()
def clinical_sentinel_list_pending() -> str:
    """List drafts awaiting human review in pending_review/."""
    _audit_operator("clinical_sentinel_list_pending", {})

    settings = get_settings()
    pending = settings.workspace_dir / "pending_review"
    if not pending.exists():
        return "pending_review: (empty)"

    entries = []
    for path in sorted(pending.glob("*-draft.json")):
        payload = json.loads(path.read_text())
        entries.append(
            f"{payload['case_id']}  expedited={payload['is_expedited']}  "
            f"deadline={payload['reporting_deadline']}"
        )
    return "\n".join(entries) if entries else "pending_review: (empty)"


@mcp.tool()
def clinical_sentinel_audit_tail(n: int = 10) -> str:
    """Show the last n audit trail entries (append-only JSONL, UTC).

    The trail records four actor classes: agent:* (tool use by
    subagents), system:* (deterministic decisions), operator:mcp
    (requests through this interface), and human:cli (approvals).

    Args:
        n: number of trailing entries to return (default 10)
    """
    settings = get_settings()
    log_path = settings.audit_dir / "audit_log.jsonl"
    if not log_path.exists():
        return "audit log: (empty)"

    lines = log_path.read_text().strip().splitlines()[-n:]
    out = []
    for line in lines:
        e = json.loads(line)
        out.append(
            f"{e['timestamp']}  {e['event_type']:24s} "
            f"actor={e['actor']:24s} {json.dumps(e['detail'])}"
        )
    return "\n".join(out)


if __name__ == "__main__":
    mcp.run()   # stdio transport by default — the client launches us