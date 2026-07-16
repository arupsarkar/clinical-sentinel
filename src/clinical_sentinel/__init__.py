"""Clinical Sentinel: multi-agent pharmacovigilance triage on the Claude Agent SDK."""

from clinical_sentinel.config import get_settings


def main() -> None:
    """Temporary smoke test: prove config loads and the environment is sane.

    This will become the real CLI entry point in a later chunk.
    """
    settings = get_settings()
    print(f"clinical-sentinel configured — model: {settings.model}")