"""Clinical Sentinel: multi-agent pharmacovigilance triage on the Claude Agent SDK."""

import asyncio
import sys

from clinical_sentinel.orchestration.intake import run_intake


def main() -> None:
    """Run intake on one report from the queue.

    Usage: clinical-sentinel <report_filename>
    Minimal argv handling for now; a real CLI framework (typer/argparse)
    arrives when subcommands do.
    """
    if len(sys.argv) != 2:
        print("usage: clinical-sentinel <report_filename>", file=sys.stderr)
        raise SystemExit(2)  # exit code 2 = usage error, Unix convention

    extraction = asyncio.run(run_intake(sys.argv[1]))
    print(f"complete: {extraction.is_complete()}")
    print(f"drug:     {extraction.suspect_drug}")
    print(f"patient:  age={extraction.patient.age_years} sex={extraction.patient.sex} initials={extraction.patient.initials}")
    print(f"event:    {extraction.event_description}")
    print(f"missing:  {extraction.missing_elements or 'none'}")
    print(f"reporter: {extraction.reporter_type}")
    for q in extraction.supporting_quotes:
        print(f"  quote: {q}")