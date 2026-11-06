---
description: Terragrunt live-repo layout, DRY config, dependencies, safe plan commands
globs:
  - "**/terragrunt.hcl"
  - "**/root.hcl"
  - "**/terragrunt.stack.hcl"
  - "**/terragrunt.values.hcl"
  - "**/env.hcl"
  - "**/region.hcl"
  - "**/account.hcl"
  - "**/project.hcl"
---

# Terragrunt rules
- Layout: one unit = one directory with `terragrunt.hcl`, under `<env>/<region>/<component>/`. Shared config lives in `root.hcl` (not a root `terragrunt.hcl`), included with `include "root" { path = find_in_parent_folders("root.hcl") }`.
- Environment values come from hierarchy files (`env.hcl`, `region.hcl`, `project.hcl`) read with `read_terragrunt_config(find_in_parent_folders("env.hcl"))`. Never literal project IDs, regions or CIDRs in a unit.
- `remote_state` (GCS backend) and the provider are generated once in `root.hcl` with `generate` blocks; units don't repeat them. State key = the unit's relative path.
- Module `source` is pinned to a tag or registry version (`?ref=vX.Y.Z`); never a branch. Local paths only while developing a module, never merged.
- `dependency` blocks: set `mock_outputs` and restrict them with `mock_outputs_allowed_terraform_commands = ["validate", "plan", "init"]` so a real apply never uses mocks. Prefer passing outputs over `terraform_remote_state`.
- Plan narrowly: `terragrunt run --all --filter '<path glob>' --out-dir .tgplan --json-out-dir .tgplan plan` (or `--filter-affected`), then the `tf-plan-review` skill on `.tgplan`. Never plan the whole tree without being asked.
- Never run `apply` or `destroy` with `--all` (it auto-approves). Applies go through the pipeline.
- Format and check HCL with `terragrunt hcl fmt` and `terragrunt hcl validate`.
