---
description: Kubernetes manifests, Helm/Kustomize and ArgoCD GitOps
globs:
  - "**/k8s/**/*.yaml"
  - "**/k8s/**/*.yml"
  - "**/manifests/**/*.yaml"
  - "**/charts/**"
  - "**/argocd/**"
  - "**/applicationsets/**"
  - "**/kustomization.yaml"
---

# Kubernetes / GitOps rules
- Changes reach clusters through Git and ArgoCD ApplicationSets. Edit manifests/values; don't `kubectl apply` to shared clusters.
- Every workload: resource requests and limits, readiness/liveness probes, a PodDisruptionBudget when replicas > 1, non-root securityContext, and Workload Identity instead of mounted keys.
- Environment differences live in overlays/values files per environment, never in the base.
- Pin image tags or digests; never `latest`.
- Validate locally with `helm template` / `kustomize build` piped to `kubectl apply --dry-run=client -f -` or `kubeconform` when available.
