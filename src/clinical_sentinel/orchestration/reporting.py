"""Reporting orchestration: draft a regulatory narrative for one case.

The human gate, enforced architecturally: the agent is read-only, the
draft is persisted to pending_review/ by SYSTEM code, and promotion
out of review exists only as a human CLI action (see approve command).
"""

import json

from claude_agent_sdk import ClaudeAgentOptions, HookMatcher, query

from clinical_sentinel.config import get_settings
from clinical_sentinel.models.report import RegulatoryDraft, ReportNarrative
from clinical_sentinel.models.severity import SeverityAssessment
from clinical_sentinel.orchestration.intake import _extract_json, _make_tool_audit_hook
from clinical_sentinel.persistence.audit import AuditLog

EXPEDITED_DAYS = 15  # ICH E2A expedited reporting window for serious cases


def _build_prompt(case_id: str) -> str:
    schema = json.dumps(ReportNarrative.model_json_schema(), indent=2)
    return (
        "Use the regulatory-reporter agent to draft the case narrative for "
        f"the case at case_files/{case_id}.json, using its assessment at "
        f"case_files/{case_id}-assessment.json.\n\n"
        "Return ONLY a JSON object (no prose, no markdown fences) "
        f"conforming exactly to this JSON schema:\n\n{schema}"
    )


async def run_draft(case_id: str) -> RegulatoryDraft:
    """Draft a report for an assessed case; persist to pending_review/."""
    settings = get_settings()
    audit = AuditLog(settings.audit_dir)

    # Fail fast: the assessment must exist BEFORE we spend an agent run.
    assessment_path = settings.case_files_dir / f"{case_id}-assessment.json"
    if not assessment_path.exists():
        raise FileNotFoundError(
            f"No assessment for {case_id}. Run: clinical-sentinel assess {case_id}"
        )
    assessment = SeverityAssessment.model_validate_json(assessment_path.read_text())

    case_payload = json.loads((settings.case_files_dir / f"{case_id}.json").read_text())

    options = ClaudeAgentOptions(
        model=settings.model,
        cwd=settings.agent_workspace,
        setting_sources=["project"],
        allowed_tools=["Read", "Agent"],   # read-only agent — the gate, part 1
        hooks={
            "PostToolUse": [
                HookMatcher(matcher="Read|Glob", hooks=[_make_tool_audit_hook(audit)])
            ]
        },
    )

    result_text: str | None = None
    async for message in query(prompt=_build_prompt(case_id), options=options):
        if hasattr(message, "result") and message.result:
            result_text = message.result
    if result_text is None:
        raise RuntimeError(f"Agent produced no result for case {case_id}")

    narrative = ReportNarrative.model_validate_json(_extract_json(result_text))

    # SYSTEM facts: expedited status from the deterministic verdict,
    # deadline from arithmetic — the LLM contributed narrative only.
    from datetime import date, timedelta
    received = date.fromisoformat(case_payload["received_date"])
    expedited = assessment.classification.is_serious
    draft = RegulatoryDraft(
        case_id=case_id,
        is_expedited=expedited,
        reporting_deadline=received + timedelta(days=EXPEDITED_DAYS) if expedited else None,
        narrative=narrative.narrative,
    )

    pending = settings.workspace_dir / "pending_review"
    pending.mkdir(exist_ok=True)
    (pending / f"{case_id}-draft.json").write_text(draft.model_dump_json(indent=2))
    audit.record(
        event_type="report_drafted",
        actor="system:reporting",
        detail={"case_id": case_id, "is_expedited": expedited,
                "deadline": str(draft.reporting_deadline)},
    )
    return draft