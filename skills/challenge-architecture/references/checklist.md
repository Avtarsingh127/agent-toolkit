# Architecture challenge checklist (GCP platform)

Ask the questions that apply; each finding needs a mechanism, not a vibe.

## Failure and recovery
- What happens on zone loss, region loss, control-plane outage (GKE, Crossplane, ArgoCD), and dependency outage (Cloud SQL/AlloyDB, Pub/Sub, IAM, DNS)?
- Stated RPO/RTO vs what the backups, replicas and failover actually deliver. Has failover been tested? Who triggers it?
- Single points of failure: one cluster, one NAT, one project, one state bucket, one person.
- Retry storms, thundering herds, cascading failure, timeouts that exceed upstream timeouts.

## Scale and limits
- Quotas: IPs per subnet and pod ranges, GKE nodes/pods per cluster, AlloyDB connections, API rate limits, Crossplane provider reconcile throughput, Terraform/Terragrunt run time and state size.
- What grows linearly with tenants/environments (clusters, projects, MRs, states)? Where is the cliff?
- Load shape: peaks, batch windows, noisy neighbours on shared clusters or node pools.

## Security and IAM
- Blast radius of each identity: who can do what on which scope? Any project-level or org-level grants, primitive roles, SA keys, wildcard `iam.serviceAccountUser`?
- Where do secrets live, how are they rotated, who can read them?
- Network exposure: public endpoints, `0.0.0.0/0`, PSC/PSA paths, egress controls, VPC-SC perimeters.
- Supply chain: pinned images/packages/modules/providers, signature or digest checks.

## Operability (day 2)
- How is it upgraded (GKE versions, provider versions, Crossplane and functions, module versions) and how often? What breaks on upgrade?
- Observability: SLIs/SLOs, alerts that page, dashboards, logs with retention and cost. How would on-call know it's broken before users do?
- Drift: who can change it outside Git? How is drift detected and reconciled (Terraform plan drift, Crossplane reconcile, ArgoCD self-heal)?
- Runbooks for the top three failure modes. Can someone other than the author operate it?

## Change, migration and rollback
- Migration path from today's state; dual-running period; data migration and validation.
- Rollback: what is irreversible (schema changes, deletions, IAM removals, KMS)? Is there a point of no return?
- Ownership boundary between Terraform/Terragrunt and Crossplane: can both manage the same resource? Import/adopt plan for existing resources.

## Cost
- Monthly run-rate at today's and 3x scale, with the drivers (nodes, AlloyDB vCPUs, egress, logging, NAT, idle environments).
- Cost of the control plane itself (management clusters, CI minutes, observability).
- What would a 30% cut require?

## Organisation and complexity
- Does the team have the skills to run it? Bus factor?
- Is a new tool (Crossplane, a new function language, an operator) justified versus extending what exists?
- Number of moving parts vs the problem size: what can be removed?

## Evidence
- Which claims are backed by a test, benchmark or production data, and which are assumptions? Propose the cheapest POC that retires the largest unverified assumption.
