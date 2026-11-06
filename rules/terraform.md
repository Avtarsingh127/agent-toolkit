---
description: Terraform on GCP — module structure, variables, IAM, stateful resources
globs:
  - "**/*.tf"
  - "**/*.tfvars"
  - "**/*.tftest.hcl"
---

# Terraform rules (GCP)
- Every environment-specific value is a variable with `description`, `type`, and a `validation` block where a format is known (project IDs, regions, CIDRs). No defaults for anything that differs per environment.
- Modules never declare `provider` or backend blocks; root stacks (or Terragrunt `generate` blocks) do. Pin providers with `~>` in `versions.tf`; commit `.terraform.lock.hcl`.
- Environments are separate root directories / Terragrunt units with their own tfvars and backend config, not `terraform workspace`.
- Prefer `for_each` over `count` for anything with identity. Use `moved {}` blocks for refactors instead of state surgery; use `import {}` blocks, not `terraform import`.
- IAM: prefer `_member` resources; never `_policy` (authoritative) unless the MR explicitly says so. No primitive roles (owner/editor/viewer) on service accounts. No SA keys.
- Stateful resources (AlloyDB, Cloud SQL, GKE, buckets, KMS) keep `deletion_protection = true` / `prevent_destroy` and are never `force_destroy`.
- Labels: apply the repo's standard label map from a variable/local, never ad-hoc literals.
- Outputs: only what downstream stacks consume; mark secrets `sensitive = true`.
- Check provider argument names against the registry docs for the pinned provider version rather than memory. Detailed standards: the `gcp-module-standards` skill.
