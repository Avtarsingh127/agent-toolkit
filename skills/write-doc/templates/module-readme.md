# <module or API name>

<One sentence: what it provisions and for whom.>

## Usage

```hcl
module "<name>" {
  source = "<registry or git source>?ref=<version>"

  project_id = var.project_id   # environment values come from the caller
  region     = var.region
  # ...
}
```

<For a Crossplane API, show an example XR instead, with values as placeholders.>

## What it creates
- <resource / composed MR> — <why>

## Design decisions
- <e.g. deletion protection always on; IAM is additive (_member)>

## Inputs and outputs
<!-- BEGIN_TF_DOCS -->
<!-- END_TF_DOCS -->

## Operational notes
- <changes that force replacement, upgrade steps, quotas, known limits>

## Testing
```bash
terraform init -backend=false && terraform validate && terraform test
```

## Changelog
See CHANGELOG.md or release tags.
