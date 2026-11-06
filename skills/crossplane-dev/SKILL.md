---
name: crossplane-dev
description: Design, write and verify Crossplane v2 APIs on GCP — XRDs, Pipeline Compositions with functions, EnvironmentConfigs, example XRs — with a render + schema-validate loop. Use for any Crossplane authoring, review or debugging.
claude:
  argument-hint: "[api directory or task]"
---

Work on Crossplane APIs following the `crossplane` rule. Read [references/patterns.md](references/patterns.md) before designing a new API or Composition.

## Authoring loop
1. **Find the conventions in this repo first:** API layout (e.g. `apis/<name>/{definition,composition}.yaml` + `examples/`), which composition functions are used (patch-and-transform, go-templating, KCL, Python), where `Function`/`Provider` manifests and EnvironmentConfigs live, and the provider family and version pinned. Follow them.
2. **Design the API before the Composition:** the XR spec is a contract for platform consumers. Small, intention-revealing fields (`size: small|medium|large`, `environment`) over raw provider knobs; defaults and enums in the XRD schema; status fields consumers need (connection info refs, endpoints).
3. **Write the Composition** in Pipeline mode. Environment values come from EnvironmentConfigs (function-environment-configs) or XR fields, never literals. End the pipeline with `function-auto-ready` if the repo uses it.
4. **Add or update an example XR** under `examples/` for every Composition (one per meaningful variant).
5. **Verify:**
   `uv run --quiet --script {{SKILL_DIR}}/scripts/xp_check.py <api-dir>`
   (no uv: `python3 -m pip install --user pyyaml`, then `python3 {{SKILL_DIR}}/scripts/xp_check.py <api-dir>`). It renders each Composition against its examples, validates the output against the XRD and provider schemas, and flags v1 leftovers and stateful resources without delete protection. Needs Docker running for functions. Add `--observed` / `--required` files to test later reconcile stages or EnvironmentConfig lookups.
6. Fix until `Result: PASS`. Report the summary, not raw render output.

## Debugging a live API (read-only)
- `crossplane resource trace <kind>/<name> -n <ns>` (or `crossplane beta trace` on older CLIs) to find the failing composed resource; then `kubectl describe` that MR and read its conditions and events.
- `kubectl get mrds` / `kubectl get managedresourceactivationpolicies` when a kind isn't served.
- Never fix live state with `kubectl apply/patch/delete`; change Git and let ArgoCD sync. Deleting an MR deletes the cloud resource unless `deletionPolicy: Orphan`.

## Terraform/Terragrunt and Crossplane together
- One owner per cloud resource. When moving a resource from Terraform to Crossplane: remove it from Terraform state with a reviewed `removed {}` block (lifecycle `destroy = false`), then adopt it in Crossplane with `crossplane.io/external-name` and `managementPolicies: ["Observe"]` first, switch to full management after the diff is clean.
