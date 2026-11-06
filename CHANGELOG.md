# Changelog

## 2.1.0 — 2026-11-06
- New `discuss` skill: peer senior-architect conversation for repo walkthroughs, new projects and concepts, in both agents. `repo_map.py` prints a bounded repo map (layout, technologies, key files, git activity, earlier notes); limits and patterns live in `guardrails.json -> discuss`. Decisions are kept in `.agents/notes/<topic>.md`.
- Public repo on GitHub: gitleaks secret scan in CI and `make scan`; docs point at the GitHub clone URL.

## 2.0.0 — 2026-11-06
- Repo-based toolkit for Claude Code and Antigravity from one tool-neutral source (`toolkit.yaml`, `make install`).
- New: Terragrunt and Crossplane rules; `crossplane-dev` skill with render + validate script; Terragrunt support in `tf-plan-review`.
- New thinking skills: `grill-me`, `challenge-architecture` (+ `architecture-critic` agent), `poc`.
- New `write-doc` skill (ADR, design, runbook, module README, postmortem, POC report) and `docs` rule; replaces `arch-doc`.
- Hooks work for both agents (shared logic, per-agent I/O); guard covers Terragrunt `--all apply/destroy` and Crossplane deletes.
- Guardrails split into repo defaults, a private local file, and per-repo overrides.

## 1.0.0 — 2026-10-19
- Initial Claude Code kit: CLAUDE.md, Terraform/Python/Kubernetes rules, tf-plan-review, gcp-module-standards, infra-review, arch-doc, handoff, bash guard, post-edit and session hooks.
