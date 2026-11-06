#!/usr/bin/env python3
"""SessionStart hook: tells the agent which GCP project and kube context are active.

At most two short lines (~40 tokens). Disable with session_context.enabled=false.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import _guardrails_config as gc  # noqa: E402
import agent_io  # noqa: E402


def quiet(argv: list[str], timeout: float) -> str:
    if not shutil.which(argv[0]):
        return "n/a"
    try:
        out = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)
        return out.stdout.strip() or "unset"
    except (subprocess.TimeoutExpired, OSError):
        return "unknown (timed out)"


def main() -> None:
    event = agent_io.read_event()
    try:
        cfg = gc.load(event.cwd)
    except SystemExit:
        sys.exit(0)
    if not gc.get(cfg, "session_context.enabled", True):
        sys.exit(0)

    timeout = float(gc.get(cfg, "prod.resolve_timeout_seconds", 3))
    project = quiet(["gcloud", "config", "get-value", "project"], timeout)
    context = quiet(["kubectl", "config", "current-context"], timeout)
    patterns = gc.get(cfg, "prod.gcp_project_patterns", []) + gc.get(cfg, "prod.kube_context_patterns", [])
    is_prod = any(re.search(p, v, re.IGNORECASE) for p in patterns for v in (project, context))

    text = f"Active gcloud project: {project}. Active kube context: {context}."
    if is_prod:
        text += (
            "\nThe active project/context matches a PROD pattern: "
            "treat every mutating command as needing explicit confirmation."
        )
    agent_io.session_context(event.target, text)


if __name__ == "__main__":
    main()
