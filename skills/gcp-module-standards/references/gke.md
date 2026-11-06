# GKE

- Private clusters (private nodes; control-plane access via authorized networks or PSC, ranges from variables). Workload Identity on. Shielded nodes and secure boot on.
- Release channel set from a variable; maintenance window and exclusions from variables; no pinned `min_master_version` unless the MR justifies it.
- `remove_default_node_pool = true`, `initial_node_count = 1`; node pools as separate `google_container_node_pool` resources keyed by `for_each` so pools can change without touching the cluster.
- Node pools: autoscaling min/max from variables, `auto_repair` and `auto_upgrade` on, surge or blue-green upgrade settings explicit, dedicated node service account with minimal roles (logging/monitoring writer, artifact registry reader).
- Taints/labels for GPU or special pools defined in the pool object variable; GPU driver installation mode explicit.
- `deletion_protection = true` on clusters. Watch the plan: many cluster attributes force replacement.
- Cluster add-ons and logging/monitoring components declared explicitly, not left to provider defaults that change between versions.
- Everything that lives inside the cluster (namespaces, workloads, RBAC) is GitOps-managed through ArgoCD, not Terraform's kubernetes provider, unless the repo has an explicit bootstrap layer.
