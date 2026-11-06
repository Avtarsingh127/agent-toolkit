#!/usr/bin/env python3
"""Print a bounded map of a repository for the discuss skill.

Usage: repo_map.py [path]

Prints the layout (directories with file counts, never every file), the
technologies detected, key files to read first, recent git activity and any
earlier discussion notes. Every limit and pattern comes from guardrails.json ->
discuss, so the map stays small on large monorepos.
Always exits 0: the skill should still have something to work from.
"""

from __future__ import annotations

import fnmatch
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

DEFAULTS: dict[str, Any] = {
    "notes_dir": ".agents/notes",
    "max_depth": 2,
    "max_tree_lines": 60,
    "max_files_scanned": 20000,
    "max_key_files": 25,
    "key_file_max_depth": 2,
    "recent_commits": 8,
    "hot_dirs_days": 90,
    "hot_dirs_depth": 2,
    "max_hot_dirs": 8,
    "exclude_dirs": [".git", ".terraform", ".terragrunt-cache", "node_modules", ".venv", "venv", "__pycache__"],
    "include_hidden_dirs": [".github", ".gitlab", ".agents", ".claude"],
    "key_files": ["README*", "AGENTS.md", "CLAUDE.md", "Makefile"],
    "signals": {},
}


def load_config() -> dict[str, Any]:
    for parent in Path(__file__).resolve().parents:
        lib = parent / "hooks" / "lib"
        if (lib / "_guardrails_config.py").exists():
            sys.path.insert(0, str(lib))
            try:
                import _guardrails_config as gc  # type: ignore

                return {**DEFAULTS, **(gc.get(gc.load(), "discuss", {}) or {})}
            except SystemExit:
                pass
            break
    return dict(DEFAULTS)


def matches(rel: PurePosixPath, pattern: str) -> bool:
    """Patterns with a slash match the whole relative path; others match the file name."""
    if "/" in pattern:
        return fnmatch.fnmatch(str(rel), pattern)
    return fnmatch.fnmatch(rel.name, pattern)


def scan(root: Path, cfg: dict[str, Any]) -> tuple[list[PurePosixPath], bool]:
    exclude = set(cfg["exclude_dirs"])
    hidden_ok = set(cfg["include_hidden_dirs"])
    files: list[PurePosixPath] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in exclude and (not d.startswith(".") or d in hidden_ok))
        rel_dir = PurePosixPath(Path(dirpath).relative_to(root).as_posix())
        for name in sorted(filenames):
            files.append(rel_dir / name if str(rel_dir) != "." else PurePosixPath(name))
            if len(files) >= cfg["max_files_scanned"]:
                return files, True
    return files, False


def ext_of(path: PurePosixPath) -> str:
    return path.suffix.lower() or path.name


def layout(files: list[PurePosixPath], cfg: dict[str, Any]) -> list[str]:
    depth = int(cfg["max_depth"])
    per_dir: dict[str, Counter[str]] = {}
    for f in files:
        parts = f.parts[:-1]
        for i in range(1, min(len(parts), depth) + 1):
            per_dir.setdefault("/".join(parts[:i]), Counter())[ext_of(f)] += 1
    lines = []
    for d in sorted(per_dir):
        counts = per_dir[d]
        top = ", ".join(f"{n} {e}" for e, n in counts.most_common(3))
        indent = "  " * (d.count("/"))
        total = sum(counts.values())
        lines.append(f"{indent}{d.rsplit('/', 1)[-1]}/  ({total} file{'' if total == 1 else 's'}: {top})")
    limit = int(cfg["max_tree_lines"])
    if len(lines) > limit:
        lines = lines[:limit] + [f"... {len(lines) - limit} more directories (raise discuss.max_tree_lines)"]
    root_files = [f.name for f in files if len(f.parts) == 1]
    if root_files:
        lines.insert(0, "./  " + ", ".join(root_files[:20]) + (" ..." if len(root_files) > 20 else ""))
    return lines


def signals(files: list[PurePosixPath], cfg: dict[str, Any]) -> list[str]:
    out = []
    for tech, patterns in (cfg.get("signals") or {}).items():
        hits = [f for f in files if any(matches(f, p) for p in patterns)]
        if not hits:
            continue
        where = Counter(str(f.parent) if str(f.parent) != "." else "./" for f in hits)
        dirs = ", ".join(d for d, _ in where.most_common(3))
        out.append(f"- {tech}: {len(hits)} file(s), mostly in {dirs}")
    return out


def key_files(files: list[PurePosixPath], cfg: dict[str, Any]) -> list[str]:
    max_depth = int(cfg["key_file_max_depth"])
    picked = [str(f) for f in files if len(f.parts) <= max_depth + 1 and any(matches(f, p) for p in cfg["key_files"])]
    picked.sort(key=lambda p: (p.count("/"), p))
    limit = int(cfg["max_key_files"])
    return picked[:limit] + ([f"... {len(picked) - limit} more"] if len(picked) > limit else [])


def git(root: Path, *args: str) -> str | None:
    proc = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=False)
    return proc.stdout.strip() if proc.returncode == 0 else None


def strip_credentials(url: str) -> str:
    return re.sub(r"(https?://)[^/@]+@", r"\1", url)


def git_section(root: Path, cfg: dict[str, Any]) -> list[str]:
    if git(root, "rev-parse", "--is-inside-work-tree") != "true":
        return ["- not a git repository"]
    out = []
    branch = git(root, "branch", "--show-current") or "(detached)"
    remote = git(root, "remote", "get-url", "origin")
    out.append(f"- Branch: {branch}" + (f" | origin: {strip_credentials(remote)}" if remote else ""))
    log = git(root, "log", "-n", str(cfg["recent_commits"]), "--format=%h %ad %s", "--date=short")
    if log:
        out.append("- Recent commits:")
        out.extend(f"  - {line}" for line in log.splitlines())
    changed = git(root, "log", f"--since={cfg['hot_dirs_days']}.days", "--name-only", "--format=")
    if changed:
        depth = int(cfg["hot_dirs_depth"])
        exclude = set(cfg["exclude_dirs"])
        paths = [PurePosixPath(p) for p in changed.splitlines() if p]
        hot = Counter("/".join(p.parent.parts[:depth]) or "./" for p in paths if not exclude.intersection(p.parts))
        top = ", ".join(f"{d} ({n})" for d, n in hot.most_common(int(cfg["max_hot_dirs"])))
        out.append(f"- Most changed in the last {cfg['hot_dirs_days']} days (file changes): {top}")
    return out


def notes_section(root: Path, cfg: dict[str, Any]) -> list[str]:
    notes_dir = root / cfg["notes_dir"]
    out = [f"- Notes folder: {cfg['notes_dir']}/"]
    notes = sorted(notes_dir.glob("*.md")) if notes_dir.is_dir() else []
    if not notes:
        out.append("- No earlier notes.")
    for note in notes:
        lines = note.read_text(errors="replace").splitlines()
        first = next((ln.lstrip("# ").strip() for ln in lines if ln.strip()), "")
        out.append(f"- {note.relative_to(root).as_posix()}: {first}")
    return out


def main() -> None:
    cfg = load_config()
    root = Path(sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].strip() else ".").expanduser().resolve()
    if not root.is_dir():
        print(f"repo_map: {root} is not a directory")
        return
    files, truncated = scan(root, cfg)
    print(f"# Repo map: {root.name}")
    print(f"{len(files)} files scanned" + (" (stopped at discuss.max_files_scanned)" if truncated else ""))
    print("\n## Layout")
    print("\n".join(layout(files, cfg)) or "(empty)")
    found = signals(files, cfg)
    print("\n## Technologies")
    print("\n".join(found) if found else "- none of the configured signals matched")
    print("\n## Read these first")
    print("\n".join(f"- {k}" for k in key_files(files, cfg)) or "- no key files found")
    print("\n## Git")
    print("\n".join(git_section(root, cfg)))
    print("\n## Earlier discussions")
    print("\n".join(notes_section(root, cfg)))


if __name__ == "__main__":
    main()
