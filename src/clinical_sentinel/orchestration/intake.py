"""Intake orchestration: run the intake-specialist agent on one report.

The orchestrator owns everything deterministic (file selection, schema
contract, validation). The agent owns exactly one thing: language
understanding. Output crosses back into our system ONLY through
Pydantic validation — Principle 1 and Principle 8.
"""

import json
from pathlib import Path
from clinical_sentinel._trace import trace
from clinical_sentinel.config import get_settings
from clinical_sentinel.models.intake import IntakeExtraction
from claude_agent_sdk import ClaudeAgentOptions, HookMatcher, query
from clinical_sentinel.persistence.audit import AuditLog


def _build_prompt(report_filename: str) -> str:
    """Assemble the task prompt: which file, and the exact JSON contract.

    We inject the Pydantic-generated JSON schema so the agent's contract
    and our validator are THE SAME object — they cannot drift apart.
    """
    schema = json.dumps(IntakeExtraction.model_json_schema(), indent=2)
    return (
        "Use the intake-specialist agent to process the report at "
        f"intake_queue/{report_filename}.\n\n"
        "Return ONLY a JSON object (no prose, no markdown fences) "
        "conforming exactly to this JSON schema:\n\n"
        f"{schema}"
    )


def _extract_json(raw: str) -> str:
    """Tolerate the common LLM tic of wrapping JSON in ```json fences."""
    text = raw.strip()
    if text.startswith("```"):
        # Drop the first fence line and the trailing fence.
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return text


def _make_tool_audit_hook(audit: AuditLog):
    """Build a PostToolUse hook that records every agent tool call.

    Deterministic by construction: the SDK invokes this on EVERY matching
    tool use — the agent cannot skip, forget, or be prompted out of it.
    Closure over `audit` = dependency injection for hooks.
    """

    async def log_tool_use(input_data, tool_use_id, context):
        tool = input_data.get("tool_name", "unknown")
        fp = input_data.get("tool_input", {}).get("file_path")
        trace("AGENT", "PostToolUse hook", f"tool={tool} file={fp}")
        audit.record(
            event_type="agent_tool_use",
            actor="agent:intake-specialist",
            detail={
                "tool": tool,
                # Log WHICH file was touched — but never file CONTENTS:
                # audit logs must not become a second copy of patient data.
                "file_path": fp,
            },
        )
        return {}  # empty dict = observe only, don't block or modify

    return log_tool_use

async def run_intake(report_filename: str) -> IntakeExtraction:
    """Process one intake document; return a VALIDATED extraction.

    Raises pydantic.ValidationError if the agent's output does not
    conform — bad output dies here, at the boundary, never downstream.
    """
    trace("SYSTEM", "run_intake", f"processing intake_queue/{report_filename}")
    settings = get_settings()
    audit = AuditLog(settings.audit_dir)

    trace("SYSTEM", "run_intake", "building prompt with injected IntakeExtraction schema")
    options = ClaudeAgentOptions(
        model=settings.model,
        cwd=settings.agent_workspace,      # the SDK's world = our workspace/
        setting_sources=["project"],        # REQUIRED to load .claude/agents/
                                            # and CLAUDE.md from that cwd —
                                            # without this the SDK runs in
                                            # isolation mode (cookbook lesson)
        allowed_tools=["Read", "Glob", "Agent"],  # Agent = the subagent
                                                  # invocation tool itself
        hooks={
            "PostToolUse": [
                HookMatcher(matcher="Read|Glob", hooks=[_make_tool_audit_hook(audit)])
            ]
        },                                                  
    )

    trace("AGENT", "run_intake", "invoking intake-specialist via SDK query()")
    result_text: str | None = None
    async for message in query(prompt=_build_prompt(report_filename), options=options):
        # The stream yields many message types (init, tool use, thinking).
        # The final ResultMessage carries `.result` — that's our payload.
        if hasattr(message, "result") and message.result:
            result_text = message.result

    if result_text is None:
        trace("SYSTEM", "run_intake", "no result from agent — raising")
        raise RuntimeError(f"Agent produced no result for {report_filename}")

    trace("VALIDATOR", "IntakeExtraction.model_validate_json", "crossing the boundary")
    # THE boundary: free text becomes typed, validated domain data — or dies.
    extraction = IntakeExtraction.model_validate_json(_extract_json(result_text))
    trace("SYSTEM", "run_intake", f"validated — is_complete={extraction.is_complete()}")
    return extraction


    