#!/usr/bin/env python3
"""PreToolUse guard for shell commands (Claude Code `Bash`, Antigravity `run_command`).

1. Hard-blocks destructive commands (terraform/terragrunt destroy, auto-approve,
   state surgery, deleting Crossplane objects, force-push, ...).
2. Asks before mutating anything that targets a production GCP project, kube
   context, Terraform/Terragrunt directory or Crossplane control plane.

Every pattern lives in config/guardrails.json (+ your local and per-repo
overrides). Nothing environment-specific is hard-coded here.

Context cost: zero unless it denies/asks, then only the short reason.
Broken config: fails closed (every command blocked until fixed).
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

FLAG_VALUE = r"(?:=|\s+)['\"]?([^\s'\";&|)]+)"


def first_flag(command: str, *flags: str) -> str | None:
    for flag in flags:
        m = re.search(rf"(?:^|\s){re.escape(flag)}{FLAG_VALUE}", command)
        if m:
            return m.group(1)
    return None


def env_prefix(command: str, var: str) -> str | None:
    m = re.search(rf"(?:^|\s){var}=['\"]?([^\s'\"]+)", command)
    return m.group(1) if m else None


def run_quiet(argv: list[str], timeout: float) -> str | None:
    if not shutil.which(argv[0]):
        return None
    try:
        out = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)
    except (subprocess.TimeoutExpired, OSError):
        return None
    return out.stdout.strip() or None


def matches_any(value: str | None, patterns: list[str]) -> bool:
    return bool(value) and any(re.search(p, value, re.IGNORECASE) for p in patterns)


def main() -> None:
    event = agent_io.read_event()
    if event.target == agent_io.ANTIGRAVITY and event.tool and event.tool != "run_command":
        agent_io.pre_tool_no_opinion(event)
    command = event.command
    if not command.strip():
        agent_io.pre_tool_no_opinion(event)

    try:
        cfg = gc.load(event.cwd)
    except SystemExit as exc:
        agent_io.pre_tool_decision(event, "deny", f"{exc}. Fix the guardrails config; shell commands are blocked.")

    default_ag = gc.get(cfg, "antigravity.pre_tool_default_decision", "allow")

    # 1. Hard blocks: never run, whatever the environment.
    for rule in gc.get(cfg, "hard_block", []):
        if re.search(rule["pattern"], command, re.IGNORECASE):
            agent_io.pre_tool_decision(event, "deny", f"Guardrail: {rule.get('reason', 'blocked by guardrails')}")

    # 2. Prod-targeted mutations: ask the human.
    project_patterns = gc.get(cfg, "prod.gcp_project_patterns", [])
    context_patterns = gc.get(cfg, "prod.kube_context_patterns", []) + project_patterns
    path_patterns = gc.get(cfg, "prod.path_patterns", []) + project_patterns
    timeout = float(gc.get(cfg, "prod.resolve_timeout_seconds", 3))
    mutations = {k: v for k, v in gc.get(cfg, "prod_mutations", {}).items() if not k.startswith("_")}

    def matched(*tools: str) -> bool:
        return any(mutations.get(t) and re.search(mutations[t], command, re.IGNORECASE) for t in tools)

    if matched("gcloud", "bq"):
        project = first_flag(command, "--project", "--project_id") or env_prefix(command, "CLOUDSDK_CORE_PROJECT")
        source = "flag or env prefix"
        if not project and gc.get(cfg, "prod.resolve_active_gcloud_project", True):
            project = run_quiet(["gcloud", "config", "get-value", "project"], timeout)
            source = "active gcloud config"
        if matches_any(project, project_patterns):
            agent_io.pre_tool_decision(
                event, "ask", f"Mutating command targets prod project '{project}' ({source}). Confirm intentionally."
            )

    if matched("kubectl", "helm", "crossplane"):
        context = first_flag(command, "--context", "--kube-context")
        if not context and matched("crossplane"):
            context = first_flag(command, "-c")  # crossplane CLI short flag; for kubectl -c is the container
        source = "flag"
        if not context and gc.get(cfg, "prod.resolve_active_kube_context", True):
            context = run_quiet(["kubectl", "config", "current-context"], timeout)
            source = "current kube context"
        if matches_any(context, context_patterns):
            agent_io.pre_tool_decision(
                event,
                "ask",
                f"Mutating command targets prod context '{context}' ({source}). "
                "Prod changes should normally go through Git/ArgoCD.",
            )

    if matched("terraform", "terragrunt", "argocd"):
        if matches_any(command, path_patterns) or matches_any(event.cwd, path_patterns):
            agent_io.pre_tool_decision(
                event,
                "ask",
                "terraform/terragrunt/argocd change appears to target prod (command or directory). Confirm.",
            )

    agent_io.pre_tool_no_opinion(event, default_ag)


if __name__ == "__main__":
    main()
