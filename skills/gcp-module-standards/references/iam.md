# IAM and service accounts

- Use additive `google_*_iam_member` resources. `_binding` is authoritative for one role and `_policy` for the whole resource; use them only when the MR states that authority is intended, and never mix them with `_member` for the same role/resource.
- No primitive roles (`roles/owner`, `roles/editor`, `roles/viewer`) for service accounts or groups in code. Pick the narrowest predefined role, or a custom role defined in Terraform.
- Grant to groups and service accounts, not individual users.
- One service account per workload. Workloads on GKE use Workload Identity (`roles/iam.workloadIdentityUser` on the GSA for `serviceAccount:<project>.svc.id.goog[<ns>/<ksa>]`), all values from variables.
- `google_service_account_key` is a finding. CI uses Workload Identity Federation (GitLab OIDC) instead of keys.
- Conditional bindings (`condition {}`) for time-boxed or resource-scoped access; give the condition a title and description.
- Cross-project grants are called out explicitly in the MR description.
- Review question for every IAM change: who gains what, on which resource scope, and is there a narrower option?
