# Testing and CI

## Local loop
`terraform fmt -recursive` -> `terraform init -backend=false` -> `terraform validate` -> `tflint` (if configured) -> `trivy config .` or `checkov -d .` (if configured) -> `terraform test`.

## terraform test
- `tests/*.tftest.hcl` with `command = plan` runs by default; `mock_provider "google" {}` so unit tests need no credentials.
- Assert on: computed names/labels, `for_each` keys, validation failures (`expect_failures = [var.x]`), and that protective settings stay on.
- Integration tests that create real resources run only in a sandbox project supplied by CI variables, never locally by default.

## GitLab CI (typical stages)
1. `fmt -check` + `validate` + lint + security scan on every MR.
2. `plan -out` per affected root, with `terraform show -json` artifact and a summarized plan posted to the MR.
3. Manual, protected `apply` job on the default branch using the exact plan artifact; Workload Identity Federation for credentials.
