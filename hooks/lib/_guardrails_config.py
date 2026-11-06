"""Shared config loader for the toolkit's hooks and skill scripts (stdlib only).

Resolution order (later wins; dicts deep-merge, lists replace):
  1. <toolkit repo>/config/guardrails.json      repo defaults, versioned
  2. $AGENT_TOOLKIT_GUARDRAILS or
     ~/.config/agent-toolkit/guardrails.json    your private overrides (real prod naming)
  3. <project>/.agents/guardrails.json and
     <project>/.claude/guardrails.json          per-repo overrides

A key ending in "_extra" holding a list is appended to the list of the same
name, so overrides can add patterns without restating the defaults:
  {"hard_block_extra": [{"pattern": "...", "reason": "..."}]}
Keys starting with "_" are comments and are ignored.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

TOOLKIT_ROOT = Path(os.environ.get("AGENT_TOOLKIT_HOME") or Path(__file__).resolve().parents[2])


def _read(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        # A broken config must be visible, not silently ignored.
        raise SystemExit(f"guardrails: cannot parse {path}: {exc}") from exc


def _merge(base: dict[str, Any], over: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in over.items():
        if key.startswith("_"):
            continue
        if key.endswith("_extra") and isinstance(value, list):
            target = key[: -len("_extra")]
            out[target] = list(out.get(target, [])) + value
        elif isinstance(value, dict):
            base_value = out.get(key)
            out[key] = _merge(base_value if isinstance(base_value, dict) else {}, value)
        else:
            out[key] = value
    return out


def sources(project_dir: str | None = None) -> list[Path]:
    local = os.environ.get("AGENT_TOOLKIT_GUARDRAILS") or "~/.config/agent-toolkit/guardrails.json"
    project = Path(project_dir or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    return [
        TOOLKIT_ROOT / "config" / "guardrails.json",
        Path(os.path.expanduser(local)),
        project / ".agents" / "guardrails.json",
        project / ".claude" / "guardrails.json",
    ]


def load(project_dir: str | None = None) -> dict[str, Any]:
    cfg: dict[str, Any] = {}
    for src in sources(project_dir):
        cfg = _merge(cfg, _read(src))
    _extend_path(cfg)
    return cfg


def _extend_path(cfg: dict[str, Any]) -> None:
    """GUI apps (e.g. the Antigravity App) often start hooks without Homebrew on PATH.
    Without gcloud/kubectl on PATH the guard can't see the active project/context."""
    current = os.environ.get("PATH", "").split(os.pathsep)
    extra = [os.path.expanduser(p) for p in get(cfg, "hook_env.extra_path", []) or []]
    missing = [p for p in extra if p not in current and os.path.isdir(p)]
    if missing:
        os.environ["PATH"] = os.pathsep.join(current + missing)


def get(cfg: dict[str, Any], dotted: str, default: Any = None) -> Any:
    node: Any = cfg
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node
