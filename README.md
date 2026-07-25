# Clinical Sentinel

Multi-agent pharmacovigilance (PV) triage system built on the
[Claude Agent SDK](https://code.claude.com/docs/en/agent-sdk/overview),
operable from Claude Code via MCP.

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

- **Intake Specialist** — extracts a structured, validated case from
  raw unstructured text; absent data stays absent
- **Severity Assessor** — establishes facts from case text; a
  deterministic script applies the ICH E2A rulebook
- **Regulatory Reporter** — read-only agent drafts the narrative;
  the system computes deadlines; drafts await human approval
- **Human gate** — the only path to an approved report is a
  human-invoked CLI action, itself recorded in the audit trail
- **Eval harness** — golden-label scoring plus N-trial consistency
  measurement of the probabilistic layer

## Scope & progress

**Goal:** an end-to-end demonstration — raw report → validated intake
→ persisted case → audited trail → severity assessment → human-gated
regulatory draft → agent-operable via MCP. A demo of architecture,
not a product.

| # | Workstream | Status |
|---|-----------|--------|
| 1 | Foundation (config, domain models, tests, docs) | ✅ Done |
| 2 | Intake agent (extraction with honesty guarantees) | ✅ Done |
| 3 | Case persistence (system-minted IDs, provenance) | ✅ Done |
| 4 | Audit trail (SDK hooks + system events, append-only) | ✅ Done |
| 5 | Severity assessor (facts vs. deterministic rulebook) | ✅ Done |
| 6 | Regulatory reporter (human-gated draft/approve lifecycle) | ✅ Done |
| 7 | CLI polish + architecture docs | 🔨 Partial |
| 8 | MCP server (Claude Code as operator console) | 🔨 In progress |
| 9 | Eval harness (golden labels, consistency runner) | ✅ Done |

Deliberate cuts and deferrals: [ADR 0005](docs/adr/0005-scope-freeze-v0-1.md)
(signal-checker agent, dedup, production concerns) ·
[ADR 0006](docs/adr/0006-human-gate-over-plan-mode.md) (architectural
gate chosen over plan mode) · [ADR 0009](docs/adr/0009-mcp-server-operator-console.md)
(MCP scope extension).

## Why it's built this way

Safety controls here are **architecture, not prompts**:

- All LLM output enters through one Pydantic boundary; nonconforming
  output dies there
- Least-privilege agents: tool grants declared per agent, enforced by
  the runtime
- The regulatory rulebook is a deterministic, diffable script the
  agent may not override
- Deterministic hooks record every agent tool call in an append-only
  audit trail — path only, never patient data
- Humans own consequential actions: approval is a human-only command,
  absent by design from the MCP surface
- The probabilistic layer is measured, not assumed: field-level
  accuracy and N-trial consistency against human-verified golden labels

## Quickstart

```bash
# Requires Python 3.12+ and uv (https://docs.astral.sh/uv/)
git clone <repo-url> && cd clinical-sentinel
cp .env.example .env       # add your ANTHROPIC_API_KEY
uv sync                    # reproduce the exact locked environment
uv run pytest -q           # deterministic-layer tests

# The pipeline
uv run clinical-sentinel report_001.txt          # intake → case
uv run clinical-sentinel assess CS-2026-000001   # facts → rulebook
uv run clinical-sentinel draft CS-2026-000001    # narrative → pending_review/
uv run clinical-sentinel approve CS-2026-000001  # THE HUMAN GATE
uv run clinical-sentinel eval report_002.txt     # N=5 consistency eval

# As an MCP operator console (Claude Code)
claude mcp add clinical-sentinel -- uv run python src/clinical_sentinel/mcp_server.py
```

## Architecture

Color-coded process flow, per-command sequence diagrams, and a
component-by-component reference:
[docs/architecture/overview.md](docs/architecture/overview.md)

## Documentation

- [Design principles](docs/architecture/design-principles.md) — the
  rules every component follows, each with its enforcement location
- [Architecture overview](docs/architecture/overview.md)
- [Architecture Decision Records](docs/adr/) — why the system is
  shaped the way it is, including what was deliberately cut

## License

TBD