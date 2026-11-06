---
description: Writing standards for Markdown docs, READMEs, ADRs and runbooks
globs:
  - "**/docs/**/*.md"
  - "**/README.md"
  - "**/adr/**/*.md"
  - "**/runbooks/**/*.md"
  - "**/poc/**/*.md"
---

# Documentation rules
- First sentence of a doc and of each section states the point (decision, answer, outcome, number). No "This document describes…".
- Audience first: an on-call engineer at 3 a.m. for runbooks, a reviewer with 10 minutes for design docs, a consumer of the module for READMEs.
- Structure carries meaning: tables for comparisons and inputs/outputs, numbered steps for procedures, Mermaid for flows and architecture (`flowchart LR`, `sequenceDiagram`). Keep diagrams under ~15 nodes.
- Every claim about current state cites a file path, command, dashboard or ticket. Unknowns become explicit open questions, never guesses.
- Commands in runbooks are copy-pasteable, read-only checks before mutations, and every mutation has its rollback next to it.
- No environment-specific values baked into prose or examples; show them as `<project-id>` placeholders or point to the config that holds them.
- Short sentences, no filler, no emoji. Dates as YYYY-MM-DD. Link, don't duplicate: point to the source of truth.
