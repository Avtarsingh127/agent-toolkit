#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6"]
# ///
"""agent-toolkit: one source of rules, skills and hooks for Claude Code and Antigravity.

  toolkit.py build                        render build/<target>/ from the sources
  toolkit.py install [--force] [--dry-run] [--target T]
                                          build, link into each agent, merge settings
  toolkit.py uninstall [--target T]       remove everything install placed
  toolkit.py status                       what is installed, conflicts, idle token cost
  toolkit.py doctor                       check tools and smoke-test the hooks
  toolkit.py new-skill NAME               scaffold skills/NAME/SKILL.md
  toolkit.py new-rule NAME                scaffold rules/NAME.md
  toolkit.py init-project REPO            add AGENTS.md/CLAUDE.md/.agents to a repo

Sources are tool-neutral; everything agent-specific comes from toolkit.yaml
(+ toolkit.local.yaml) and targets/<agent>/ templates.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML is required: run through `make` (uses uv or a local .venv) or `pip install pyyaml`.")

REPO = Path(__file__).resolve().parents[1]
BUILD_ROOT = Path(os.environ.get("AGENT_TOOLKIT_BUILD_DIR") or REPO / "build").resolve()
TARGETS = ("claude", "antigravity")
MANAGED_HOOK_SCRIPTS = ("/hooks/pre_bash_guard.py", "/hooks/post_edit_check.py", "/hooks/session_context.py")
COND = re.compile(r"<!--\s*only:([a-z,\s]+?)\s*-->\n?(.*?)<!--\s*end\s*-->\n?", re.S)
COMMENT = re.compile(r"<!--.*?-->\n?", re.S)


# --------------------------------------------------------------------------- config


def deep_merge(base: Any, over: Any) -> Any:
    if isinstance(base, dict) and isinstance(over, dict):
        out = dict(base)
        for k, v in over.items():
            out[k] = deep_merge(base.get(k), v) if k in base else v
        return out
    return over


def load_config(path: Path | None = None) -> dict[str, Any]:
    path = path or REPO / "toolkit.yaml"
    cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    local = path.with_name("toolkit.local.yaml")
    if local.exists():
        cfg = deep_merge(cfg, yaml.safe_load(local.read_text(encoding="utf-8")) or {})
    return cfg


def expand(p: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(p)))


def selected(cfg: dict[str, Any], kind: str, target: str, names: list[str]) -> list[str]:
    spec = (cfg.get("target_components", {}).get(target, {}) or {}).get(kind) or cfg.get("components", {}).get(kind, {})
    inc, exc = spec.get("include", ["*"]), spec.get("exclude", [])
    return [n for n in names if any(fnmatch.fnmatch(n, p) for p in inc) and not any(fnmatch.fnmatch(n, p) for p in exc)]


# --------------------------------------------------------------------------- markdown


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return yaml.safe_load(text[4:end]) or {}, text[end + 5 :]
    return {}, text


def join_frontmatter(fm: dict[str, Any], body: str) -> str:
    if not fm:
        return body.lstrip("\n")
    dumped = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True, width=10_000).strip()
    return f"---\n{dumped}\n---\n\n{body.lstrip(chr(10))}"


def render_text(text: str, target: str, skill_dir: str = "", args_token: str = "") -> str:
    text = COND.sub(lambda m: m.group(2) if target in [t.strip() for t in m.group(1).split(",")] else "", text)
    text = COMMENT.sub("", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.replace("{{SKILL_DIR}}", skill_dir).replace("{{ARGS}}", args_token)


def render_skill_frontmatter(fm: dict[str, Any], target: str) -> dict[str, Any]:
    out = {k: v for k, v in fm.items() if k not in TARGETS}
    out.update(fm.get(target) or {})
    return out


def render_rule_frontmatter(fm: dict[str, Any], target: str) -> dict[str, Any] | None:
    globs = fm.get("globs") or []
    activation = fm.get("activation") or ("glob" if globs else "always")
    if target == "claude":
        if activation == "glob":
            return {"paths": globs}
        if activation == "always":
            return {}
        return None  # model_decision/manual rules have no Claude equivalent: make a skill instead
    fm_ag: dict[str, Any] = {"trigger": {"always": "always_on"}.get(activation, activation)}
    if fm.get("description"):
        fm_ag["description"] = fm["description"]
    if activation == "glob":
        fm_ag["globs"] = ", ".join(globs)
    return fm_ag


# --------------------------------------------------------------------------- build


def names_in(folder: Path, suffix: str = "") -> list[str]:
    if not folder.exists():
        return []
    if suffix:
        return sorted(p.stem for p in folder.glob(f"*{suffix}") if p.is_file())
    return sorted(p.name for p in folder.iterdir() if (p / "SKILL.md").exists())


def tokens(text: str) -> int:
    return round(len(text) / 3.8)


def json_template(path: Path, cfg: dict[str, Any]) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    subs = {"__PYTHON__": cfg.get("python", "python3"), "__REPO__": str(REPO), "__HOME__": str(Path.home())}
    for token, value in subs.items():
        raw = raw.replace(token, json.dumps(value)[1:-1])
    return json.loads(raw)


def build(cfg: dict[str, Any], build_root: Path) -> dict[str, dict[str, Any]]:
    """Render every enabled target. Returns a plan of {target: {placements, fragments}}."""
    plans: dict[str, dict[str, Any]] = {}
    for target in TARGETS:
        tcfg = cfg.get("targets", {}).get(target, {})
        if not tcfg.get("enabled", False):
            continue
        out = build_root / target
        if out.exists():
            shutil.rmtree(out)
        out.mkdir(parents=True)
        placements: list[tuple[Path, Path]] = []  # (built source, install destination)
        idle: list[tuple[str, int]] = []

        # Always-on instructions
        core = render_text((REPO / "core" / "AGENTS.md").read_text(encoding="utf-8"), target)
        (out / "instructions.md").write_text(core, encoding="utf-8")
        placements.append((out / "instructions.md", expand(tcfg["instructions_file"])))
        idle.append(("instructions", tokens(core)))

        # Rules
        (out / "rules").mkdir()
        for name in selected(cfg, "rules", target, names_in(REPO / "rules", ".md")):
            fm, body = split_frontmatter((REPO / "rules" / f"{name}.md").read_text(encoding="utf-8"))
            tfm = render_rule_frontmatter(fm, target)
            if tfm is None:
                print(f"  skip rule {name} for {target}: activation {fm.get('activation')} unsupported")
                continue
            dst = out / "rules" / f"{name}.md"
            dst.write_text(join_frontmatter(tfm, render_text(body, target)), encoding="utf-8")
            placements.append((dst, expand(tcfg["rules_dir"]) / f"{name}.md"))
            if not fm.get("globs") and fm.get("activation", "always") == "always":
                idle.append((f"rule {name}", tokens(body)))

        # Skills
        (out / "skills").mkdir()
        skills_dir = expand(tcfg["skills_dir"])
        for name in selected(cfg, "skills", target, names_in(REPO / "skills")):
            src = REPO / "skills" / name
            fm, body = split_frontmatter((src / "SKILL.md").read_text(encoding="utf-8"))
            if (fm.get(target) or {}).get("skip"):
                continue
            skill_token = tcfg.get("skill_dir_token") or str(skills_dir / name)
            tfm = render_skill_frontmatter(fm, target)
            tfm.pop("skip", None)
            dst = out / "skills" / name
            dst.mkdir()
            rendered = render_text(join_frontmatter(tfm, body), target, skill_token, tcfg.get("args_token", ""))
            (dst / "SKILL.md").write_text(rendered, encoding="utf-8")
            for entry in src.iterdir():
                if entry.name != "SKILL.md" and not entry.name.startswith("."):
                    (dst / entry.name).symlink_to(entry)
            placements.append((dst, skills_dir / name))
            if not tfm.get("disable-model-invocation"):
                idle.append((f"skill {name}", tokens(f"{tfm.get('name', name)}: {tfm.get('description', '')}")))

        fragments: dict[str, Any] = {}
        hook_names = selected(cfg, "hooks", target, ["guard", "post-edit", "session-context"])

        if target == "claude":
            (out / "agents").mkdir()
            for name in selected(cfg, "agents", target, names_in(REPO / "agents", ".md")):
                text = render_text((REPO / "agents" / f"{name}.md").read_text(encoding="utf-8"), target)
                dst = out / "agents" / f"{name}.md"
                dst.write_text(text, encoding="utf-8")
                placements.append((dst, expand(tcfg["agents_dir"]) / f"{name}.md"))
                fm, _ = split_frontmatter(text)
                idle.append((f"agent {name}", tokens(f"{fm.get('name')}: {fm.get('description', '')}")))
            tpl = json_template(REPO / "targets" / "claude" / "settings.template.json", cfg)
            hooks: dict[str, list] = {}
            for comp in hook_names:
                for event, groups in tpl["hooks_by_component"].get(comp, {}).items():
                    hooks.setdefault(event, []).extend(groups)
            fragments["settings"] = {"permissions": tpl["permissions"], "hooks": hooks}
            (out / "settings.fragment.json").write_text(json.dumps(fragments["settings"], indent=2), encoding="utf-8")
        else:
            tpl = json_template(REPO / "targets" / "antigravity" / "hooks.template.json", cfg)
            hooks_frag: dict[str, Any] = {}
            for comp in hook_names:
                hooks_frag.update(tpl["hooks_by_component"].get(comp, {}))
            fragments["hooks"] = hooks_frag
            perms = json_template(REPO / "targets" / "antigravity" / "permissions.template.json", cfg)["permissions"]
            fragments["permissions"] = perms
            (out / "hooks.fragment.json").write_text(json.dumps(hooks_frag, indent=2), encoding="utf-8")
            (out / "app-permissions.txt").write_text(
                "Paste into Antigravity: Settings > General > Global Permissions\n\n"
                + "\n\n".join(f"[{k.upper()}]\n" + "\n".join(v) for k, v in perms.items())
                + "\n",
                encoding="utf-8",
            )
        idle_hooks = 40 if "session-context" in hook_names else 0
        idle.append(("session-context hook", idle_hooks))
        plans[target] = {"placements": placements, "fragments": fragments, "idle": idle, "config": tcfg}
        print(f"built {target}: {len(placements)} items -> {out}")
    return plans


# --------------------------------------------------------------------------- install helpers


def is_ours(path: Path) -> bool:
    if not path.is_symlink():
        return False
    target = Path(os.path.realpath(path))
    return any(root in target.parents or target == root for root in (REPO, BUILD_ROOT))


def manifest_path() -> Path:
    return expand("~/.config/agent-toolkit/manifest.json")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8").strip()
    return json.loads(text) if text else {}


def write_json(path: Path, data: dict[str, Any], backup_root: Path, dry: bool) -> None:
    new = json.dumps(data, indent=2) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == new:
        return
    if dry:
        print(f"  would write {path}")
        return
    if path.exists():
        dst = backup_root / path.relative_to(Path.home()) if Path.home() in path.parents else backup_root / path.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dst)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new, encoding="utf-8")
    print(f"  merged {path}")


def place(src: Path, dst: Path, force: bool, dry: bool, backup_root: Path) -> str:
    if dst.is_symlink():
        if Path(os.path.realpath(dst)) == Path(os.path.realpath(src)):
            return "ok"
        if not is_ours(dst) and not force:
            return "conflict (foreign symlink)"
        if not dry:
            dst.unlink()
    elif dst.exists():
        if not force:
            return "conflict (existing file; rerun with --force to back it up and replace)"
        if not dry:
            backup = backup_root / (dst.relative_to(Path.home()) if Path.home() in dst.parents else dst.name)
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(dst), str(backup))
    if dry:
        return "would link"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.symlink_to(src)
    return "linked"


def strip_managed_hooks(hooks: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for event, groups in (hooks or {}).items():
        kept = [
            g
            for g in groups
            if not any(any(s in (h.get("command") or "") for s in MANAGED_HOOK_SCRIPTS) for h in g.get("hooks", []))
        ]
        if kept:
            out[event] = kept
    return out


def merge_permissions(current: dict[str, Any], new: dict[str, list], previous: dict[str, list]) -> dict[str, Any]:
    out = dict(current or {})
    for key in ("allow", "ask", "deny"):
        stale = set(previous.get(key, [])) - set(new.get(key, []))
        merged = [p for p in out.get(key, []) if p not in stale]
        merged += [p for p in new.get(key, []) if p not in merged]
        out[key] = merged
    return out


# --------------------------------------------------------------------------- commands


def cmd_install(cfg: dict[str, Any], args: argparse.Namespace) -> None:
    plans = build(cfg, BUILD_ROOT)
    manifest = read_json(manifest_path())
    backup_root = expand(cfg.get("backup_dir", "~/.agent-toolkit-backups")) / time.strftime("%Y%m%d-%H%M%S")
    conflicts = 0
    new_manifest: dict[str, Any] = {"repo": str(REPO), "targets": dict(manifest.get("targets", {}))}
    for target, plan in plans.items():
        if args.target and args.target != target:
            continue
        print(f"\n== {target}")
        prev = manifest.get("targets", {}).get(target, {})
        wanted = {str(dst) for _, dst in plan["placements"]}
        for old in prev.get("links", []):
            p = Path(old)
            if old not in wanted and is_ours(p):
                print(f"  removed stale {p}")
                if not args.dry_run:
                    p.unlink()
        links = []
        for src, dst in plan["placements"]:
            state = place(src, dst, args.force, args.dry_run, backup_root)
            if state.startswith("conflict"):
                conflicts += 1
            else:
                links.append(str(dst))
            if state != "ok":
                print(f"  {state}: {dst}")
        tcfg = plan["config"]
        entry: dict[str, Any] = {"links": links}
        if target == "claude":
            path = expand(tcfg["settings_file"])
            settings = read_json(path)
            frag = plan["fragments"]["settings"]
            settings["permissions"] = merge_permissions(
                settings.get("permissions", {}), frag["permissions"], prev.get("permissions", {})
            )
            hooks = strip_managed_hooks(settings.get("hooks", {}))
            for event, groups in frag["hooks"].items():
                hooks.setdefault(event, []).extend(groups)
            settings["hooks"] = hooks
            write_json(path, settings, backup_root, args.dry_run)
            entry["permissions"] = frag["permissions"]
        else:
            path = expand(tcfg["hooks_file"])
            hooks = {k: v for k, v in read_json(path).items() if not k.startswith("agent-toolkit-")}
            hooks.update(plan["fragments"]["hooks"])
            write_json(path, hooks, backup_root, args.dry_run)
            if tcfg.get("manage_cli_permissions", True):
                spath = expand(tcfg["cli_settings_file"])
                settings = read_json(spath)
                settings["permissions"] = merge_permissions(
                    settings.get("permissions", {}), plan["fragments"]["permissions"], prev.get("permissions", {})
                )
                write_json(spath, settings, backup_root, args.dry_run)
                entry["permissions"] = plan["fragments"]["permissions"]
            print(f"  Antigravity App permissions to paste: {BUILD_ROOT / 'antigravity' / 'app-permissions.txt'}")
        new_manifest["targets"][target] = entry
    if not args.dry_run:
        manifest_path().parent.mkdir(parents=True, exist_ok=True)
        manifest_path().write_text(json.dumps(new_manifest, indent=2), encoding="utf-8")
        local = expand(cfg.get("guardrails", {}).get("local", "~/.config/agent-toolkit/guardrails.json"))
        if not local.exists():
            local.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO / "config" / "guardrails.local.example.json", local)
            print(f"\ncreated {local}: put your real prod project/context naming there")
    if backup_root.exists():
        print(f"\nbackups: {backup_root}")
    if conflicts:
        print(f"\n{conflicts} conflict(s) left untouched. Review them, then rerun with --force to back up and replace.")
        sys.exit(1)


def cmd_uninstall(cfg: dict[str, Any], args: argparse.Namespace) -> None:
    manifest = read_json(manifest_path())
    backup_root = expand(cfg.get("backup_dir", "~/.agent-toolkit-backups")) / time.strftime("%Y%m%d-%H%M%S")
    for target, entry in list(manifest.get("targets", {}).items()):
        if args.target and args.target != target:
            continue
        tcfg = cfg["targets"][target]
        for link in entry.get("links", []):
            p = Path(link)
            if is_ours(p):
                p.unlink()
                print(f"  removed {p}")
        empty: dict[str, list] = {"allow": [], "ask": [], "deny": []}
        if target == "claude":
            path = expand(tcfg["settings_file"])
            s = read_json(path)
            if s:
                s["hooks"] = strip_managed_hooks(s.get("hooks", {}))
                s["permissions"] = merge_permissions(s.get("permissions", {}), empty, entry.get("permissions", {}))
                write_json(path, s, backup_root, False)
        else:
            path = expand(tcfg["hooks_file"])
            h = read_json(path)
            if h:
                write_json(path, {k: v for k, v in h.items() if not k.startswith("agent-toolkit-")}, backup_root, False)
            spath = expand(tcfg["cli_settings_file"])
            s = read_json(spath)
            if s and entry.get("permissions"):
                s["permissions"] = merge_permissions(s.get("permissions", {}), empty, entry["permissions"])
                write_json(spath, s, backup_root, False)
        manifest["targets"].pop(target)
    manifest_path().parent.mkdir(parents=True, exist_ok=True)
    manifest_path().write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("uninstalled. Your guardrails.local file and backups were kept.")


def cmd_status(cfg: dict[str, Any], _: argparse.Namespace) -> None:
    plans = build(cfg, BUILD_ROOT)
    for target, plan in plans.items():
        print(f"\n== {target}")
        for src, dst in plan["placements"]:
            if dst.is_symlink() and Path(os.path.realpath(dst)) == Path(os.path.realpath(src)):
                state = "installed"
            elif dst.exists() or dst.is_symlink():
                state = "CONFLICT"
            else:
                state = "not installed"
            print(f"  {state:14} {dst}")
        total = sum(n for _, n in plan["idle"])
        print(f"  always-on context: ~{total} tokens")
        for label, n in plan["idle"]:
            print(f"    {n:5}  {label}")


def cmd_doctor(cfg: dict[str, Any], _: argparse.Namespace) -> None:
    ok = True
    print(f"python {sys.version.split()[0]} (needs >= 3.10): {'ok' if sys.version_info >= (3, 10) else 'TOO OLD'}")
    ok &= sys.version_info >= (3, 10)
    hook_py = cfg.get("python", "python3")
    print(f"hook interpreter {hook_py}: {shutil.which(hook_py) or 'NOT FOUND'}")
    ok &= bool(shutil.which(hook_py))
    for tool in ["git", "claude", "agy", "gcloud", "kubectl", "terraform", "terragrunt", "crossplane", "helm",
                 "argocd", "ruff", "jq", "yq", "shellcheck", "tflint", "glab", "uv"]:  # fmt: skip
        print(f"  {'ok ' if shutil.which(tool) else '-- '} {tool}")
    probes = {
        "claude": {"tool_name": "Bash", "tool_input": {"command": "terraform destroy"}, "cwd": str(REPO)},
        "antigravity": {"toolCall": {"name": "run_command", "args": {"CommandLine": "terraform destroy"}}},
    }
    for target, payload in probes.items():
        proc = subprocess.run(
            [hook_py, str(REPO / "hooks" / "pre_bash_guard.py"), "--target", target],
            input=json.dumps(payload), capture_output=True, text=True, check=False,
        )  # fmt: skip
        try:
            out = json.loads(proc.stdout)
            denied = "deny" in json.dumps(out)
        except json.JSONDecodeError:
            denied = False
        print(
            f"guard smoke test ({target}): {'ok, destroy denied' if denied else 'FAILED: ' + proc.stdout + proc.stderr}"
        )
        ok &= denied
    sys.exit(0 if ok else 1)


SKILL_SCAFFOLD = """---
name: {name}
description: <What it does and when to use it, in one sentence. This line is always in context; keep it specific.>
claude:
  # Claude-only frontmatter, e.g.:
  # disable-model-invocation: true     # only runs when you type /{name}; costs zero idle tokens
  # argument-hint: "[arg]"
antigravity: {{}}
---

<Instructions, written for any agent. Reference bundled files as {{{{SKILL_DIR}}}}/scripts/x.py.
Keep this file short; put long material in references/ and say when to read it.>
<!-- only:claude -->
<Claude-only lines go between these markers.>
<!-- end -->
"""

RULE_SCAFFOLD = """---
description: <one line: what the rule covers>
globs:
  - "**/*.ext"
# activation: glob | always | model_decision | manual   (default: glob when globs are set, else always)
---

# {title} rules
- <Only what the agent gets wrong without being told. Each line is loaded whenever a matching file is touched.>
"""


def cmd_new(kind: str, name: str) -> None:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", name):
        sys.exit("name must be lowercase letters, digits and hyphens")
    if kind == "skill":
        path = REPO / "skills" / name / "SKILL.md"
        content = SKILL_SCAFFOLD.format(name=name)
    else:
        path = REPO / "rules" / f"{name}.md"
        content = RULE_SCAFFOLD.format(title=name.replace("-", " ").title())
    if path.exists():
        sys.exit(f"{path} already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"created {path.relative_to(REPO)}; edit it, then `make install`")


def cmd_init_project(repo_path: str, force: bool) -> None:
    repo = Path(repo_path).expanduser().resolve()
    if not repo.is_dir():
        sys.exit(f"not a directory: {repo}")
    tpl = REPO / "templates" / "project"
    copies = {
        "AGENTS.md": "AGENTS.md",
        "CLAUDE.md": "CLAUDE.md",
        "guardrails.json": ".agents/guardrails.json",
        "mcp.json.example": ".mcp.json.example",
    }
    for src, dst in copies.items():
        target = repo / dst
        if target.exists() and not force:
            print(f"  kept existing {dst}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(tpl / src, target)
        print(f"  wrote {dst}")
    settings = repo / ".claude" / "settings.json"
    current = read_json(settings)
    frag = json.loads((tpl / "claude-settings.json").read_text(encoding="utf-8"))
    current["permissions"] = merge_permissions(current.get("permissions", {}), frag["permissions"], {})
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
    print("  merged .claude/settings.json")
    gitignore = repo / ".gitignore"
    lines = gitignore.read_text(encoding="utf-8").splitlines() if gitignore.exists() else []
    added = [ln for ln in (tpl / "gitignore.snippet").read_text(encoding="utf-8").splitlines()
             if ln.strip() and not ln.startswith("#") and ln not in lines]  # fmt: skip
    if added:
        gitignore.write_text("\n".join(lines + added) + "\n", encoding="utf-8")
        print(f"  .gitignore += {', '.join(added)}")
    print(
        f"\nNext: fill the <placeholders> in {repo / 'AGENTS.md'} and commit AGENTS.md, CLAUDE.md, .agents/, .claude/."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", type=Path, help="alternate toolkit.yaml")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    p_install = sub.add_parser("install")
    p_install.add_argument("--force", action="store_true")
    p_install.add_argument("--dry-run", action="store_true")
    p_install.add_argument("--target", choices=TARGETS)
    p_un = sub.add_parser("uninstall")
    p_un.add_argument("--target", choices=TARGETS)
    sub.add_parser("status")
    sub.add_parser("doctor")
    for kind in ("skill", "rule"):
        p = sub.add_parser(f"new-{kind}")
        p.add_argument("name")
    p_init = sub.add_parser("init-project")
    p_init.add_argument("repo")
    p_init.add_argument("--force", action="store_true")
    args = parser.parse_args()
    cfg = load_config(args.config)

    if args.cmd == "build":
        build(cfg, BUILD_ROOT)
    elif args.cmd == "install":
        cmd_install(cfg, args)
    elif args.cmd == "uninstall":
        cmd_uninstall(cfg, args)
    elif args.cmd == "status":
        cmd_status(cfg, args)
    elif args.cmd == "doctor":
        cmd_doctor(cfg, args)
    elif args.cmd == "init-project":
        cmd_init_project(args.repo, args.force)
    else:
        cmd_new(args.cmd.removeprefix("new-"), args.name)


if __name__ == "__main__":
    main()
