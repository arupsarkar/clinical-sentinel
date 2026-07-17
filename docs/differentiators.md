# Differentiators — Living Document

Talking points for "why this stack?" objections, maintained like an
SA battle card. Rule of the document: every claim is either
**demonstrated in this repo** (marked ⚙️) or **verify-current before
using** (marked 📅 — check docs/pricing the week of the meeting).
Never argue a competitor is bad; show what is structurally different.

---

## 1. Why Claude

**The harness, not just the model.** ⚙️ The Agent SDK is the same
agent loop, tool execution, and context management that runs Claude
Code in production at enormous scale — exposed as a library. This
repo contains zero agent-loop code; it contains a pharmacovigilance
system. With a raw-API build, the loop is my problem; here it's the
vendor's product.

**Model behavior you can architect on.** ⚙️ The intake agent's
honesty guarantees (absent data stays absent, evidence quotes,
"incomplete is a valid outcome") are *designed with* the model's
instruction-following and refusal behavior, not against it. For
regulated buyers, calibrated refusal is a feature.

**Safety as research program, not marketing page.** Anthropic's
differentiation for HLS/financial customers is that interpretability
and steerability are the company's core research agenda — the
guarantees regulated industries ask about are what the vendor is
*for*. 📅 Cite current published work, not memory.

**First-party velocity.** New model/runtime capabilities land in the
SDK the day they ship, because the SDK is the product's own runtime —
no abstraction layer waiting to catch up.

**Talk track:** "You can build an agent loop on any frontier model.
What I'm demonstrating is what production agent architecture looks
like — and where the stack differences surface is exactly where
enterprises get hurt: governance, auditability, failure modes."

---

## 2. Security

**Least-privilege agents, declared not coded.** ⚙️ Each agent's tool
grant lives in its frontmatter (`tools: Read, Glob`). The intake
agent physically cannot write or reach the network. Reviewable by a
compliance officer in a text editor.

**Deterministic enforcement layer.** ⚙️ Hooks fire on every matching
tool call at the runtime level — the agent cannot skip, forget, or be
prompted out of the audit trail. Contrast: in a hand-rolled loop, the
enforcement layer is usually a prompt — a policy the model can be
talked out of. Hooks can also *block* (deny-rules), not just observe.

**Boundary validation.** ⚙️ LLM output enters the system through one
door: schema validation. Nonconforming output dies at the boundary
(`ValidationError`), never downstream.

**Data governance in the audit design.** ⚙️ Logs record which file
was touched, never contents — the audit trail must not become a
second copy of patient data.

**Deployment posture.** Claude is consumable inside existing
enterprise trust boundaries — cloud marketplaces (Bedrock, Vertex,
Foundry) and gateway patterns for centralized credentials and
controls. 📅 Verify current platform list + enterprise features
(SSO, ZDR availability) before citing.

**Talk track:** "Safety controls here are architecture, not prompts:
schema validation, tool permissions, deterministic hooks, human
gates. Nothing that can be talked out of its behavior."

---

## 3. Interoperability

**MCP — the open standard the industry adopted.** Anthropic created
the Model Context Protocol and opened it; it is now the de-facto
standard for connecting AI to enterprise systems, with broad
cross-vendor adoption. For a customer, MCP connectors are an
investment that outlives any single model choice. 📅 Verify current
adoption examples before naming names.

**The architecture is portable by design.** ⚙️ This repo's Pydantic
boundary, deterministic rulebook, and audit pattern are
stack-agnostic — deliberately. The honest pitch: "your domain model
and governance patterns survive a vendor change; what's native here
is the harness, hooks, and plan mode." Conceding portability of good
architecture builds more trust than claiming lock-in-as-feature.

**Meets existing estates where they are.** Claude runs behind
common frameworks (LangChain et al.) and gateways; the native SDK
is the recommendation for *governance-critical* workloads, not a
demand to burn existing investments. Salesforce parallel: same
posture as Data 360 coexisting with customer lakehouses — composable,
not rip-and-replace.

**Talk track:** "Frameworks abstract across models; the SDK is
vertically integrated with one. I'd tell a customer: keep the
framework estate, use the native stack where audit and control are
the requirement — and MCP means your integration work is portable
either way."

---

## 4. How to Manage Cost

**Model tiering — the biggest lever.** Match model to task: frontier
models for judgment-heavy steps, smaller/faster models (Haiku-class)
for extraction and classification at scale. ⚙️ This repo centralizes
the model choice in `Settings` — per-agent model assignment is a
one-line change per agent, which is the demo answer to "how would
you cut this bill 10x for the intake tier?" 📅 Verify current model
lineup + pricing before quoting numbers.

**Prompt caching.** Repeated context (system prompts, CLAUDE.md,
schemas) can be cached and re-read at a fraction of input cost — the
single most impactful optimization for agent workloads that resend
stable context every call. 📅 Verify current cache pricing/TTL.

**Deterministic work stays deterministic.** ⚙️ The seriousness
rulebook is a free Python script, not a model call. Every rule moved
from prompt to code is tokens that never get billed again — cost
control as an architecture principle, not a procurement negotiation.

**Batch and async where latency doesn't matter.** Non-interactive
workloads (overnight case backlogs) belong on batch processing at
discounted rates. 📅 Verify current batch discount.

**Right-size the context, observe the spend.** Context management
(compaction, session hygiene) controls the quadratic cost of long
agent sessions; OpenTelemetry export from the SDK gives per-workload
cost observability — the enterprise answer to "who's spending what."

**Talk track:** "Cost management for agents is an architecture
discipline: tier the models per agent, cache the stable context,
move rules from prompts to code, batch the non-urgent. My demo
already has the seams for all four — that's why the model lives in
config and the rulebook lives in a script."

---