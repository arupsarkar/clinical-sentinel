# Clinical Sentinel

Multi-agent pharmacovigilance (PV) triage system built on the
[Claude Agent SDK](https://code.claude.com/docs/en/agent-sdk/overview).
- [Design principles](docs/architecture/design-principles.md) — the rules every component follows

> **Status:** 🚧 Active development — this README is a living document.

## What it does

Pharmaceutical companies are legally required to monitor the safety of
their medicines. Adverse event (AE) reports — a patient's side effect
described in a call transcript, a physician's email, a faxed form —
must be triaged, assessed for seriousness, and reported to regulators
(e.g., the FDA) within strict deadlines, some as short as 15 days.

Clinical Sentinel automates the first mile of that workflow with a
team of specialized AI agents, while keeping humans in control of
every consequential decision:

- **Intake Agent** — extracts a structured, validated case from raw
  unstructured text
- **Severity Assessor** — applies regulatory seriousness criteria via
  deterministic scoring
- **Signal Checker** — verifies events against known drug label information
- **Regulatory Reporter** — drafts expedited reports in plan mode,
  requiring human approval before anything is submitted

## Scope & progress

**v0.1 goal:** an end-to-end demonstration — raw report → validated
intake → persisted case → audited trail → severity assessment →
human-gated regulatory draft. A demo of architecture, not a product.

| # | Workstream | Status |
|---|-----------|--------|
| 1 | Foundation (config, domain models, tests, docs) | ✅ Done |
| 2 | Intake agent (extraction with honesty guarantees) | ✅ Done |
| 3 | Case persistence (system-minted IDs, provenance) | 🔨 In progress |
| 4 | Audit trail via deterministic hooks | ⬜ Planned |
| 5 | Severity assessor agent | ⬜ Planned |
| 6 | Regulatory reporter (plan mode, human-gated) | ⬜ Planned |
| 7 | CLI polish + architecture docs | ⬜ Planned |

**Overall: ~71%** · Deliberately out of scope: see
[ADR 0005](docs/adr/0005-scope-freeze-v0-1.md).  

## Why it's built this way

Safety controls here are **architecture, not prompts**:

- Deterministic hooks create an audit trail of every file the agents touch
- Plan mode gates regulatory actions behind human review
- Structured outputs guarantee validated data payloads, not free text
- An immutable configuration layer fails fast on broken environments

## Quickstart

```bash
# Requires Python 3.12+ and uv (https://docs.astral.sh/uv/)
git clone <repo-url> && cd clinical-sentinel
cp .env.example .env       # add your ANTHROPIC_API_KEY
uv sync                    # reproduce the exact locked environment
uv run clinical-sentinel   # smoke test
```

## Architecture

*(Diagram forthcoming — see [docs/architecture](docs/architecture/) for the current design.)*

## Documentation

- [Architecture overview](docs/architecture/overview.md)
- [Architecture Decision Records](docs/adr/) — why the system is shaped the way it is

## License

TBD