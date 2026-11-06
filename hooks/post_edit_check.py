#!/usr/bin/env python3
"""PostToolUse formatter + linter (Claude Code Edit/Write, Antigravity file-edit tools).

Runs the configured `fix` steps silently (formatters, safe auto-fixes), then the
`check` step. Claude gets remaining failures back (capped); Antigravity only
documents an empty PostToolUse response, so there it formats and stays silent.
A clean file costs zero context tokens. Commands come from guardrails.json -> post_edit.
"""

from __future__ import annotations

import fnmatch
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import _guardrails_config as gc  # noqa: E402
import agent_io  # noqa: E402


def language_for(path: Path, languages: dict) -> str | None:
    for lang, spec in languages.items():
        if lang.startswith("_") or not isinstance(spec, dict):
            continue
        if any(fnmatch.fnmatch(path.name, g) or fnmatch.fnmatch(str(path), g) for g in spec.get("globs", [])):
            return lang
    return None


def run(argv: list[str], file: str, cwd: str | None) -> tuple[int, str]:
    if not argv:
        return 0, ""
    argv = [a.replace("{file}", file).replace("{dir}", str(Path(file).parent)) for a in argv]
    if not shutil.which(argv[0]):
        return 0, ""
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=60, cwd=cwd, check=False)
    except (subprocess.TimeoutExpired, OSError) as exc:
        return 1, f"{argv[0]} failed to run: {exc}"
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def main() -> None:
    event = agent_io.read_event()
    if event.target == agent_io.ANTIGRAVITY and event.tool not in agent_io.AG_EDIT_TOOLS:
        agent_io.post_tool_feedback(event, None)
    file_path = event.file_path
    if not file_path or not Path(file_path).is_file():
        agent_io.post_tool_feedback(event, None)

    try:
        cfg = gc.load(event.cwd)
    except SystemExit:
        agent_io.post_tool_feedback(event, None)  # best-effort; the guard reports config errors

    languages = gc.get(cfg, "post_edit.languages", {})
    lang = language_for(Path(file_path), languages)
    spec = languages.get(lang, {}) if lang else {}
    if not spec.get("enabled", False):
        agent_io.post_tool_feedback(event, None)

    # Fix steps are silent: anything they can't fix shows up in the check step.
    for step in spec.get("fix", []):
        run(step, file_path, event.cwd)

    code, out = run(spec.get("check", []), file_path, event.cwd)
    if code == 0 or not out:
        agent_io.post_tool_feedback(event, None)

    max_lines = int(gc.get(cfg, "post_edit.max_feedback_lines", 25))
    lines = out.splitlines()
    shown = lines[:max_lines] + ([f"... {len(lines) - max_lines} more lines"] if len(lines) > max_lines else [])
    agent_io.post_tool_feedback(event, f"{lang} checks still failing for {file_path}:\n" + "\n".join(shown))


if __name__ == "__main__":
    main()
