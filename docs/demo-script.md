# Demo Script — Clinical Sentinel

A 10–12 minute technical demo: what to RUN, what to SHOW, what to SAY.
Each act ends with a **value line** — the sentence that converts the
technical beat into a business point. Rehearse until the value lines
are yours, not the script's.

## Pre-demo checklist (5 min before)

````bash
cd ~/Projects/AI/clinical-sentinel
git status                        # clean tree — professionalism is visible
uv run pytest -q                  # 6 green — open with working software
rm -f workspace/case_files/*.json workspace/audit/audit_log.jsonl   # fresh state
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

## Act 5 — The audit trail (2 min)

**RUN:**
````bash
cat workspace/audit/audit_log.jsonl
````

**SHOW:** the actor field — `agent:*` lines and `system` lines
interleaved in one UTC timeline.

**SAY:** "Two kinds of actors, one append-only trail. The agent lines
come from SDK hooks — the runtime records every tool call
deterministically; the agent cannot skip or forget it. The system
lines come from my persistence layer. Note what's absent: file
contents. We log which file was touched, never patient data —
the audit log must not become a second copy of the record."

**VALUE LINE:** *"Safety controls here are architecture, not prompts —
schema validation, tool permissions, deterministic hooks. Nothing
that can be talked out of its behavior."*

## Act 6 — Close (60 sec)

**SHOW:** README progress table + `docs/adr/`.

**SAY:** "Built in small reviewed increments — the ADR log is every
decision with its rationale, including what I deliberately cut. Next
on the frozen scope: the regulatory reporter runs in plan mode — it
drafts, a human approves, and the approval itself lands in the audit
log. Humans own consequential actions."

**VALUE LINE:** *"This is the pattern I'd bring to your customers:
the LLM does language, code does rules, hooks do compliance, and
humans keep the pen on anything that matters."*

---

## Recovery moves (when, not if)

- **Agent output fails validation:** don't apologize — narrate:
  "and THIS is why the boundary exists; watch it reject
  nonconforming output rather than pass it downstream." Re-run once.
- **Slow run:** fill with Act 2 material — you have 30 seconds of
  agent-definition talking points banked for exactly this.
- **Non-deterministic wobble** (e.g., missing_elements phrasing
  varies): name it — "same input, different advisory phrasing;
  load-bearing fields stay stable because the schema constrains them.
  This is why customers need eval frameworks, which is my next build."
- **Total API failure:** the audit log and case files from rehearsal
  are your fallback — walk the artifacts instead of the live run.
````
````

Three demo-craft notes baked into its design, worth internalizing: **the stumble is scripted** — Act 3's incomplete case and the recovery moves turn failure modes into planned beats, which is the single biggest difference between demos that survive contact with reality and demos that die; **show the boring files** — Acts 2 and 4 spend time on markdown and a plain Python script, because *legibility to non-engineers* is the enterprise story, not the flashy part; and **every act lands on one sentence** — technical audiences remember demos, executives remember value lines, and this role requires serving both in the same meeting.

Add it, commit (`docs: add technical demo script with value framing`), and do one full dry run against the script — out loud, timed — before you ever perform it. That dry run will also tell us if any beat needs a code tweak (e.g., you may want `report_002`'s case ID stable, which the fresh-state reset in the checklist guarantees).

That's genuinely everything tomorrow could need and more. Rehearse the four spoken pieces, sleep, take the call. Debrief me after.