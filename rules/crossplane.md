---
description: Crossplane v2 APIs, compositions, functions and GCP providers
globs:
  - "**/crossplane/**"
  - "**/xrd*.yaml"
  - "**/definition*.yaml"
  - "**/composition*.yaml"
  - "**/functions*.yaml"
  - "**/apis/**/*.yaml"
  - "**/xr*.yaml"
  - "**/crossplane.yaml"
---

# Crossplane rules (v2)
- New APIs are v2 XRDs (`apiextensions.crossplane.io/v2`) with `scope: Namespaced` unless the API must be cluster-wide. No new claims or `LegacyCluster` XRDs; don't change Compositions already used by live legacy XRs.
- Compositions use `mode: Pipeline` with composition functions (patch-and-transform, go-templating, KCL or Python as the repo already uses). Native `mode: Resources` is removed in v2.
- Compose namespaced managed resources (API groups with `.m.`, e.g. `*.gcp.m.upbound.io`); confirm group/version with `kubectl get mrds` or the provider docs for the pinned version, not memory.
- Environment-specific values (project, region, network, CIDRs, sizes) come from EnvironmentConfigs via function-environment-configs or from XR fields, never literals in the Composition.
- Stateful MRs (AlloyDB/Cloud SQL, GKE, buckets, KMS, networks) set `deletionPolicy: Orphan` or `managementPolicies` without `Delete`, and use `Usage` objects to protect dependencies from deletion order mistakes.
- Provider credentials: one `ProviderConfig` per environment using Workload Identity (`InjectedIdentity`) via a `DeploymentRuntimeConfig`; no JSON keys in secrets.
- Packages (`Provider`, `Function`, `Configuration`) use fully qualified, pinned versions (tag or digest). Activate only needed MRDs with a `ManagedResourceActivationPolicy` when the repo does so.
- XRD schemas: required fields, enums, defaults and `x-kubernetes-validations` for invariants; keep status fields the platform consumers need.
- Every Composition has an example XR under `examples/` and must pass render + schema validation (the `crossplane-dev` skill) before review. Changes reach clusters through Git/ArgoCD, never `kubectl apply`.
