---
name: poc
description: Plan, build and report a time-boxed proof of concept in a sandbox — hypothesis, success and kill criteria, minimal implementation, evidence, teardown. Use when asked to try, spike, prototype or prove out a tool, pattern or design.
claude:
  disable-model-invocation: true
  argument-hint: "<what to prove, e.g. 'Crossplane manages AlloyDB with Orphan delete policy'>"
---

What to prove: {{ARGS}}. If that is missing or vague, ask me for the one question this POC should answer.

A POC answers one question cheaply. It is not a production build: optimise for learning speed and evidence, but never for skipping safety.

## Phase 1: Plan (stop for my approval)
1. Create `poc/<YYYY-MM-DD>-<slug>/` in the current repo (or the location AGENTS.md / CLAUDE.md names for POCs).
2. Write `PLAN.md` from [templates/plan.md](templates/plan.md): hypothesis, success criteria with numbers, kill criteria, timebox, scope in/out, sandbox target, cost cap, teardown plan, risks.
3. The sandbox (project, cluster, kube context, Terragrunt env) comes from my answer or the repo's config. It must not match a prod pattern; if the only available target looks like prod, stop and ask.
4. Show me the plan in five lines and wait for "go". Challenge the hypothesis if it can't fail (then it isn't a test).

## Phase 2: Build the thinnest slice
- Implement only what the success criteria need. Hard-code nothing environment-specific even here: put sandbox values in a `config/` or tfvars/EnvironmentConfig file inside the POC folder so the POC can move projects.
- Reuse existing modules, compositions and functions; note every shortcut taken in `NOTES.md` (it becomes the "production gaps" list).
- Verify as you go with the same checks as real work (validate, plan summary, render/validate for Crossplane, tests). Creating resources in the sandbox still needs my confirmation for each apply.

## Phase 3: Measure and report
- Run the measurements in the success criteria and keep raw evidence (command output, screenshots, timings) under `evidence/`.
- Write `REPORT.md` with the `write-doc` skill's poc-report template: recommendation, results vs criteria, learnings, cost, production gaps, teardown status.
- Teardown: list the exact commands to remove sandbox resources and ask me to run or approve them. Never destroy on your own.

If a kill criterion is hit, stop building, write the report with "Don't adopt" or "Need more data", and say what would be worth trying instead.
