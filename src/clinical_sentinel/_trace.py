"""Runtime execution tracer — opt-in "console.log" for the pipeline.

Prints one line per meaningful step to STDERR, gated by the CS_TRACE
environment variable. STDERR (not stdout) because the CLI's stdout is
the machine-readable payload — tests and pipes must not see trace noise.

Color coding matches docs/architecture/architecture-process-flow.md, so
what you see in the terminal maps 1:1 to boxes in the diagrams:

    [SYSTEM   ] 🔵 blue          — deterministic Python code
    [AGENT    ] 🟠 amber         — LLM subagent work
    [VALIDATOR] 🔴 red           — Pydantic boundary
    [AUDIT    ] 🟣 magenta       — append-only compliance events
    [STORAGE  ] ⚪ gray          — filesystem read/write
    [HUMAN    ] 🟢 green         — CLI action initiated by a human
    [EVAL     ] 🧪 bright purple — offline measurement layer (not runtime)

Each line ALSO carries the caller's source file and line number,
auto-detected from the stack frame — so the physical location of the
trace call is one glance away, independent of the logical `where`
label the caller passes in. Example:

    [VALIDATOR] 🔴 clinical_sentinel/orchestration/intake.py:105  IntakeExtraction.model_validate_json — crossing the boundary
                    └── physical source (dimmed)                  └── logical `where` label

Usage:
    from clinical_sentinel._trace import trace
    trace("SYSTEM", "run_intake", f"processing {filename}")

Enable at the shell:
    CS_TRACE=1 uv run clinical-sentinel report_001.txt

Disable colors (piping, CI):
    NO_COLOR=1 CS_TRACE=1 uv run clinical-sentinel report_001.txt
"""

import os
import sys
from typing import Literal

# Read once at import — the tracer is a fact about this process, not
# mutable state. Re-import (rare) picks up changes.
_ENABLED: bool = os.environ.get("CS_TRACE", "").lower() in ("1", "true", "yes", "on")
_NO_COLOR: bool = os.environ.get("NO_COLOR") is not None or not sys.stderr.isatty()

Actor = Literal["SYSTEM", "AGENT", "VALIDATOR", "AUDIT", "STORAGE", "HUMAN", "EVAL"]

# Actor → (emoji, ANSI color) — colors chosen to match the process-flow
# doc; emoji provided so NO_COLOR mode still visually distinguishes actors.
# EVAL uses bright-magenta and 🧪 to stay in the "purple" family of the
# doc while remaining visually distinct from AUDIT (regular magenta / 🟣).
_STYLES: dict[str, tuple[str, str]] = {
    "SYSTEM":    ("🔵", "\033[36m"),  # cyan
    "AGENT":     ("🟠", "\033[33m"),  # yellow
    "VALIDATOR": ("🔴", "\033[31m"),  # red
    "AUDIT":     ("🟣", "\033[35m"),  # magenta
    "STORAGE":   ("⚪", "\033[90m"),  # bright black (gray)
    "HUMAN":     ("🟢", "\033[32m"),  # green
    "EVAL":      ("🧪", "\033[95m"),  # bright magenta (purple)
}
_RESET = "\033[0m"
_DIM = "\033[2m"

# Package-relative trim marker: anything before "clinical_sentinel/" is
# noise (the checkout path varies per machine); anything from it onward
# uniquely identifies a source file within the package.
_PKG_MARKER = "clinical_sentinel" + os.sep


def _caller_location(depth: int = 2) -> str:
    """Return e.g. 'clinical_sentinel/orchestration/intake.py:105' from the caller.

    depth=2 skips this function's frame AND trace()'s frame, so the
    reported location is where `trace()` was actually written — not
    the tracer plumbing. Best-effort: if frame introspection fails
    for any reason we return '?' rather than crash the caller.
    """
    try:
        frame = sys._getframe(depth)
        filename = frame.f_code.co_filename
        lineno = frame.f_lineno
        idx = filename.rfind(_PKG_MARKER)
        path = filename[idx:] if idx != -1 else os.path.basename(filename)
        return f"{path}:{lineno}"
    except Exception:
        return "?"


def trace(actor: Actor, where: str, msg: str = "") -> None:
    """Emit one flow line to stderr; no-op unless CS_TRACE is set.

    actor: which layer is speaking (matches process-flow doc colors)
    where: logical label — Class.method or function being described
    msg:   optional detail — values crossed, decisions taken, transitions

    The physical source file:line is auto-detected from the call stack
    and rendered in dimmed color between the actor tag and `where`.
    """
    if not _ENABLED:
        return
    emoji, color = _STYLES[actor]
    tag = f"[{actor:<9}]"
    loc = _caller_location()
    if not _NO_COLOR:
        tag = f"{color}{tag}{_RESET}"
        loc = f"{_DIM}{loc}{_RESET}"
    tail = f" — {msg}" if msg else ""
    print(f"{tag} {emoji} {loc}  {where}{tail}", file=sys.stderr)


def is_enabled() -> bool:
    """Cheap check for callers that want to skip expensive formatting."""
    return _ENABLED
