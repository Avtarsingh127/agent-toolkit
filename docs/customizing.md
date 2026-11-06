# Customizing the toolkit

Rule of thumb for where a change goes:

| You noticed… | Put it in | Idle cost |
|---|---|---|
| The agent gets something wrong in every repo | `core/AGENTS.md` (keep it short) | every request |
| It gets something wrong for one kind of file | a rule: `make new-rule NAME=x`, set `globs` | 0 until a matching file is touched |
| You repeat the same multi-step prompt | a skill: `make new-skill NAME=x` | ~50-80 tokens listed (0 in Claude if manual-only) |
| Something must happen every time, no exceptions | a hook + `config/guardrails.json` | 0 |
| One repo is different | that repo's `AGENTS.md` or `.agents/guardrails.json` | per repo |
| Only your machine is different | `toolkit.local.yaml`, `~/.config/agent-toolkit/guardrails.json` | 0 |

## Writing sources once for both agents
- Skill frontmatter: `name` and `description` for everyone; anything Claude-specific under `claude:` (e.g. `disable-model-invocation`, `context: fork`, `agent`, `allowed-tools`, `argument-hint`, `paths`), Antigravity-specific under `antigravity:`. Set `skip: true` under one agent to keep a skill out of it.
- Use `{{SKILL_DIR}}` for bundled files and `{{ARGS}}` for what was typed after the slash command.
- Agent-specific lines: wrap in `<!-- only:claude -->` … `<!-- end -->` (or `only:antigravity`). All other HTML comments are stripped at build time, so they are free notes.
- Rules: `description`, `globs`, optional `activation: always | model_decision | manual` (model_decision/manual are Antigravity-only; Claude skips them).

## Turning things off
```yaml
# toolkit.local.yaml
components:
  skills: {include: ["*"], exclude: ["handoff"]}       # both agents
target_components:
  antigravity:
    skills: {include: ["*"], exclude: ["infra-review"]} # one agent
  claude:
    hooks: {include: ["guard", "session-context"], exclude: []}
targets:
  antigravity: {enabled: false}                         # whole agent
```
`make install` removes links for anything no longer selected.

## Release habit
1. Change sources, add or adjust a test in `tests/` when you touch hooks or scripts.
2. `make test && make lint && make status` (check the always-on token cost didn't creep).
3. `make install`, try it in both agents.
4. Add a line to `CHANGELOG.md`, commit, push.
