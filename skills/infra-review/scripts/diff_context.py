#!/usr/bin/env python3
"""Print a bounded review context: changed-file stat plus the diff against the
merge-base with the base ref (committed + uncommitted changes).

Usage: diff_context.py [base-ref]
Base ref, line cap and excluded globs come from guardrails.json -> review.
Always exits 0: a non-zero exit would abort the skill that injects this output.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULTS: dict[str, Any] = {"base_ref": "origin/main", "max_diff_lines": 1500, "exclude_globs": []}


def git(*args: str) -> tuple[int, str]:
    proc = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    return proc.returncode, proc.stdout if proc.returncode == 0 else proc.stderr


def load_config() -> dict[str, Any]:
    for parent in Path(__file__).resolve().parents:
        lib = parent / "hooks" / "lib"
        if (lib / "_guardrails_config.py").exists():
            sys.path.insert(0, str(lib))
            try:
                import _guardrails_config as gc  # type: ignore

                return {**DEFAULTS, **(gc.get(gc.load(), "review", {}) or {})}
            except SystemExit:
                pass
            break
    return dict(DEFAULTS)


def main() -> None:
    cfg = load_config()
    base = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].strip() else cfg["base_ref"]

    code, _ = git("rev-parse", "--is-inside-work-tree")
    if code != 0:
        print("Not inside a git repository; nothing to review.")
        return

    code, merge_base = git("merge-base", base, "HEAD")
    if code != 0:
        print(
            f"Could not find merge-base with '{base}' ({merge_base.strip()}). "
            f"Pass a base ref, e.g. /infra-review origin/develop. Falling back to HEAD (uncommitted changes only)."
        )
        merge_base = "HEAD"
    merge_base = merge_base.strip()

    excludes = [f":(exclude,glob){g}" for g in cfg["exclude_globs"]]
    _, stat = git("diff", "--stat=120", merge_base, "--", ".", *excludes)
    _, untracked = git("ls-files", "--others", "--exclude-standard")
    _, diff = git("diff", "--unified=5", "--no-color", merge_base, "--", ".", *excludes)

    print(f"Base: {base} (merge-base {merge_base[:12]})\n")
    print("### Changed files")
    print(stat.strip() or "(no tracked changes)")
    if untracked.strip():
        print("\nUntracked files (not in diff, read them if relevant):")
        print("\n".join(f"- {u}" for u in untracked.split()[:50]))

    lines = diff.splitlines()
    limit = int(cfg["max_diff_lines"])
    print(f"\n### Diff ({len(lines)} lines{', truncated to ' + str(limit) if len(lines) > limit else ''})")
    print("```diff")
    print("\n".join(lines[:limit]))
    print("```")
    if len(lines) > limit:
        print("Diff truncated. Read the remaining files listed in the stat directly, one at a time.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 - must never abort the skill
        print(f"diff_context failed: {exc}")
    sys.exit(0)
