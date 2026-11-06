"""Translate hook payloads and decisions between Claude Code and Antigravity.

The hook logic is written once; this module reads either agent's stdin payload
into a neutral Event and writes the decision in the format that agent expects.

Claude Code   https://code.claude.com/docs/en/hooks
  stdin:  {"tool_name": "Bash", "tool_input": {"command": ..., "file_path": ...}, "cwd": ...}
  deny:   {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", ...}}
Antigravity   https://antigravity.google/docs/hooks
  stdin:  {"toolCall": {"name": "run_command", "args": {"CommandLine": ..., "Cwd": ...}}, "workspacePaths": [...]}
  deny:   {"decision": "deny", "reason": ...}
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from typing import Any

CLAUDE = "claude"
ANTIGRAVITY = "antigravity"

# Antigravity tool names that write files, and the arg holding the path.
AG_EDIT_TOOLS = {"write_to_file", "replace_file_content", "multi_replace_file_content"}


@dataclass
class Event:
    target: str
    tool: str = ""
    command: str = ""
    file_path: str = ""
    cwd: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


def detect_target(payload: dict[str, Any], forced: str | None) -> str:
    if forced in (CLAUDE, ANTIGRAVITY):
        return forced
    return ANTIGRAVITY if "toolCall" in payload or "conversationId" in payload else CLAUDE


def read_event(argv: list[str] | None = None) -> Event:
    argv = argv if argv is not None else sys.argv[1:]
    forced = None
    if "--target" in argv:
        idx = argv.index("--target")
        forced = argv[idx + 1] if idx + 1 < len(argv) else None
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            payload = {}
    except (json.JSONDecodeError, ValueError):
        payload = {}

    target = detect_target(payload, forced)
    if target == ANTIGRAVITY:
        call = payload.get("toolCall") or {}
        args = call.get("args") or {}
        workspaces = payload.get("workspacePaths") or []
        return Event(
            target=target,
            tool=call.get("name", ""),
            command=args.get("CommandLine") or "",
            file_path=args.get("TargetFile") or args.get("AbsolutePath") or "",
            cwd=args.get("Cwd") or (workspaces[0] if workspaces else None),
            raw=payload,
        )
    tool_input = payload.get("tool_input") or {}
    return Event(
        target=target,
        tool=payload.get("tool_name", ""),
        command=tool_input.get("command") or "",
        file_path=tool_input.get("file_path") or "",
        cwd=payload.get("cwd"),
        raw=payload,
    )


def emit(obj: dict[str, Any]) -> None:
    print(json.dumps(obj))
    sys.exit(0)


def pre_tool_decision(event: Event, decision: str, reason: str) -> None:
    """decision: 'deny' or 'ask'. Exits."""
    if event.target == ANTIGRAVITY:
        emit({"decision": decision, "reason": reason})
    emit(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": decision,
                "permissionDecisionReason": reason,
            }
        }
    )


def pre_tool_no_opinion(event: Event, antigravity_default: str = "allow") -> None:
    """Let the agent's normal permission flow decide. Exits."""
    if event.target == ANTIGRAVITY:
        emit({"decision": antigravity_default})
    sys.exit(0)


def post_tool_feedback(event: Event, text: str | None) -> None:
    """Return lint failures to the model where the agent supports it. Exits."""
    if event.target == ANTIGRAVITY:
        # Antigravity documents only {} for PostToolUse output: format-only there.
        emit({})
    if text:
        emit({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": text}})
    sys.exit(0)


def session_context(target: str, text: str) -> None:
    """Add a short note at session start. Exits."""
    if target == ANTIGRAVITY:
        emit({"injectSteps": [{"systemMessage": {"systemMessage": text}}]})
    print(text)
    sys.exit(0)
