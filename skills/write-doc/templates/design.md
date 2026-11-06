# <Title> — Design

| | |
|---|---|
| Author | <name> |
| Reviewers | <names> |
| Status | Draft / In review / Approved |
| Last updated | YYYY-MM-DD |

## 1. Summary
<Three sentences: what, why, outcome.>

## 2. Goals and non-goals
**Goals:** measurable outcomes. **Non-goals:** explicitly out of scope.

## 3. Current state
<Architecture today with evidence (file paths, gcloud/kubectl output). Diagram if it helps (Mermaid).>

## 4. Requirements
- Functional
- Non-functional: availability/SLO, RPO/RTO, scale, latency, security, compliance, cost ceiling

## 5. Proposed design
### 5.1 Architecture
<Components, data flow, Mermaid diagram.>
### 5.2 GCP resources and Terraform
<Modules/stacks added or changed, per-environment configuration inputs (no literal values), state layout.>
### 5.3 Kubernetes / GitOps
<ApplicationSets, overlays, rollout strategy.>
### 5.4 Security and IAM
<Identities, roles, network exposure, secrets.>
### 5.5 Observability
<SLIs, dashboards, alerts, logs.>

## 6. Alternatives considered
| Option | Why not |
|---|---|

## 7. Rollout plan
<Phases per environment, feature flags, gates, rollback.>

## 8. Cost estimate
<Monthly estimate with assumptions; what drives it.>

## 9. Risks and open questions
| Risk / question | Impact | Mitigation / owner |
|---|---|---|
