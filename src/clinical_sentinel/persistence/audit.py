"""Append-only audit log — the compliance trail (Principle 8).

One JSONL file, one JSON object per line, append-only by construction:
we open in 'a' mode and never expose an update or delete operation.
JSONL because append is atomic-enough per line, greppable, and each
line is independently parseable — the format regulators' auditors
and log pipelines both love.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from clinical_sentinel._trace import trace


class AuditLog:
    """Writes structured audit events. No read/update/delete API — by design."""

    def __init__(self, audit_dir: Path) -> None:
        audit_dir.mkdir(parents=True, exist_ok=True)
        self._path = audit_dir / "audit_log.jsonl"

    def record(self, event_type: str, actor: str, detail: dict) -> None:
        """Append one audit event.

        actor: 'system' for deterministic code paths, or the agent name
        for agent-initiated actions — WHO did it is first-class data.
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),  # UTC, always
            "event_type": event_type,
            "actor": actor,
            "detail": detail,
        }
        with self._path.open("a") as f:
            f.write(json.dumps(entry) + "\n")
        trace("AUDIT", "AuditLog.record", f"{event_type} actor={actor} detail={detail}")