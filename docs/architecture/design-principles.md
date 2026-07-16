# Design Principles

Standing rules that govern every component in Clinical Sentinel.
Each principle names the rule, the reason, and where it's enforced
in code — so a reader can verify we practice what we document.

## 1. Validate at the boundary, fail fast

Bad data and broken environments are rejected at the earliest possible
moment, with human-readable errors — never deep inside an agent loop.

- **Enforced in:** `config.py` (`get_settings()` rejects a missing API
  key at startup); `models/case.py` (Pydantic field constraints and
  `@model_validator` make invalid cases unconstructible).

## 2. The domain model precedes the agents

What an "adverse event case" *is* was defined as executable, tested
types before any agent existed. Agents produce and consume these types;
they do not define the domain.

- **Enforced in:** `models/case.py`, `tests/test_case_model.py`.

## 3. LLMs never mint identifiers or system facts

Case IDs, timestamps, sequence numbers — anything that is a fact about
the *system* rather than the *source text* — are assigned
deterministically by the orchestrator. The agent extracts only what
requires language understanding.

- **Enforced in:** `models/intake.py` (`IntakeExtraction` deliberately
  has no `case_id` or `received_date` fields).

## 4. Absent data stays absent

Agents must never pad, infer, or invent missing information. An
incomplete extraction is a valid, useful outcome — gaps are recorded
as first-class data, not silently filled.

- **Enforced in:** `IntakeExtraction.missing_elements`;
  workspace `CLAUDE.md` rule 1; intake-specialist prompt.

## 5. Every extraction is traceable to its source

Agents show their work: extracted facts carry verbatim supporting
quotes so a human can spot-check any field against the original
document.

- **Enforced in:** `IntakeExtraction.supporting_quotes`.

## 6. Least-privilege agents

Each agent is granted only the tools its job requires, declared in
its definition file. The intake agent can read; it cannot write,
execute, or reach the network.

- **Enforced in:** `workspace/.claude/agents/*.md` frontmatter
  (`tools:` line).

## 7. Humans own consequential actions

The system drafts, assesses, and flags; it does not submit anything
to a regulator. Regulatory actions are gated behind human review
(plan mode).

- **Enforced in:** workspace `CLAUDE.md` rule 4; (forthcoming)
  regulatory-reporter agent runs in plan mode.

## 8. Safety controls are architecture, not prompts

Where a guarantee matters, it is enforced by a mechanism that cannot
be talked out of its behavior: schema validation, tool permissions,
deterministic hooks, human gates. Prompts express intent; architecture
enforces it.

- **Enforced in:** all of the above — this principle is the summary
  of the system.