---
name: tf-plan-review
description: Summarize and risk-review Terraform or Terragrunt plans (saved plan file, plan JSON, or a Terragrunt --json-out-dir) instead of reading raw plan output. Use after any plan, before asking for apply.
claude:
  argument-hint: "[plan-file | plan.json | plan-dir] [--chdir root-module-dir]"
  allowed-tools: Bash(python3 {{SKILL_DIR}}/scripts/summarize_plan.py *) Bash(terraform show *) Bash(terragrunt run *)
---

Never paste or read full `terraform plan` / `terragrunt plan` text output; it wastes context. Work from the summary.

1. Produce machine-readable plans if none were given:
   - **Terraform root module:** `terraform plan -out=tfplan -input=false -lock=false` (use the repo's var-file/backend flags from AGENTS.md / CLAUDE.md). Summarize `tfplan`.
   - **Terragrunt (one unit or a stack):** `terragrunt run --all --out-dir .tgplan --json-out-dir .tgplan plan` from the directory whose units you changed. Narrow it with `--filter '<path glob>'` or `--filter-affected` instead of planning the whole tree. Summarize the `.tgplan` directory.
2. Run: `python3 {{SKILL_DIR}}/scripts/summarize_plan.py <plan-file | plan.json | .tgplan>` (several paths allowed). Units without changes are collapsed into one line.
3. Report, in this order:
   - **Verdict**: safe to apply / needs changes / needs a human decision.
   - **Destructive changes**: for each delete/replace, why it happens (the "forced by" attribute) and whether a `moved {}` block, `lifecycle` setting, or argument change avoids it.
   - **Risk flags**: IAM, firewall, public access, deletion protection, stateful resources. Say what to change.
   - **Unexpected changes**: anything the current diff doesn't explain, including drift and changes in Terragrunt units you didn't touch (dependency outputs often cause these).
4. For detail on one resource, filter the plan JSON with `jq` to that single address. Never dump the whole JSON.
5. Never apply. Applying is a human or pipeline step. Add `.tgplan/` and `tfplan*` to `.gitignore` if missing.
