"""Severity orchestration: run the severity-assessor agent on one case file.

Same architecture as intake — model, prompt with injected schema, agent,
validated boundary — because the pattern IS the point: every agent in
this system enters and exits through the same door.
"""

import json

from claude_agent_sdk import ClaudeAgentOptions, HookMatcher, query

from clinical_sentinel.config import get_settings
from clinical_sentinel.models.severity import SeverityAssessment
from clinical_sentinel.orchestration.intake import _extract_json, _make_tool_audit_hook
from clinical_sentinel.persistence.audit import AuditLog


def _build_prompt(case_id: str) -> str:
    schema = json.dumps(SeverityAssessment.model_json_schema(), indent=2)
    return (
        "Use the severity-assessor agent to assess the case at "
        f"case_files/{case_id}.json.\n\n"
        "Return ONLY a JSON object (no prose, no markdown fences) "
        "conforming exactly to this JSON schema:\n\n"
        f"{schema}"
    )


async def run_assessment(case_id: str) -> SeverityAssessment:
    """Assess one persisted case; return a validated assessment."""
    settings = get_settings()
    audit = AuditLog(settings.audit_dir)

    options = ClaudeAgentOptions(
        model=settings.model,
        cwd=settings.agent_workspace,
        setting_sources=["project"],
        # Bash is new here: the assessor must run the rulebook script.
        allowed_tools=["Read", "Bash", "Agent"],
        hooks={
            "PostToolUse": [
                # Bash added to the matcher: script executions are audited too.
                HookMatcher(matcher="Read|Glob|Bash", hooks=[_make_tool_audit_hook(audit)])
            ]
        },
    )

    result_text: str | None = None
    async for message in query(prompt=_build_prompt(case_id), options=options):
        if hasattr(message, "result") and message.result:
            result_text = message.result

    if result_text is None:
        raise RuntimeError(f"Agent produced no result for case {case_id}")

    return SeverityAssessment.model_validate_json(_extract_json(result_text))