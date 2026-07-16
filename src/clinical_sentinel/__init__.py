"""Clinical Sentinel: multi-agent pharmacovigilance triage on the Claude Agent SDK."""

import asyncio

from clinical_sentinel.orchestration.intake import run_intake


def main() -> None:
    """Temporary: run intake on report_001 end to end. Real CLI comes later."""
    extraction = asyncio.run(run_intake("report_001.txt"))
    print(f"complete: {extraction.is_complete()}")
    print(f"drug:     {extraction.suspect_drug}")
    print(f"patient:  age={extraction.patient.age_years} sex={extraction.patient.sex}")
    print(f"event:    {extraction.event_description}")
    print(f"missing:  {extraction.missing_elements or 'none'}")
    print(f"quotes:   {len(extraction.supporting_quotes)} supporting quote(s)")