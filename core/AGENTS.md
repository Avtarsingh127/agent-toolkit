<!-- Shared always-on instructions. Rendered to ~/.claude/CLAUDE.md and ~/.gemini/config/AGENTS.md.
     Loaded on EVERY request by both agents: keep it under ~45 lines.
     HTML comments are stripped at build time. Agent-specific lines go in only:<agent> blocks.
     Language/tool standards live in rules/ (loaded only for matching files); procedures in skills/. -->

# How I work
- I'm a staff-level cloud platform engineer (GCP: GKE, AlloyDB, IAM, VPC; Terraform + Terragrunt; Crossplane; Python; ArgoCD GitOps; GitLab CI). Skip basics; be direct.
- Config-driven by default: no environment-specific values (project IDs, regions, CIDRs, bucket/cluster names, emails, URLs) in code. Put them in variables, tfvars, Terragrunt env/region HCL, Crossplane EnvironmentConfigs, or config files, and reference them.
- Prefer CLIs over MCP tools for GCP and Git work: `gcloud`, `bq`, `kubectl`, `terraform`, `terragrunt`, `crossplane`, `glab`. Read-only first; ask before anything that mutates.
- Production changes go through Git (MR -> CI -> ArgoCD / Terraform / Terragrunt pipeline), never applied from this machine.
- Tell me when you think I'm wrong. Disagree with evidence; don't just agree.

# Workflow
- Non-trivial change (multiple files, unfamiliar code, or infra with blast radius): plan first, wait for my OK, then implement.
- Give me evidence, not assertions: the command you ran and its relevant output.
- Definition of done, by kind of change:
  - Terraform module: `terraform fmt`, `terraform validate`, `terraform test`.
  - Terraform/Terragrunt stack: saved plan, then the `tf-plan-review` skill on it.
  - Crossplane: render + schema-validate with the `crossplane-dev` skill's check script.
  - Python: `ruff check`, `ruff format --check`, the narrowest relevant `pytest`.
- Large reads, log digging or broad searches: delegate to a subagent when available and bring back only findings.
- If I correct you twice on the same thing, stop and tell me the instruction you were missing so I can add it to the toolkit.

# Documents
- Docs are Markdown in the repo (default `docs/`; follow existing layout). Diagrams in Mermaid. Use the `write-doc` skill's templates for ADRs, design docs, runbooks, READMEs, postmortems and POC reports.
- Lead with the decision or answer; tables for comparisons; every claim about current state cites a file path or command.

# Output
- Reviews: findings ordered blocker / should-fix / nit, each with file:line and a concrete fix.
- Architecture: assumptions, options with trade-offs, a recommendation, and what would change it.
<!-- only:claude -->

# Compact instructions
When compacting, keep: the task goal, files changed, commands that verify the work, open decisions, and any prod-related warnings.
<!-- end -->
