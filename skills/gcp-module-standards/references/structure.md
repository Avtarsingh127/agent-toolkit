# Module structure

## Files
- `main.tf` (resources), `variables.tf`, `outputs.tf`, `versions.tf` (required_version + required_providers with `~>` pins), `locals.tf` when locals are non-trivial, `README.md` (generated with terraform-docs if the repo uses it), `tests/`.
- No `provider` blocks, no `backend` blocks, no `terraform.tfvars` inside reusable modules.

## Variables
- Every variable: `description`, explicit `type` (use `object({...})` with `optional()` for grouped settings instead of many loose variables).
- `validation` blocks for anything with a known format: project ID (`^[a-z][a-z0-9-]{4,28}[a-z0-9]$`), region, CIDR (`can(cidrhost(var.x, 0))`), label keys.
- No defaults for environment-specific values (project, region, network, CIDRs, domains). Sensible defaults only for true policy choices (e.g. `deletion_protection = true`).
- Mark secrets `sensitive = true`; prefer passing Secret Manager secret IDs over secret values.

## Naming and labels
- Resource names derive from a `name_prefix`/`naming` input plus a role suffix, built in `locals`. Never inline environment names in strings.
- One `labels` map input merged with module-owned labels in `locals`; apply it to every labelable resource.

## Identity and iteration
- `for_each` over maps keyed by stable names; `count` only for 0/1 toggles.
- Refactors use `moved {}` blocks; adoption of existing resources uses `import {}` blocks reviewed in the MR.

## Outputs
- Only values consumers need (IDs, self links, emails, connection names). Describe each. Never output secrets without `sensitive = true`.

## Root stacks
- One root per environment (or per environment x region), each with its own backend config (`backend.hcl` passed via `-backend-config`), GCS backend with versioning on the state bucket.
- Environment values live in that root's `*.tfvars`; module sources pinned to a tag (`?ref=vX.Y.Z`) or registry version.
