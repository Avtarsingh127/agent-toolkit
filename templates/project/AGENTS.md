<!-- Project instructions shared by Claude Code (via CLAUDE.md -> @AGENTS.md) and Antigravity (reads AGENTS.md).
     Loaded on every request for everyone on the team: target < 80 lines.
     Only write what an agent can't learn by reading the code. Generic Terraform/Terragrunt/Crossplane/Python
     standards already come from the personal toolkit. Fill the <...> placeholders, delete what doesn't apply. -->

# <repo name>
<One sentence: what this repo provisions/runs and who consumes it.>

## Layout
- `modules/` reusable Terraform modules (no providers/backends inside)
- `live/<env>/<region>/<component>/terragrunt.hcl` Terragrunt units; shared config in `live/root.hcl`, env values in `env.hcl`/`region.hcl`
- `apis/<name>/` Crossplane XRDs, Compositions and `examples/`; `functions.yaml`, `providers.yaml`, `environment/<env>.yaml`
- `k8s/` (or `apps/`) manifests/values synced by ArgoCD ApplicationSets
- `tools/` Python utilities; config via `<config module/path>`

## Ownership boundary
- Terraform/Terragrunt owns: <org, projects, Shared VPC, management clusters, IAM baselines>
- Crossplane owns: <self-service resources, e.g. per-team databases and buckets>
- A resource is never managed by both.

## Commands
- Terragrunt plan (narrow): `cd live && terragrunt run --all --filter '<env>/<region>/<component>' --out-dir .tgplan --json-out-dir .tgplan plan` then `tf-plan-review .tgplan`
- Module checks: `terraform fmt -recursive && terraform validate` · tests: `terraform test` (in the module dir)
- Crossplane: `crossplane-dev` check script on `apis/<name>`
- Python: `uv run pytest <path>` · `ruff check . && ruff format --check .`
- CI: `.gitlab-ci.yml`; MRs via `glab mr create`

## Conventions specific to this repo
- Naming: <prefix pattern and where it's built>
- Labels: <standard label map source>
- Environments: <list> — promotion <dev -> stg -> prod>; prod only via the protected pipeline.
- Docs: <docs/ layout if different from docs/{adr,design,runbooks,postmortems}>; POCs in `poc/`.

## Gotchas
- <e.g. "AlloyDB module: changing network_config replaces the cluster">
- <e.g. "Crossplane provider-gcp family pinned to vX; bump all families together">
