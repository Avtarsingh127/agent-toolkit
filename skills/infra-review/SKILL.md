---
name: infra-review
description: Review the current branch's Terraform, Terragrunt, Crossplane, Kubernetes, CI and Python changes against platform standards, as a separate reviewer. Use for MR/PR review.
claude:
  argument-hint: "[base-ref]"
  disable-model-invocation: true
  context: fork
  agent: infra-reviewer
  allowed-tools: Bash(python3 {{SKILL_DIR}}/scripts/diff_context.py*)
---

Review the change set below. You are a separate reviewer: you did not write this code, so judge it on its own terms.

<!-- only:claude -->
!`python3 {{SKILL_DIR}}/scripts/diff_context.py {{ARGS}}`
<!-- end -->
<!-- only:antigravity -->
First run `python3 {{SKILL_DIR}}/scripts/diff_context.py [base-ref]` (base ref from the request, else the configured default) and review its output. Treat the review as a fresh pass: don't defend changes you made earlier in this conversation.
<!-- end -->

## What to check
- **Correctness:** will it plan/apply/deploy/reconcile as intended? Run `terraform validate` in touched root modules, `terragrunt hcl validate` for touched units, the `crossplane-dev` check script for touched APIs, and `ruff check` on touched Python when it helps you confirm.
- **Blast radius:** deletes/replacements of stateful resources, IAM widening, network exposure, changes that hit every environment at once (a `root.hcl` or shared module edit, a Composition used by many XRs, a function version bump).
- **Config-driven:** any hard-coded project ID, region, CIDR, bucket, cluster, email or URL in a module, unit or Composition is a finding.
- **Terragrunt:** pinned module sources, `mock_outputs` limited to validate/plan, no duplicated remote_state/provider config.
- **Crossplane:** v2 XRDs and Pipeline mode for new APIs, stateful MRs protected (Orphan / managementPolicies / Usage), example XR updated, pinned packages, one owner per cloud resource (not also in Terraform).
- **GitOps:** cluster changes flow through manifests/values/ApplicationSets; environment differences through overlays, tfvars, env HCL or EnvironmentConfigs.
- **Tests and docs:** new inputs documented and validated; Python changes have tests; runbooks/ADRs updated when behaviour changes.

## Output (keep under ~60 lines)
1. One-line verdict: approve / approve with nits / request changes.
2. Findings grouped **Blocker**, **Should fix**, **Nit**; each with `file:line`, the problem, and the concrete fix.
3. Anything you could not verify and why.
Report only issues that affect correctness, safety, operability or the stated standards. No style opinions the formatter already handles.
