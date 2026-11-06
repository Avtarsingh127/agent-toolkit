# Stateful data services

## AlloyDB / Cloud SQL
- Private IP only (PSA/PSC); no public IP or authorized networks unless the MR justifies it.
- `deletion_protection = true` and `lifecycle { prevent_destroy = true }` on clusters/instances.
- Automated backups and continuous backup / PITR retention from variables; maintenance window from variables.
- Machine sizing, read pool counts, flags (`database_flags`) from typed object variables per environment.
- CMEK via a KMS key ID input when the org requires it.
- IAM database authentication preferred; any initial user password comes from Secret Manager, never a variable default or output.
- Plans that replace a primary instance or cluster are blockers until explained.

## Cloud Storage
- `uniform_bucket_level_access = true`, `public_access_prevention = "enforced"`.
- Versioning and lifecycle rules from variables; `force_destroy = false`.
- Retention policy/locks only with an explicit MR decision (locks are irreversible).

## KMS
- Key rings and keys are never destroyed; `prevent_destroy = true`. Rotation period from a variable.
- Grant `roles/cloudkms.cryptoKeyEncrypterDecrypter` only to the service agents/SAs that need it, per key.
