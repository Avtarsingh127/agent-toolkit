---
name: gcp-module-standards
description: Detailed standards for designing, writing and reviewing GCP Terraform modules and root stacks (structure, IAM, networking, GKE, AlloyDB/Cloud SQL, storage, KMS, testing). Use when creating or refactoring a module or reviewing module design.
claude:
  paths:
    - "**/*.tf"
    - "**/*.tftest.hcl"
---

# GCP Terraform module standards

The always-on essentials are in the `terraform` rule. This skill holds the detail. Load only the reference you need:

| Topic | File | Read when |
|---|---|---|
| Module layout, variables, outputs, versioning | [references/structure.md](references/structure.md) | creating or refactoring any module |
| IAM and service accounts | [references/iam.md](references/iam.md) | any `*_iam_*`, service account, or Workload Identity change |
| VPC, subnets, firewall, PSC, DNS | [references/networking.md](references/networking.md) | network resources |
| GKE clusters and node pools | [references/gke.md](references/gke.md) | `google_container_*` |
| AlloyDB, Cloud SQL, GCS, KMS | [references/data.md](references/data.md) | stateful resources |
| Tests and CI | [references/testing.md](references/testing.md) | adding tests or pipeline steps |

Workflow for a new module:
1. Read `structure.md`, then the topic file(s) for the resources involved.
2. Look at one existing module in this repo and follow its conventions where they don't conflict with these standards.
3. Write the module, then a `tests/*.tftest.hcl` with `command = plan` and mocked providers where possible.
4. Run `terraform fmt -recursive`, `terraform init -backend=false`, `terraform validate`, and `terraform test`.
