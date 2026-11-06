# agent-toolkit

One versioned source of instructions, rules, skills, subagents and guardrail hooks for **Claude Code** (VS Code / CLI) and **Google Antigravity** (App, IDE, CLI), tuned for GCP platform engineering: Terraform, Terragrunt, Crossplane, GKE/ArgoCD and Python.

Sources are tool-neutral. `make install` renders them into each agent's format and links them into place, so `git pull && make install` updates both agents at once.

```bash
make doctor        # tools present? guard works for both agents?
make dry-run       # what install would change
make install       # install (conflicts are reported, never overwritten)
make install-force # replace conflicts after backing them up (use when migrating from the v1 kit)
make status        # what's installed + always-on token cost per agent
make test          # 30 tests: guard decisions for both agents, render/install/uninstall, scripts
make scan          # secret scan of history and uncommitted changes (CI runs it on every push)
```

Repo: https://github.com/Avtarsingh127/agent-toolkit (public: never commit prod names, project IDs or credentials; they belong in the local files below).

Full Mac setup: [docs/mac-setup.md](docs/mac-setup.md). How Antigravity maps to Claude Code: [docs/antigravity.md](docs/antigravity.md). Changing things: [docs/customizing.md](docs/customizing.md).

## Catalog

**Always on** (~1.1K tokens per agent): `core/AGENTS.md` → `~/.claude/CLAUDE.md` and `~/.gemini/config/AGENTS.md`. How you work, config-driven code, CLIs first, definition of done per kind of change, documentation defaults.

### Rules — load only when a matching file is touched
| Rule | Triggers on | Covers |
|---|---|---|
| `terraform` | `*.tf`, `*.tfvars`, `*.tftest.hcl` | variables/validation, no providers in modules, `for_each`, `moved`/`import` blocks, IAM `_member`, stateful protection |
| `terragrunt` | `terragrunt.hcl`, `root.hcl`, `*.stack.hcl`, `env.hcl`, `region.hcl` … | `root.hcl` + hierarchy files, generated backend/provider, pinned sources, `mock_outputs` limits, narrow `--filter` plans, never `--all apply` |
| `crossplane` | `crossplane/**`, `xrd*.yaml`, `composition*.yaml`, `apis/**` … | v2 namespaced XRDs, Pipeline mode, `.m.` MRs, EnvironmentConfigs, Orphan/Usage for stateful, Workload Identity ProviderConfigs, pinned packages |
| `python` | `*.py` | typed settings object, ADC, injected clients, pytest, ruff |
| `kubernetes` | `k8s/**`, `charts/**`, `argocd/**`, `kustomization.yaml` | GitOps only, probes/limits/PDB, overlays per env, pinned images |
| `docs` | `docs/**/*.md`, `README.md`, `adr/**`, `runbooks/**`, `poc/**` | point-first writing, Mermaid, cited claims, copy-pasteable commands with rollback |

### Skills — description listed, body loaded on use
| Skill | Kind | What it does |
|---|---|---|
| `tf-plan-review` | auto | Summarizes Terraform plans or a Terragrunt `--json-out-dir` into counts, deletes/replaces with the forcing attribute, risk flags, drift — never raw plan text |
| `gcp-module-standards` | auto | Module standards split into 6 references (structure, IAM, networking, GKE, data services, testing) read on demand |
| `crossplane-dev` | auto | XRD/Composition authoring loop with `xp_check.py`: render every Composition against its example XRs, validate against schemas, flag v1 leftovers and unprotected stateful MRs |
| `write-doc` | auto | House templates: ADR, design doc, runbook, module README, postmortem, POC report |
| `infra-review` | manual (`/infra-review`) | Bounded diff review across Terraform/Terragrunt/Crossplane/K8s/Python; Claude runs it in a fresh `infra-reviewer` subagent |
| `discuss` | manual | Peer architect conversation: maps a repo first (`repo_map.py`: layout, tech, key files, git activity), shapes a new project, or explains a concept; keeps decision notes in `.agents/notes/` |
| `grill-me` | manual | One question at a time, with a recommended answer, until every decision is explicit; ends in a decision log |
| `challenge-architecture` | manual | Red-team review: pre-mortem, failure/scale/security/cost/operability checklist, severity-ranked findings, steelmanned alternatives; Claude runs it in the `architecture-critic` subagent (Opus) |
| `poc` | manual | Time-boxed POC: PLAN.md with hypothesis, success + kill criteria → thinnest slice in a sandbox → REPORT.md → teardown commands |
| `handoff` | manual | Handoff note so a fresh session (either agent) continues the task |

"Manual" skills cost zero idle tokens in Claude (`disable-model-invocation`); Antigravity lists every skill's description.

### Claude subagents (Claude Code only)
`infra-reviewer` (Sonnet, read-only), `gcp-investigator` (Sonnet, read-only live GCP/GKE/Crossplane triage), `architecture-critic` (Opus, read-only red team).

### Hooks — run outside the model (same scripts, per-agent I/O)
| Hook | Claude Code | Antigravity |
|---|---|---|
| Guard (`pre_bash_guard.py`) | `PreToolUse` on `Bash` | `PreToolUse` on `run_command` |
| Post-edit (`post_edit_check.py`) | formats, returns remaining lint failures (capped) | formats only (Antigravity documents no PostToolUse feedback) |
| Session context (`session_context.py`) | prints active gcloud project + kube context | `injectSteps` system message |

The guard hard-blocks: terraform/terragrunt destroy, auto-approve, `--all apply`, state surgery, force-unlock, deleting Crossplane XRDs/Compositions/packages/managed resources, namespace/PVC/CRD deletes, bulk deletes, project deletes, recursive bucket deletes, force-push. It asks before mutations aimed at a prod project, kube context or prod directory (by flag, env prefix, active config or path). Broken config = everything blocked.

## Configuration
| File | In git? | Purpose |
|---|---|---|
| `toolkit.yaml` | yes | install paths per agent, which components go where |
| `toolkit.local.yaml` | no | your machine's overrides (paths, excluded skills) |
| `config/guardrails.json` | yes | guard patterns, formatters, review/plan/crossplane/discuss settings |
| `~/.config/agent-toolkit/guardrails.json` | no | your real prod naming (created on first install) |
| `<repo>/.agents/guardrails.json` | per repo | repo-specific patterns (`*_extra` keys append) |

## Layout
```
core/AGENTS.md          always-on instructions (only:<agent> blocks for agent-specific lines)
rules/*.md              neutral frontmatter: description, globs, optional activation
skills/<name>/          SKILL.md (+ scripts/, references/, templates/); claude:/antigravity: frontmatter maps
agents/*.md             Claude subagents
hooks/                  guard, post-edit, session-context; hooks/lib/agent_io.py translates payloads
targets/<agent>/        settings/hooks/permissions templates
templates/project/      AGENTS.md, CLAUDE.md (@AGENTS.md), .agents/guardrails.json for repos
tools/toolkit.py        build / install / uninstall / status / doctor / new-skill / new-rule / init-project
tests/                  unittest suite
```
