# Clinical Sentinel — The Feynman Study Guide

*Rule of this document: if you can't say it simply, you don't own it yet.
Every section has two layers — the simple explanation (say it to a smart
friend who knows nothing about AI or pharma) and the mechanism (say it to
Jonathan). Practice both, out loud. The simple version is not the dumbed-down
version; it is the proof you understand.*

---

## Part 1 — The Project, Explained Simply

### The one-breath version

> Drug companies are legally required to track side effects. The reports come
> in as messy human language — phone calls, emails, faxes. I built a team of
> AI agents that reads those reports, pulls out the facts, decides how serious
> the case is, and drafts the regulatory paperwork — but the system is built
> so the AI physically cannot do the dangerous things: it can't invent patient
> data that survives to a case file, it can't classify seriousness by opinion,
> and it can't submit anything to a regulator. Code and humans own those.

### The problem (Feynman version)

Imagine a hospital's lost-and-found, except what gets turned in are *stories*:
"my mother got dizzy after her heart pills." The law says every story must be
checked for four things — who's the patient, who's telling us, which drug,
what happened — and if the story is serious (someone hospitalized, someone's
life threatened), the clock starts: report to the FDA within 15 days.

Millions of stories a year. Humans read every one. It's language work,
drowning in volume, with legal deadlines. That's pharmacovigilance (PV).

**Why AI fits:** the bottleneck is *reading and structuring language* — the
exact thing LLMs are best at.
**Why AI is scary here:** an invented data point isn't a typo, it's a
corrupted safety record. So the system's job is to use the LLM for language
and *refuse to trust it* for anything else.

### The pipeline in five verbs

```
intake  →  persist  →  assess  →  draft  →  approve
(agent)    (system)    (agent+    (agent)   (HUMAN)
                        script)
```

1. **Intake** — an agent reads one raw report and extracts structured facts.
2. **Persist** — *system code* (not the agent) mints a case ID, stamps the
   date, writes the case file.
3. **Assess** — an agent answers six factual yes/no questions ("was the
   patient hospitalized?"); a *plain Python script* applies the regulatory
   rulebook to those answers. The agent may never override the script.
4. **Draft** — a read-only agent writes the report narrative; the system
   computes the deadline (received date + 15 days if serious). Draft lands in
   `pending_review/`.
5. **Approve** — a human runs the approve command. That human action is
   itself logged in the audit trail. Nothing reaches "approved" any other way.

### The cast of three actors (memorize this — it's the demo's spine)

The audit log has three kinds of actors, and the whole philosophy is in who
does what:

| Actor | What they own | Example log line |
|---|---|---|
| `agent:*` | Language understanding only | "Read intake_queue/report_002.txt" |
| `system:*` | Facts, rules, identifiers, math | "case_created CS-2026-000005" |
| `human:*` | Consequential decisions | "report_approved CS-2026-000001" |

**Feynman line:** *"Agents read, the system decides, humans sign."*

---

## Part 2 — The Eight Principles, Each With Its Mechanism

*Never recite this list. Each row exists so that when ONE principle comes up,
you give its mechanism in the same breath. Principle without mechanism = 
marketing. The mock proved this.*

| Principle (never say alone) | Mechanism (always say with it) |
|---|---|
| Validate at the boundary, fail fast | All LLM output enters through one door: `IntakeExtraction.model_validate_json()`. Nonconforming output raises `ValidationError` and dies there. Missing API key fails at startup with a fix-it message, not mid-run. |
| Domain model precedes agents | `AdverseEventCase` encodes the regulatory rules as Pydantic types: age constrained 0–130, case ID regex-enforced, a `@model_validator` that refuses to construct a case with an unidentifiable patient. Invalid cases aren't caught — they're *unconstructible*. |
| LLMs never mint identifiers or system facts | `IntakeExtraction` (the agent's output type) deliberately has no `case_id` or `received_date` fields. `CaseStore._next_case_id()` mints IDs; the system clock stamps dates; `received + timedelta(days=15)` computes deadlines. Arithmetic, not opinion. |
| Absent data stays absent | The agent's constitution (workspace CLAUDE.md rule 1) + `missing_elements` as a first-class field + the eval harness's `must_not_invent` hallucination check that fails ANY invented value where golden truth says null. |
| Every extraction is traceable | `supporting_quotes`: each extracted fact carries the verbatim source language that supports it. A human can spot-check any field against the original document. |
| Least-privilege agents | Declared in each agent's frontmatter: intake gets `Read, Glob` (cannot write, cannot execute, cannot reach network); assessor gets `Read, Bash` (needs to run the scoring script); reporter gets `Read` only. Reviewable by a compliance officer in a text editor. |
| Humans own consequential actions | The reporter agent is read-only; drafts land in `pending_review/` via system code; the ONLY path to "approved" is the human-invoked CLI command, which logs `actor: human:cli`. |
| Safety controls are architecture, not prompts | The summary of all of the above: schema validation, tool permissions, deterministic scripts, hooks, human gates — mechanisms that cannot be talked out of their behavior. Prompts express intent; architecture enforces it. |

---

## Part 3 — The Hard Q&A Bank

# Clinical Sentinel — Grounded Q&A Bank

*Rule of this document: no claim without a code address. Every answer has
three layers — the SPOKEN answer (what you say), the EVIDENCE (file, code,
and what it does in plain English), and where honest, the GAP (what the code
does NOT do — conceded precisely, with where that control actually lives).*

*Verify each snippet against your actual tree once before Thursday — code
cited here is the project as we built it; if you've edited solo, know where
the line moved.*

---

## Q1. "Safety controls as architecture, not prompts — convince me."

**SPOKEN:** "Let me give you one guarantee and its mechanism. The guarantee:
a case file with an unidentifiable patient cannot exist. Not unlikely —
unconstructible. It's a Pydantic model-level validator: after all fields
parse, if none of age, sex, or initials is present, construction raises.
The persistence layer can only write objects that constructed. Pick any
other control and I'll walk you to its code the same way."

**EVIDENCE:**

`src/clinical_sentinel/models/case.py`:

```python
@model_validator(mode="after")
def patient_must_be_identifiable(self) -> "AdverseEventCase":
    if not self.patient.is_identifiable():
        raise ValueError(
            "Case rejected: patient is not identifiable. "
            "At least one of age, sex, or initials is required "
            "(PV minimum criteria)."
        )
    return self
```

Plain English: this method runs automatically every time anyone, anywhere,
tries to create an `AdverseEventCase`. There is no way to construct the
object without passing through it. If the patient has no qualifier, the
object never exists — so it can never be written to disk, because
`CaseStore.create_case` writes `case.model_dump(...)`, and there is no
`case` to dump.

And `is_identifiable()` on `Patient` (same file):

```python
def is_identifiable(self) -> bool:
    return any([self.age_years is not None, self.sex, self.initials])
```

Plain English: the regulatory rule — any ONE qualifier suffices — encoded
as one line of checkable logic, not as a paragraph in a prompt.

---

## Q2. "Your agent invents `age: 70` on a report with no age. Does it reach the case file?"

**SPOKEN:** "Honestly: today, yes — and I can show you exactly why, and
exactly where the controls sit instead."

**EVIDENCE — why it passes (concede with precision):**

`src/clinical_sentinel/models/case.py`:

```python
age_years: int | None = Field(default=None, ge=0, le=130)
```

Plain English: the boundary checks that age is an integer between 0 and 130.
An invented 70 satisfies that perfectly. **Structural validation checks
form, not truth** — the constraint cannot know the source document never
mentioned an age.

**EVIDENCE — control 1, detectability (exists today):**

`src/clinical_sentinel/models/intake.py`:

```python
# Verbatim quotes supporting each extracted field — the agent must
# show its work, enabling human spot-checks against the source.
supporting_quotes: list[str] = Field(default_factory=list)
```

Printed by `_intake_command` in `src/clinical_sentinel/__init__.py`:

```python
for q in extraction.supporting_quotes:
    print(f'  quote: {q}')
```

Plain English: every extraction carries verbatim source passages. A reviewer
can Ctrl-F each quote in the source file and check the extracted value
appears in the cited language. An invented 70 would have no quote containing
"70" — the evidence gap is visible. **This is detection by a human, not
enforcement by the machine** — note `default_factory=list`: nothing forces
one quote per fact; the agent chooses what to cite each run.

**EVIDENCE — control 2, measurement (exists today):**

`src/clinical_sentinel/evals/scorer.py`:

```python
invented = must_not_invent and expected is None and actual is not None
```

and the golden label `eval/golden/report_002.json`:

```json
"must_not_invent": ["patient.age_years", "patient.initials"]
```

Plain English: for fields where the human-verified answer key says "the
truth is: absent," ANY value the system supplies is flagged
`is_hallucination` — a distinct failure class, separated from ordinary
wrongness. The eval harness measures the invention RATE across N trials.
Runtime catches malformed outputs; evals catch untrue ones.

**THE GAP (name it before he does):** "The runtime path does not verify
groundedness. The designed fix is deterministic: for each supporting quote,
assert `quote in source_text` — a fabricated quote fails instantly because
the source file is ground truth the model can't alter — then assert the
extracted value appears within its quote. Two string checks, no AI, at the
boundary. It's about 25 lines and it's next on my list."

---

## Q3. "Why a deterministic script for seriousness? The model would be right most of the time."

**SPOKEN:** "Because 'right most of the time' fails exactly where this
domain punishes failure — the tail case in front of a regulator. So the
split: the LLM answers the language question, a script answers the rule
question. And I can show you that the split is structural, not aspirational."

**EVIDENCE — the split is in the schema:**

`src/clinical_sentinel/models/severity.py`:

```python
class SeriousnessFacts(BaseModel):
    """The agent's six factual determinations — the language-understanding half."""
    death: bool
    life_threatening: bool
    hospitalization: bool
    ...

class Classification(BaseModel):
    """The script's verdict — the rulebook half. Mirrors scorer output."""
    is_serious: bool
    criteria_met: list[Seriousness] = Field(default_factory=list)
```

Plain English: facts and verdict are *different types*. The output data
itself preserves who decided what — an auditor sees the agent's claimed
facts sitting beside the script's verdict and can re-run the script on
those facts to check they match.

**EVIDENCE — the rulebook is auditable code:**

`workspace/scripts/seriousness_scorer.py` — the entire import section:

```python
import argparse
import json
```

Plain English: stdlib only, by design (it runs in the agent's bare Bash
environment). No dependencies, no AI, ~50 lines. `git log` on this file is
the complete history of every rule change, with author and date — that's
what "reviewable by a compliance officer" means concretely.

**EVIDENCE — no defaults decide:**

```python
for c in CRITERIA:
    parser.add_argument(f"--{c.replace('_', '-')}", type=str2bool, required=True)
```

Plain English: all six criterion flags are `required=True`. Omit one and
argparse exits with an error before any classification happens — the agent
must take an explicit true/false position on every criterion. And
`str2bool` accepts only literal "true"/"false"; anything else raises.

**EVIDENCE — vocabulary drift dies at the boundary:**

`criteria_met: list[Seriousness]` — typed against the enum in
`models/case.py`. Plain English: if anything upstream produces a criterion
name the rulebook vocabulary doesn't contain, Pydantic validation raises at
`SeverityAssessment.model_validate_json` in `orchestration/severity.py`.

**THE GAP (honest labeling):** "The 'never override the script' rule is in
the agent's instructions — that's intent, not enforcement:

```markdown
Report the script's output as the classification — never override it,
never classify by your own judgment. If the script errors, report the
error; do not classify without it.
```

The enforcement upgrade is ~10 lines in the orchestrator: system code
re-runs the scorer on the agent's reported facts and asserts the verdict
matches. Defiance is already *visible* — facts sit beside verdict in the
output — the re-check makes it *impossible*. It's on the same list as the
quote-grounding check."

---

## Q4. "Tell me about your eval harness. What did it find?"

**SPOKEN:** "Two artifacts, and a finding that surprised me. Deterministic
scorer: golden label versus one extraction, field by field. Consistency
runner: same report, N times, per-field agreement — because a test asserts
once; an eval samples a distribution. First real run caught drug
identification at 80%: one run in five returned the verbatim misspelling
instead of the catalog name. Most load-bearing field in the system,
invisible to every manual check I'd done."

**EVIDENCE — the two metrics and why both exist:**

`src/clinical_sentinel/evals/consistency.py`:

```python
pass_rate: float            # fraction of trials matching golden
agreement_rate: float       # fraction agreeing with the modal answer
modal_value: str            # most common answer across trials
distinct_values: int        # how many different answers appeared
```

Plain English: pass measures *correctness* (against the human answer key);
agreement measures *stability* (against itself). The 2×2 diagnoses the fix:
low pass + high agreement = stably wrong → content fix (prompt says the
wrong thing). Low agreement = unstable → constraint fix (prompt
under-specifies). My finding was pass 80 / agree 80 / 2 distinct values —
instability: four runs normalized "Cardioflex" to Cardiofex, one didn't.

**EVIDENCE — the actual finding (your own terminal, real numbers):**

```
field                   pass  agree  #vals  modal
suspect_drug             80%    80%      2  Cardiofex
patient.age_years       100%   100%      1  None
patient.sex             100%   100%      1  female
...
all trials passed: False
```

Plain English: the single-run scorecard on the same report said "all
passed: True." The N=5 table said otherwise. That contradiction between the
two artifacts is the entire argument for consistency testing.

**EVIDENCE — the two-layer fix:**

Fix 1, prompt (intent): add to `intake-specialist.md` — "map suspect drug
names to the product catalog in CLAUDE.md; record verbatim spellings only
in supporting quotes." Fix 2, code (guarantee): a drug-name normalization
map, same pattern as the reporter map already in `evals/scorer.py`:

```python
_REPORTER_CATEGORY_MAP: list[tuple[str, str]] = [
    ("physician", "physician"), ("oncologist", "physician"), ...
    ("consumer", "consumer"), ("family", "consumer"), ("daughter", "consumer"),
]
```

Plain English: normalization rulings live in diffable code, not in the
prompt — which is why `reporter_category` scored 100% consistent even
though the agent's raw free-text phrasing varies run to run. The map
absorbed the wobble. Same medicine for drug names.

---

## Q5. "80% from five trials — what's wrong with that number, and what's your deployment gate?"

**SPOKEN (own these words — three spoken reps):** "80% from N=5 isn't a
measurement, it's an anecdote with a decimal point — four-of-five carries a
confidence interval from roughly the thirties to the high nineties. Same
disease as a one-month Sharpe ratio. My own paper refuses to trust a Sharpe
without deflating it for sample size; my harness deserves the same
discipline, and at N=5 it doesn't have it. Five was the right N to find the
first bug, the wrong N to certify a deployment. The scaling rule: N grows
with the claim — observing failures at a 1% rate needs hundreds of trials;
~300 clean supports 'ninety-nine-plus with reasonable confidence.' The
gate, as I'd write it in an SOW: load-bearing fields ≥99% over N≥300 on a
held-out golden set the customer's own team labels, zero tolerance for
hallucination-class failures, advisory fields ≥90%, re-certification on
every prompt or model change, and the eval report is a deliverable."

**EVIDENCE — the harness already parameterizes N:**

`src/clinical_sentinel/evals/consistency.py`:

```python
async def run_consistency(golden: GoldenCase, report_filename: str, n: int = 5) -> ConsistencyReport:
```

Plain English: N=5 is a default argument, not a design limit — the
certification run is the same function at n=300. What changes is budget,
which is why the docstring carries a cost note and why eval tiering exists:
deterministic checks (free) at high N, judge checks (paid) at lower N.

**EVIDENCE — hallucination as a separate failure class (the
zero-tolerance line is implementable because the scorer distinguishes it):**

`evals/models.py`:

```python
passed: bool
is_hallucination: bool = False   # failed specifically by inventing data
```

Plain English: the gate "zero hallucination-class failures" isn't rhetoric —
it's a filter on an existing field: `[f for f in result.fields if
f.is_hallucination]` is already a property (`CaseEvalResult.hallucinations`).

---

## Q6. "Where does your ground truth come from?"

**SPOKEN:** "Hand-verified against source, by me — because the alternative
is circular. My system's case files look exactly like golden labels;
promote one and the eval becomes 'does the system produce what the system
produced' — 100% forever, including on every bug. The chain must run
source document → human judgment → golden label, never through the system.
I do use system output as a labeling draft — standard bootstrapping — but
every field gets verified against source text before it's golden."

**EVIDENCE — the golden schema is richer than any system output:**

`eval/golden/report_002.json`:

```json
"must_not_invent": ["patient.age_years", "patient.initials"],
"notes": "RULINGS: (1) sex=female accepted as correct — 'my mother' states
sex by direct implication; this single qualifier makes the patient
identifiable, hence is_complete=true. (2) suspect_drug normalized to
catalog name 'Cardiofex' despite source spellings 'Cardioflex'/'cardiofex'..."
```

Plain English: two things no system output can contain. `must_not_invent`
is a statement about what a correct system *refrains* from doing. And
`notes` records the human labeling RULINGS — the answer to "what counts as
correct?" (is inferred sex acceptable? is normalization expected?). Those
rulings are the scorer's spec; the scorer's normalization maps implement
them. Deciding what counts as correct is the hard part of eval design —
the notes field is where that work is visible.

**EVIDENCE — golden files are validated too:**

`evals/models.py` — `GoldenCase(BaseModel)` with typed sub-models.
Plain English: a malformed answer key dies at load time, same boundary
discipline as everywhere else. Even the eval layer doesn't trust its inputs.

---

## Q7. "Why the Agent SDK and not raw API, or LangChain?"

**SPOKEN:** "With the raw API, the agent loop, tool execution, and context
management are my code to maintain. The SDK ships the harness that runs
Claude Code in production, as a library — my repo contains zero agent-loop
code; it contains a pharmacovigilance system. The deeper reason is where
governance primitives live: my audit trail and tool permissions are runtime
features, not prompt requests. On LangChain: abstraction across models is
genuinely useful for portability, and I'd never tell a customer to burn an
estate — but abstractions catch up to new capabilities on a lag; the SDK is
the product's own runtime. My honest framing: keep the framework where it
serves; use the native stack for governance-critical workloads."

**EVIDENCE — governance as runtime configuration, not prompt text:**

`src/clinical_sentinel/orchestration/intake.py`:

```python
options = ClaudeAgentOptions(
    model=settings.model,
    cwd=settings.agent_workspace,
    setting_sources=["project"],
    allowed_tools=["Read", "Glob", "Agent"],
    hooks={
        "PostToolUse": [
            HookMatcher(matcher="Read|Glob", hooks=[_make_tool_audit_hook(audit)])
        ]
    },
)
```

Plain English, line by line: `allowed_tools` — the intake agent cannot
write, execute, or reach the network, enforced by the runtime, not
requested by the prompt. `hooks` — the runtime calls my logging function on
every matching tool use; the agent cannot skip it, forget it, or be talked
out of it. `setting_sources=["project"]` — agent definitions load from the
workspace, so the whole team is reviewable markdown. Per-agent variation:
severity gets `["Read", "Bash", "Agent"]` (needs the script), reporter gets
`["Read", "Agent"]` (read-only by design) — least privilege, per role, in
`orchestration/severity.py` and `orchestration/reporting.py`.

**EVIDENCE — the hook logs paths, never patient data:**

```python
detail={
    "tool": input_data.get("tool_name", "unknown"),
    # Log WHICH file was touched — but never file CONTENTS:
    # audit logs must not become a second copy of patient data.
    "file_path": input_data.get("tool_input", {}).get("file_path"),
},
```

Plain English: a compliance decision expressed in what the code *doesn't*
collect. The audit trail must not become a second, unguarded copy of the
sensitive record.

---

## Q8. "What breaks first at a thousand reports a day?"

**SPOKEN:** "Several things, all named as deliberate scope decisions in the
repo, not surprises."

**EVIDENCE — each break, with its code address:**

1. **Duplicate detection.** My own audit log shows it:

```jsonl
{"event_type": "case_created", "detail": {"case_id": "CS-2026-000001", "source_file": "report_001.txt"}}
{"event_type": "case_created", "detail": {"case_id": "CS-2026-000004", "source_file": "report_001.txt"}}
```

Plain English: same source, processed twice, two case IDs — dedup is a real
PV discipline, explicitly deferred in the scope-freeze ADR, and my own
compliance trail exhibits the gap honestly.

2. **The ID sequence.** `persistence/case_store.py`:

```python
existing = len(list(self._case_dir.glob("CS-*.json")))
return f"CS-{year}-{existing + 1:06d}"
```

Plain English: counts files on disk — honest for a single process, a race
condition under concurrency. The docstring says so itself ("a real
deployment would use a database sequence"). The fix is a database sequence;
the point is the limitation is documented at the line that has it.

3. **Sequential agent runs** → batch processing for the non-urgent tier.
4. **Audit attribution** — the hook hardcodes one agent name; per-subagent
   attribution via the SDK's parent_tool_use_id is the named fix.
5. **The eval program** scales from 3 golden cases to a labeled corpus with
   a CI certification gate — `run_consistency(n=...)` is already the
   function; the corpus and the gate are the work.

---

## Q9. "How do you manage cost at scale?"

**SPOKEN:** "Cost is an architecture discipline, and the seams are built in."

**EVIDENCE:**

1. **Model tiering** — `config.py`:

```python
model: str = "claude-sonnet-4-6"
```

Plain English: the model is one config property, injected into every
orchestrator via `settings.model` — per-agent model assignment (Haiku-class
for extraction at scale, frontier for judgment) is a one-line change per
agent, not a refactor.

2. **Rules in code are tokens never billed** — `seriousness_scorer.py`
runs for free, forever. Every rule moved from prompt to code exits the
per-request bill permanently.

3. **Prompt caching** — the stable context every call resends
(`workspace/CLAUDE.md`, agent definitions, the injected JSON schema from
`IntakeExtraction.model_json_schema()`) is exactly the cacheable tier.

4. **Batch the non-urgent; observe the spend** — overnight backlogs don't
need interactive latency; SDK telemetry makes per-workload cost observable.

---

## Q10. "What would you build next?"

**SPOKEN, with the code each item lands in:** "Three things. One: the
quote-grounding check — `quote in source_text` and value-in-quote,
deterministic, at the boundary in `run_intake`, closing the groundedness
gap. Two: the scorer re-verification in `run_assessment` — system code
re-runs the rulebook on the agent's reported facts and asserts the verdict
matches; converts 'never override' from instruction to enforcement. Three:
wrap the pipeline as an MCP server so Claude Code becomes the operator
console — the commands you saw (`intake`, `assess`, `draft`, `approve`,
`eval`) become tools an operator invokes conversationally, with the same
audit trail accruing underneath. That's the panel demo."

---

## The Meta-Answer (if asked "how do you know your own system this well?")

"Because I built it in small reviewed increments and refused black boxes —
every principle in my docs carries an 'enforced in' pointer to a file, every
decision is an ADR, and when my interviewer prep found claims I couldn't
pin to a line of code, I rewrote the claims. The discipline you're seeing
in the answers is the same discipline in the repo."

---

## Part 4 — Feynman Self-Tests

*Close the document. Say each of these in ONE sentence, out loud. If any
takes two, re-study that section.*

1. What is pharmacovigilance? *(...the legal duty to track drug side
   effects: collect reports, judge seriousness, tell regulators on
   deadline.)*
2. Why do LLMs fit PV intake? *(...the bottleneck is reading messy language
   at volume — the one thing LLMs are best at.)*
3. Why not trust the LLM with everything? *(...an invented data point is a
   corrupted safety record, so the LLM gets language and nothing else.)*
4. What's the four-minimum-elements rule? *(...a valid case needs an
   identifiable patient, identifiable reporter, a suspect drug, and an
   event.)*
5. What does "validate at the boundary" mean mechanically? *(...all LLM
   output enters through one Pydantic parse that raises on anything
   nonconforming.)*
6. Runtime validation vs. evals in one line? *(...runtime catches malformed
   outputs; evals catch untrue ones.)*
7. Test vs. eval in one line? *(...a test asserts once on deterministic
   code; an eval samples a distribution from a probabilistic system.)*
8. pass_rate vs. agreement_rate? *(...pass measures correctness against
   golden; agreement measures stability regardless of correctness — the 2×2
   tells you whether to fix content or constraint.)*
9. Why is N=5 not enough? *(...small samples can't carry big claims — 80%
   from five trials is an anecdote with a decimal point.)*
10. Why can't system outputs be golden labels? *(...the student can't write
    the answer key — circular evals certify bugs.)*
11. What do the three actors own? *(...agents read, the system decides,
    humans sign.)*
12. Why a script for seriousness? *(...rules should give the same answer
    every run, be diffable in git, and be readable by a compliance officer.)*
13. What can the intake agent NOT do? *(...write files, run code, or reach
    the network — Read and Glob only, declared in frontmatter.)*
14. Where does the 15-day deadline come from? *(...arithmetic in system
    code — received date plus fifteen — never from the model.)*
15. Your one-line differentiator? *(...the LLM does language, code does
    rules, hooks do compliance, and humans keep the pen on anything that
    matters.)*

---

## Part 5 — The Mock's Lessons, Standing Orders

1. **Mechanism first.** On any "how/enforce/concretely" question: one
   guarantee, one mechanism, 45 seconds, invite the next thread. Never open
   with a principle list.
2. **Vocabulary of probability.** Never "the model will not." Always "the
   model may; the system won't let it matter — and where it can, I measure
   the rate."
3. **Concede precisely, then relocate the control.** "The runtime path does
   not verify groundedness — that control lives in the eval layer" beat
   every polished claim in the mock.
4. **Jot multi-part questions.** Pen and paper beside the keyboard. It looks
   like customer-call discipline because it is.
5. **Own the statistics answers in your own words.** Three spoken reps of
   Q5 before Thursday. They were borrowed in the mock; they must be yours in
   the room.
6. **Manage the clock for your close.** Two pre-loaded questions, then:
   data + context career → this role adds the intelligence layer → "what do
   you need from me before the panel?"