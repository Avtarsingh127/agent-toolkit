# Claude Code ↔ Antigravity mapping

Checked against the Antigravity docs (rules, skills, hooks, permissions, MCP pages) on 2026-11-06. Antigravity moves quickly; if a path changes, edit `toolkit.yaml` (or `toolkit.local.yaml`) and run `make install`.

| Concept | Claude Code | Antigravity | How the toolkit bridges it |
|---|---|---|---|
| Always-on instructions | `~/.claude/CLAUDE.md` | `~/.gemini/config/AGENTS.md` (also `~/.gemini/GEMINI.md`) | `core/AGENTS.md` rendered to both; `only:claude` blocks dropped for Antigravity |
| Project instructions | `CLAUDE.md` | `AGENTS.md` (workspace and parents) | project template: `AGENTS.md` + `CLAUDE.md` containing `@AGENTS.md` |
| Path-scoped rules | `~/.claude/rules/*.md`, `paths:` | `~/.gemini/config/rules/*.md`, `trigger: glob` + comma-separated `globs` | neutral `globs:` list rendered per agent |
| Skills | `~/.claude/skills/<n>/SKILL.md` | `~/.gemini/config/skills/<n>/SKILL.md` (`name`, `description`) | Claude-only fields live under `claude:` and are dropped for Antigravity |
| Skill script path | `${CLAUDE_SKILL_DIR}` | none: absolute path | `{{SKILL_DIR}}` rendered per agent |
| Skill arguments | `$ARGUMENTS` | none | `{{ARGS}}` → `$ARGUMENTS` / "the topic given with this request" |
| Manual-only skills | `disable-model-invocation: true` (0 idle tokens) | no equivalent: description always listed | Antigravity pays ~40-80 tokens per manual skill |
| Dynamic context `!`cmd`` | yes | no | `only:antigravity` block tells the agent to run the command |
| Forked skill context / subagent | `context: fork`, `agent:` + `~/.claude/agents/` | subagents defined at runtime (no files) | review/critic skills run inline in Antigravity, told to treat it as a fresh pass |
| Hooks | `settings.json` → `hooks`, exit codes / `hookSpecificOutput` | `~/.gemini/config/hooks.json`, named hooks, `decision` JSON | same scripts; `hooks/lib/agent_io.py` reads/writes each format |
| Hook: block a command | `permissionDecision: deny` | `decision: deny` | `pre_tool_decision()` |
| Hook: no objection | no output | `decision: allow` (configurable: `antigravity.pre_tool_default_decision`) | `pre_tool_no_opinion()` |
| Hook: feedback after edit | `additionalContext` | only `{}` documented | Antigravity gets format-only |
| Hook: session note | stdout | `injectSteps` → `systemMessage` | `session_context()` |
| Permissions | `settings.json` allow/ask/deny, `Bash(cmd *)` | CLI: `~/.gemini/antigravity-cli/settings.json` `command(x)` / `command(regex:…)`; App: Settings UI | CLI merged automatically; App list generated to paste |
| MCP | `.mcp.json` / `claude mcp add` | `~/.gemini/config/mcp_config.json`, `.agents/mcp_config.json`, `serverUrl` for remote | not managed (CLIs preferred); example in project template |

## Things to verify on your machine
- **Session-context hook output shape.** The docs' example nests `systemMessage` inside `systemMessage`; if Antigravity rejects it, change `session_context()` in `hooks/lib/agent_io.py` to the flat form.
- **No-objection decision.** `allow` should hand the call back to Antigravity's normal permission flow. If it behaves like auto-approve, set `antigravity.pre_tool_default_decision` to `ask` in your local guardrails file.
- **Global skills path.** Official docs say `~/.gemini/config/skills/`; some CLI builds also read `~/.gemini/skills/`. If skills don't show up, set `targets.antigravity.skills_dir` in `toolkit.local.yaml`.
