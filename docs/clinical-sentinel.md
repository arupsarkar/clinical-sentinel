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

*Format: the question as Jonathan (or a panel, or a customer) would ask it,
then the answer in YOUR voice, spoken-length (45–90 seconds). The mock
findings are baked in: mechanism-first, "the model may / the system won't
let it matter," concede gaps precisely.*

### Q1. "Safety controls as architecture, not prompts — convince me that means more than a strict system prompt."

**Answer (mechanism-first — this is the fixed opening from the mock):**

"Let me give you one concrete guarantee and its mechanism, and then you can
pull whatever thread you want.

The guarantee: a case file with an unidentifiable patient cannot exist in
this system. Not 'is unlikely' — cannot exist. The mechanism: the case is a
Pydantic model, and it has a model-level validator that runs after all fields
parse. If none of age, sex, or initials is present, construction raises. The
persistence layer can only write objects that constructed. So an
unidentifiable-patient case isn't caught by review — it's unconstructible by
type design.

That's the pattern everywhere: the model is instructed not to invent data —
that's the prompt, and I treat it as intent, not enforcement. The enforcement
is the schema boundary, the tool permissions in each agent's definition, a
deterministic scoring script the agent can't override, and a human approval
gate that's the only path to an approved report. Pick any one and I'll walk
you through the code."

### Q2. "Your agent invents `age: 70` on a report with no age. Walk me through what happens. Does it reach the case file?"

**Answer (the honest one — this is the exchange that won the mock):**

"Honestly: yes, it can reach the case file — and it's important I'm precise
about why. My boundary validates *form*, not *truth*. An invented 70 is a
valid integer in range; it makes the patient identifiable; every structural
gate passes. Structural validation cannot catch a well-formed lie.

The model may invent; my job is to make sure it doesn't matter, and where it
can matter, to measure it. Three controls: first, the agent's output carries
supporting quotes — verbatim source language per extracted fact — so any
value is human-verifiable against the document. Second, my eval harness has a
hallucination check: golden labels mark fields as must-not-invent, and any
non-null value there is a scored failure — so I measure the invention *rate*
on labeled data. Third — and this is a check I've designed but not yet built —
quote-grounding at runtime: verify the supporting quote exists verbatim in
the source and the extracted value appears in it. That's deterministic and
would close the gap per-request.

So: runtime catches malformed outputs; evals catch untrue ones. Different
layers, different questions, both load-bearing."

### Q3. "Why a deterministic script for seriousness? The model would be right most of the time."

**Answer:**

"'Right most of the time' is exactly the problem — in this domain the failure
that matters is the tail case in front of a regulator, not the average case.

So I split the job along the line of what each side is actually good at. The
LLM answers language questions: was the patient hospitalized? — that requires
reading 'we had to admit him overnight' and understanding it. The script
answers rule questions: does hospitalization make this serious? — that's ICH
E2A, and it should give the same answer every run, forever.

What the split buys, concretely: the rulebook is a stdlib-only Python script,
diffable in git, reviewable by a compliance officer who's never touched AI.
Every criterion flag is required — the agent must take an explicit position
on all six; it can't omit one and let a default decide. And the agent's
instructions say: report the script's output as the classification, never
override it — and if the script errors, report the error rather than classify
by judgment. The guardrail covers the failure path, not just the happy path.

Bonus: every rule moved from prompt to code is tokens that never get billed
again. Compliance and cost point the same direction."

### Q4. "Tell me about your eval harness. What did it find that surprised you?"

**Answer (the war story — tell it with the numbers):**

"Two artifacts: a deterministic scorer — golden label versus one extraction,
field by field — and a consistency runner: same report, N times, per-field
agreement. Because a test asserts once; an eval samples a distribution. My
agent is non-deterministic, so 'did it pass' is the wrong question — 'how
often, per field' is the right one.

First real run surprised me. I'd manually run my hardest test report five
times over days — the one with a misspelled drug name — and it looked solid.
The harness ran it five times in a row and caught drug identification at
80%: one run in five returned the verbatim misspelling instead of the
normalized catalog name. The most load-bearing field in the system, wobbling
one time in five, invisible to every manual check I'd done.

And the two metrics diagnose it: pass 80, agree 80, two distinct values —
that's *instability*, not stable wrongness. Four runs normalized, one didn't.
Which tells me the fix is constraint, not content: tighten the prompt to map
to the catalog, and add a deterministic normalization map in code so the
guarantee doesn't depend on the prompt behaving. Prompt for intent, code for
enforcement — same philosophy as the rest of the system."

### Q5. "80% from five trials. What's wrong with that number, and what's your deployment gate?"

**Answer (the statistics — own these words):**

"What's wrong is that 80% from N=5 isn't a measurement, it's an anecdote with
a decimal point. Four-of-five has a confidence interval running from roughly
the thirties to the high nineties — five trials can't distinguish an
80%-reliable field from a 60% or a 95% one. It's the same disease as a
one-month Sharpe ratio: an impressive number on a sample too small to carry
it. My own paper refuses to trust a Sharpe without deflating it for exactly
this; my harness deserves the same discipline, and at N=5 it doesn't have it
yet. Five was the right N to find the first bug; it's the wrong N to certify
a deployment.

The scaling rule: N grows with the claim. To observe failures at a 1% rate
you need hundreds of trials — around 300 clean trials supports 'ninety-nine
percent plus with reasonable confidence.' Certifying more nines needs orders
of magnitude more, which is why eval cost is a real budget line and why you
tier it: cheap deterministic checks at high N, expensive judge checks at
lower N.

The gate, stated like a statement of work: load-bearing fields — drug,
patient identifiers, seriousness facts — at ninety-nine percent or better
over at least 300 trials, on a held-out golden set the customer's own team
labels, with zero tolerance for hallucination-class failures. Advisory fields
at ninety percent. Re-certification on every prompt or model change. And the
eval report is a deliverable, not an internal artifact."

### Q6. "Where does your ground truth come from? How do you know it's right?"

**Answer:**

"Hand-verified against source, by me — and the 'against source' part is the
whole point. The trap I explicitly avoided: my system produces case files
that look exactly like golden labels, and promoting them would make the eval
'does the system produce what the system produced' — a hundred percent
forever, including on every bug. Circular evaluation is worse than none,
because it enshrines defects behind a green dashboard.

So the chain runs source document → human judgment → golden label, never
through the system. I do use system output as a labeling *draft* — that's
standard bootstrapping — but every field gets verified against the source
text before it's golden. And the golden schema is richer than any output:
it includes must-not-invent lists — statements about what a correct system
*refrains* from doing, which no output file can express.

At customer scale this becomes a labeling pipeline with adjudication —
which, as you know better than I do, is the problem Snorkel was built on.
The hard part of evals isn't the harness; it's deciding what counts as
correct. My golden files carry a notes field with every normalization
ruling for exactly that reason — the rulings are the spec."

### Q7. "Why the Agent SDK and not raw API calls, or LangChain?"

**Answer:**

"On raw API: with the bare API, the agent loop, tool execution, and context
management are my code to write and maintain. The Agent SDK ships the same
harness that runs Claude Code in production — as a library. My repo contains
zero agent-loop code; it contains a pharmacovigilance system. That's the
point.

But the deeper reason is where the governance primitives live. My audit
trail runs on SDK hooks — the runtime invokes my logging function on every
matching tool call, deterministically; the agent cannot skip it or be
prompted out of it. Tool permissions are declared per agent. In a hand-rolled
loop, that enforcement layer usually ends up being... a prompt. Which is a
policy the model can be talked out of.

On LangChain: it's an abstraction across many models — genuinely useful for
portability, and I'd never tell a customer to burn an existing estate;
Claude runs behind it fine. But abstraction layers sit between you and the
model and catch up to new capabilities on a lag. The SDK is first-party —
it's the product's own runtime. My honest framing for a customer: keep the
framework where it serves you; use the native stack for the
governance-critical workloads. And my own architecture — the Pydantic
boundary, the deterministic rulebook — is deliberately stack-agnostic.
Good decisions shouldn't be hostage to a vendor; what's native here is the
harness, the hooks, and the enforcement layer."

### Q8. "What breaks first at a thousand reports a day?"

**Answer (honest, from the production-path notes):**

"Several things, and they're named in the repo as deliberate scope decisions,
not surprises. First: duplicate detection — my own audit log already shows
the same source processed twice under two case IDs, because dedup is a real
PV discipline I explicitly deferred. Second: my case-ID sequence counts files
on disk — honest for a single-process demo, wrong for concurrency; that
becomes a database sequence. Third: sequential agent runs become batch
processing for the non-urgent tier — overnight backlogs don't need
interactive latency and shouldn't pay for it. Fourth: my audit attribution
needs per-subagent precision — the SDK exposes parent_tool_use_id for
exactly that. And the eval program scales from three golden cases to a
labeled corpus with a certification gate in CI.

The meta-answer: I froze scope in an ADR early, and every one of these is
listed there with a rationale. A demo that knows what it isn't is worth more
than a demo pretending to be a product."

### Q9. "How would you manage cost for a customer running this at scale?"

**Answer:**

"Cost management for agents is an architecture discipline, and this system
has the seams built in. Model tiering is the biggest lever: the model lives
in one config property, assignable per agent — extraction at scale belongs
on a Haiku-class model; judgment-heavy steps earn a frontier model. Second:
everything moved from prompt to code is tokens never billed again — my
seriousness rulebook costs nothing to run, forever. Third: prompt caching
for the stable context every call resends — system prompts, the workspace
constitution, schemas. Fourth: batch for the non-interactive tier. And you
watch it: the SDK exports telemetry, so per-workload cost is observable,
not estimated."

### Q10. "What would you build next?"

**Answer:**

"Three things, in order. The runtime quote-grounding check — verify each
supporting quote exists verbatim in source and contains the extracted value;
it's deterministic and closes the groundedness gap we discussed. Second, the
eval program grows up: bigger golden corpus, N sized to the reliability
claim, certification gate wired into CI so no prompt change ships without
re-measurement. Third, I'm wrapping the whole pipeline as an MCP server so
Claude Code becomes the operator console — the system's tools become
conversational: 'process the new report and assess it,' and the multi-agent
pipeline executes underneath with the audit trail accruing. That's the panel
demo."

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