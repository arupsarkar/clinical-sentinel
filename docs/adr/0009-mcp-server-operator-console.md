# ADR 0009: MCP server as operator console, human gate preserved

**Status:** Accepted · **Date:** 2026-07-25 · **Extends scope per panel requirement (supersedes 0005 scope list, adds WS8)**

## Context
The interview panel requires a demonstration built with Claude Code. The
pipeline already has clean command/orchestration separation, making a
second frontend cheap. Exposing the system as MCP tools lets any MCP
client — Claude Code for the demo — operate it conversationally.

## Decisions
1. **No approve tool — the human gate survives by omission.** The MCP
   surface exposes intake, assess, draft, list_pending, and audit_tail,
   but deliberately NOT approve. Promotion out of pending_review/
   remains a human-only CLI action. A new surface must not weaken
   Principle 7; the strongest enforcement is absence.
2. **stdio transport.** The client launches the server as a subprocess
   and speaks over pipes: zero infrastructure, faithful to the local
   operator-console use case. HTTP transport is the production path for
   shared deployment, noted and deferred.
3. **Tools return text, never print.** stdio transport owns stdout for
   protocol frames; command handlers (which print) are not reused —
   MCP tools call the orchestrators directly.
4. **The operator is audited.** Every MCP tool invocation logs
   actor `operator:mcp`, adding a fourth actor class to the trail:
   who asked, who read, who decided, who approved.

## Consequences
CLI and MCP are now two thin frontends over the same orchestrators.
The demo can show Claude Code chaining the pipeline agentically while
the audit trail records the full causal chain — and refusing approval,
which is the point.