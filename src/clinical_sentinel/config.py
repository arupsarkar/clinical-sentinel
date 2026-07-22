"""Application configuration for Clinical Sentinel.

Single source of truth for all runtime settings. Every module that
needs configuration imports from here — nothing else in the codebase
reads environment variables directly. This gives us one choke point
for validation, defaults, and (later) per-environment overrides.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

from clinical_sentinel._trace import trace

# Load .env into process environment variables at import time.
# Safe to call even if no .env file exists (e.g., in CI where
# variables are injected directly) — it simply does nothing.
load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Immutable runtime settings.

    frozen=True makes instances read-only after creation: configuration
    is a fact about the run, not mutable state. Any code that tries to
    modify settings at runtime raises an error — a bug caught early.
    """

    # The model our agents run on. Centralized here so a model upgrade
    # is a one-line change, not a codebase-wide hunt.
    model: str = "claude-sonnet-4-6"

    # Working directory for agent filesystem context (CLAUDE.md, .claude/).
    # Relative to the project root; resolved properly in later chunks.
    agent_workspace: str = "workspace"

    @property
    def workspace_dir(self) -> Path:
        return Path(self.agent_workspace)

    @property
    def audit_dir(self) -> Path:
        return self.workspace_dir / "audit"

    @property
    def case_files_dir(self) -> Path:
        return self.workspace_dir / "case_files"

    @property
    def intake_queue_dir(self) -> Path:
        return self.workspace_dir / "intake_queue"    


def get_settings() -> Settings:
    """Build and validate settings; fail fast if the environment is broken.

    We check for the API key here — at startup — rather than letting the
    SDK fail mid-run with a confusing error deep inside an agent loop.
    'Fail fast, fail loud, fail at the boundary' is the pattern.

    Note: we deliberately do NOT store the key on Settings. The SDK reads
    ANTHROPIC_API_KEY from the environment on its own; keeping the secret
    out of our objects means it can't leak via logging or repr().
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        trace("SYSTEM", "get_settings", "ANTHROPIC_API_KEY missing — failing fast")
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. "
            "Copy .env.example to .env and add your key."
        )
    settings = Settings()
    trace(
        "SYSTEM",
        "get_settings",
        f"model={settings.model} workspace={settings.workspace_dir}",
    )
    return settings