# Crossplane v2 patterns for a GCP platform

## Where Crossplane fits next to Terraform/Terragrunt
- **Terraform/Terragrunt:** foundations that change rarely and need plan review — org/folders, projects, Shared VPC, the management cluster that runs Crossplane, IAM baselines.
- **Crossplane:** self-service, per-team or per-app resources that consumers request through a Kubernetes API (databases, buckets, service accounts with Workload Identity, Pub/Sub), reconciled continuously and delivered by ArgoCD.
- Never let both manage the same resource. Document the boundary in the repo's AGENTS.md.

## API layout
```
apis/<api-name>/
  definition.yaml        # XRD, apiextensions.crossplane.io/v2, scope: Namespaced
  composition.yaml       # mode: Pipeline
  examples/
    small.yaml           # example XRs used by render tests
functions.yaml           # Function packages (pinned) used by all compositions
providers.yaml           # Provider packages (pinned), DeploymentRuntimeConfig
environment/<env>.yaml   # EnvironmentConfig per environment (project, region, network, labels)
```

## XRD essentials
```yaml
apiVersion: apiextensions.crossplane.io/v2
kind: CompositeResourceDefinition
metadata:
  name: postgresdbs.platform.example.org
spec:
  group: platform.example.org
  names: {kind: PostgresDB, plural: postgresdbs}
  scope: Namespaced
  versions:
    - name: v1alpha1
      served: true
      referenceable: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              required: [size]
              properties:
                size: {type: string, enum: [small, medium, large], default: small}
                deletionProtection: {type: boolean, default: true}
            status:
              type: object
              properties:
                endpoint: {type: string}
```
Use `x-kubernetes-validations` (CEL) for cross-field rules, e.g. immutable fields: `self == oldSelf`.

## Composition essentials
```yaml
apiVersion: apiextensions.crossplane.io/v1
kind: Composition
metadata:
  name: postgresdb-gcp
spec:
  compositeTypeRef: {apiVersion: platform.example.org/v1alpha1, kind: PostgresDB}
  mode: Pipeline
  pipeline:
    - step: environment
      functionRef: {name: function-environment-configs}
      input:
        apiVersion: environmentconfigs.fn.crossplane.io/v1beta1
        kind: Input
        spec:
          environmentConfigs:
            - type: Selector
              selector:
                matchLabels:
                  - {key: environment, type: FromCompositeFieldPath, valueFromFieldPath: metadata.namespace}
    - step: resources
      functionRef: {name: function-go-templating}   # or the repo's choice
      input: {}   # templates read .context["apiextensions.crossplane.io/environment"] for project/region
    - step: ready
      functionRef: {name: function-auto-ready}
```
Check the function input schemas for the pinned function versions; they evolve.

## Safety defaults for stateful resources
- `deletionPolicy: Orphan` (or `managementPolicies: ["Create","Update","Observe","LateInitialize"]`) on databases, buckets, KMS keys, networks.
- `Usage` objects so a network or KMS key can't be deleted while a database uses it.
- Provider-level `deletion_protection`-style fields set from the XR's `deletionProtection` (default true).

## Providers on GKE
- Upjet GCP family providers (install only the families you use), pinned versions.
- `DeploymentRuntimeConfig` sets the KSA annotated for Workload Identity; `ProviderConfig` per environment with `credentials.source: InjectedIdentity` and the target project from config.
- Limit served MRDs with a `ManagedResourceActivationPolicy` to cut API server load on clusters with many providers.

## Testing ladder
1. `xp_check.py` (render + validate) on every change, in CI too.
2. Composition tests with expected-output assertions if the repo uses a test framework for functions (e.g. KCL/Python unit tests).
3. A sandbox control plane for end-to-end: apply the example XR via ArgoCD, `crossplane resource trace` until Ready, then delete and confirm Orphan behaviour.
