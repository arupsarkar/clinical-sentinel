# Demo Script — Clinical Sentinel

A 12–15 minute technical demo (10–12 without the optional Act 7): what
to RUN, what to SHOW, what to SAY. Each act ends with a **value line** —
the sentence that converts the technical beat into a business point.
Rehearse until the value lines are yours, not the script's.

## Commands at a glance (presenter reference)

| Command | Actor of consequence | Effect |
|---|---|---|
| `clinical-sentinel <report>` | system | Extract → validate → persist a case |
| `clinical-sentinel assess <case_id>` | system | Establish facts → run rulebook → persist assessment |
| `clinical-sentinel draft <case_id>` | system | Draft narrative → park in `pending_review/` |
| `clinical-sentinel approve <case_id>` | **human:cli** | Promote to `approved_reports/` (the only path in) |
| `clinical-sentinel eval <report>` | eval layer | N=5 consistency measurement against a golden fixture |

## Pre-demo checklist (5 min before)

````bash
cd ~/Projects/AI/clinical-sentinel
git status                        # clean tree — professionalism is visible
uv run pytest -q                  # tests green — open with working software

# Fresh state — every act starts from a known baseline
rm -f workspace/case_files/*.json workspace/audit/audit_log.jsonl
rm -f workspace/pending_review/*.json workspace/approved_reports/*.json

ls eval/golden/                   # confirm golden fixtures present (for Act 7)
````

Terminal font large, one window, `.env` NEVER opened on screen.
Have `workspace/intake_queue/report_001.txt` open in an editor tab.

---

## Act 1 — The problem (60 sec, no typing)

**SHOW:** report_001.txt — the raw call transcript.

**SAY:** "This is pharmacovigilance intake: a doctor calls about a
patient reaction. Pharma companies process millions of these a year,
from calls, emails, faxes. Every one must be triaged against
regulatory criteria on deadlines as short as 15 days. It's language
work, it's regulated, and it's drowning in volume."

**VALUE LINE:** *"This is the class of problem enterprises actually
have: high-volume unstructured language plus regulatory consequence."*

## Act 2 — The agent team is readable (90 sec)

**RUN:** nothing yet.
**SHOW:** `workspace/.claude/agents/` — open both agent files.
Point at the frontmatter `tools:` lines.

**SAY:** "The agents are markdown, not code. The intake specialist can
Read and Glob — it physically cannot write files or reach the network.
The severity assessor gets Bash because its job requires running a
script. Least privilege, declared per agent, reviewable by a
compliance officer who's never seen Python."

**VALUE LINE:** *"Your security team can audit my agent team in a
text editor."*

## Act 3 — Intake: extraction with honesty (3 min)

**RUN:**
````bash
uv run clinical-sentinel report_001.txt
````

**SHOW while it runs (~30 sec):** the transcript again — "watch it
find the four regulatory minimum elements scattered in conversation."
When output lands: point at the supporting quotes.

**SAY:** "Structured extraction, validated through a Pydantic schema —
the agent's contract and my validator are the same object; bad output
dies at the boundary. And every extracted fact carries a verbatim
quote: traceability to source."

**RUN the stress test:**
````bash
uv run clinical-sentinel report_002.txt
````

**SHOW:** `age=None` — and the missing_elements honesty.

**SAY:** "This report is from a worried daughter — no age, no name.
The agent inferred sex from 'my mother' — defensible — and refused to
invent the rest. In PV, an invented data point is the cardinal sin.
My workspace constitution says: absent data stays absent."

**VALUE LINE:** *"The system is engineered to say 'I don't know' —
that's a feature you design for, not hope for."*

## Act 4 — Severity: facts vs. rulebook (3 min)

**SHOW first:** `workspace/scripts/seriousness_scorer.py` — scroll it.

**SAY:** "Here's the architectural decision I'd defend in any design
review: the regulatory rulebook is a deterministic script, not a
prompt. The LLM answers language questions — 'was the patient
hospitalized?' The script answers rule questions — 'does
hospitalization make this serious?' Same facts in, same answer out,
forever. Diffable in git. The agent is instructed it may never
override the script."

**RUN both classifications:**
````bash
uv run clinical-sentinel assess CS-2026-000001   # serious: hospitalization
uv run clinical-sentinel assess CS-2026-000002   # scary language, NOT serious
````

**SHOW:** the contrast. Case 2's email said "serious consequences" —
the reporter's word. The system applied ICH E2A, not vocabulary.

**VALUE LINE:** *"Compliance logic lives where auditors can read it —
in code — and the AI is confined to what AI is good at."*

## Act 5 — Draft + Approve: the human gate (2 min)

**RUN:**
````bash
uv run clinical-sentinel draft CS-2026-000001
ls workspace/pending_review/                     # airlock: the draft is here
ls workspace/approved_reports/                   # outbox: empty until a human acts
uv run clinical-sentinel approve CS-2026-000001
ls workspace/pending_review/                     # empty — a draft cannot be both
ls workspace/approved_reports/                   # promoted, status: approved
````

**SHOW:** the airlock file appearing after `draft`, then vanishing
after `approve` while the outbox file appears. Open the reporter
agent's frontmatter (`workspace/.claude/agents/regulatory-reporter.md`)
and point at `tools: Read` — no Write, no Bash.

**SAY:** "The regulatory reporter is a read-only agent — its allowed
tools are Read and Agent, nothing else. It drafts a narrative, and my
system code parks the draft in `pending_review/`. Nothing about the
LLM's output can promote itself further. The one and only command
that moves a file to `approved_reports/` is this human `approve` step,
and the audit log records it with actor `human:cli` — the third actor
type in the trail. System code also computes the expedited flag and
the 15-day deadline from the deterministic severity verdict — the
LLM's contribution is exactly one field: narrative text."

**VALUE LINE:** *"The human isn't a review step bolted onto AI output —
the human is the only actor in the system with write permission on
the outbox."*

## Act 6 — The audit trail (2 min)

**RUN:**
````bash
cat workspace/audit/audit_log.jsonl
````

**SHOW:** the actor field — three kinds interleaved in one UTC
timeline: `agent:*` lines, `system` lines, and one `human:cli` line
(from Act 5's approval).

**SAY:** "Three kinds of actors, one append-only trail. The agent
lines come from SDK hooks — the runtime records every tool call
deterministically; the agent cannot skip or forget it. The system
lines come from my persistence and orchestration layers. The
`human:cli` line at the bottom is the approval — the consequential
step. Note what's absent from every line: file contents. We log which
file was touched, never patient data — the audit log must not become
a second copy of the record."

**VALUE LINE:** *"Safety controls here are architecture, not prompts —
schema validation, tool permissions, deterministic hooks, and a
human-only promotion path. Nothing that can be talked out of its
behavior."*

## Act 7 — Evals: measure the probabilistic layer (2 min — optional / extended cut)

**SAY first (setup, before the run):** "Deterministic code you
unit-test. Probabilistic code you eval — because the same input can
produce different outputs. This next command runs the intake agent
five times against the same report and scores each run against a
human-verified golden label."

**RUN:**
````bash
uv run clinical-sentinel eval report_002.txt
````

**SHOW:** the output table — the `pass` and `agree` columns
specifically. Point at any field where they diverge.

**SAY:** "Two rates matter and they measure different things.
`pass_rate` is correctness — how often the answer matches the golden.
`agreement_rate` is stability — how often the answer matches ITSELF
across runs. When pass is low but agreement is high, the system is
stably wrong — a golden or normalization fix. When both are low, the
system is unstable — a prompt or schema fix. Different diagnoses,
different remediations. The eval doesn't pass or fail; it produces a
scorecard, and a deployment threshold is a policy applied on top."

**VALUE LINE:** *"You cannot ship an LLM system you cannot measure.
The eval isn't a nice-to-have — it's the deterministic reasoning
about a probabilistic component, and it belongs in code review just
like everything else."*

## Act 8 — Close (60 sec)

**SHOW:** README progress table + `docs/adr/` + `docs/architecture/
architecture-process-flow.md` (the color-coded pipeline diagram).

**SAY:** "Built in small reviewed increments — the ADR log is every
decision with its rationale, including what I deliberately cut. The
process-flow diagram color-codes every step by actor: blue for
deterministic code, amber for LLM work, red for validators, green
for the human gate, purple for the eval layer. What you saw today
maps 1-to-1 to that diagram — the terminal output can even be traced
live with `CS_TRACE=1` for developer reviews."

**VALUE LINE:** *"This is the pattern I'd bring to your customers:
the LLM does language, code does rules, hooks do compliance, evals
do measurement, and humans keep the pen on anything that matters."*

---

## Recovery moves (when, not if)

- **Agent output fails validation:** don't apologize — narrate:
  "and THIS is why the boundary exists; watch it reject
  nonconforming output rather than pass it downstream." Re-run once.
- **Slow run:** fill with Act 2 material — you have 30 seconds of
  agent-definition talking points banked for exactly this. If the
  audience is technical, add: `CS_TRACE=1 uv run …` will stream the
  actor-by-actor pipeline to stderr — pull that up as the developer
  view of the same run.
- **Non-deterministic wobble** (e.g., missing_elements phrasing
  varies): name it — "same input, different advisory phrasing;
  load-bearing fields stay stable because the schema constrains them,
  and Act 7 shows you exactly how I measure that stability."
- **Eval trial fails mid-run (Act 7):** the tool prints partial
  results — narrate: "this is what a real eval failure looks like;
  pass_rate drops before agreement_rate does when the agent goes
  unstable." If the whole eval fails, fall back to a cached run in
  `workspace/evals/` if present.
- **Draft agent tries to Write (Act 5):** it can't — allowed_tools
  forbids it — but if it errors visibly, that's the point: narrate
  "the safety is architectural, so the failure mode is a permission
  error, not a rogue submission."
- **Total API failure:** the audit log, case files, `pending_review/`,
  and `approved_reports/` from rehearsal are your fallback — walk the
  artifacts instead of the live run. Every act has an artifact.
````
````

Three demo-craft notes baked into its design, worth internalizing: **the stumble is scripted** — Act 3's incomplete case and the recovery moves turn failure modes into planned beats, which is the single biggest difference between demos that survive contact with reality and demos that die; **show the boring files** — Acts 2 and 4 spend time on markdown and a plain Python script, because *legibility to non-engineers* is the enterprise story, not the flashy part; and **every act lands on one sentence** — technical audiences remember demos, executives remember value lines, and this role requires serving both in the same meeting.

Add it, commit (`docs: add technical demo script with value framing`), and do one full dry run against the script — out loud, timed — before you ever perform it. That dry run will also tell us if any beat needs a code tweak (e.g., you may want `report_002`'s case ID stable, which the fresh-state reset in the checklist guarantees).

That's genuinely everything tomorrow could need and more. Rehearse the four spoken pieces, sleep, take the call. Debrief me after.