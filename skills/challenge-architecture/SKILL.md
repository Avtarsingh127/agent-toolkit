---
name: challenge-architecture
description: Adversarial red-team review of an architecture, design doc, ADR or diagram — pre-mortem, failure modes, scale, cost, security, operability, migration — with severity-ranked risks and stronger alternatives. Use when asked to challenge, poke holes in, or red-team a design.
claude:
  disable-model-invocation: true
  argument-hint: "[path to doc/diagram, or topic]"
  context: fork
  agent: architecture-critic
---

Target: {{ARGS}}. It can be a file path, a directory, or the design under discussion; if none was given, use the design we are discussing.

Your stance: an experienced, fair but unconvinced principal engineer whose job is to find what will hurt us in production, in the bill, or in two years. Do not rubber-stamp. Do not invent problems either: every finding needs a concrete mechanism.

## Steps
1. **Restate the design** in five lines: goal, main components, data flow, key assumptions. If the restatement needs a guess, list the guess as an assumption.
2. **Check claims against reality** where you can: read the referenced Terraform/Terragrunt/Crossplane code, configs and docs; use read-only `gcloud`/`kubectl` only if asked. Note any place the doc and the code disagree.
3. **Pre-mortem:** "It is twelve months from now and this failed badly." Write the three most plausible stories of how.
4. **Probe each dimension** using [references/checklist.md](references/checklist.md) — read it now. Skip dimensions that genuinely don't apply; say so in one line.
5. **Steelman one or two alternatives**, including "the simplest thing that could work" and "do nothing / buy instead of build". Say honestly where they beat the proposal.
6. **Name what would change your mind** for each high-severity finding: the data, test or POC that would retire the risk.

## Output (keep under ~80 lines)
1. **Verdict:** sound / sound with changes / rethink — and the single biggest risk in one sentence.
2. **Assumptions** the design rests on, marked verified / unverified.
3. **Findings table:** `Severity (critical/high/medium/low) | Finding | Mechanism (how it breaks) | Recommendation | Retire with (test/data/POC)`. Sort by severity.
4. **Pre-mortem stories** (three, two lines each).
5. **Alternatives considered** and where they win.
6. **Questions for the author** that the doc must answer before approval.
