---
name: write-doc
description: Create or update engineering docs from house templates — ADR, design doc, runbook, module README, postmortem, POC report. Use whenever asked to write or document something as a file in a repo.
claude:
  argument-hint: "adr|design|runbook|readme|postmortem|poc-report <title or path>"
---

Write a document of the requested type. If the type isn't given, infer it from the request and say which one you chose.

| Type | Template | Default location | Naming |
|---|---|---|---|
| adr | [templates/adr.md](templates/adr.md) | `docs/adr/` | `NNNN-kebab-title.md`, next number after the highest existing |
| design | [templates/design.md](templates/design.md) | `docs/design/` | `kebab-title.md` |
| runbook | [templates/runbook.md](templates/runbook.md) | `docs/runbooks/` | `<service>-<symptom>.md` |
| readme | [templates/module-readme.md](templates/module-readme.md) | the module/package root | `README.md` |
| postmortem | [templates/postmortem.md](templates/postmortem.md) | `docs/postmortems/` | `YYYY-MM-DD-kebab-title.md` |
| poc-report | [templates/poc-report.md](templates/poc-report.md) | the POC folder | `REPORT.md` |

Steps:
1. **Location:** follow the repo's existing doc layout if it has one (look for `docs/`, `adr/`, `decisions/`, `runbooks/`, or instructions in AGENTS.md / CLAUDE.md). Use the defaults above only when nothing exists.
2. **Facts first:** gather current state before writing. For more than a handful of files, use a subagent or a focused search and bring back only: affected components, Terraform/Terragrunt/Crossplane code involved, environments, constraints (quotas, SLOs, compliance).
3. **Ask only what only I know** (drivers, deadlines, budget, owners, non-negotiables): at most 4 questions per round, and stop once the template's required sections can be filled. Mark anything still unknown as an open question in the doc.
4. **Fill the template.** Delete sections that truly don't apply rather than writing "N/A". Mermaid for diagrams. Environment values as placeholders or references to config.
5. **Generated reference sections:** for a Terraform module README, run `terraform-docs markdown table .` if it is installed and paste between the `BEGIN_TF_DOCS` markers; otherwise build the inputs/outputs tables from `variables.tf` / `outputs.tf`. For a Crossplane API, document the XRD's spec fields from its schema.
6. **Self-check before saving:** first sentence of each section states its point; every current-state claim cites a path/command; no hard-coded environment values; commands are copy-pasteable.
7. Save, then reply with the path and a three-line summary. Don't paste the whole document into chat.
