"""Shared test helpers: run hooks/scripts in an isolated HOME with shimmed CLIs."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


class Sandbox:
    """Temporary HOME + PATH shims so tests never touch real config or cloud CLIs."""

    def __init__(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        self.bin = self.root / "bin"
        self.project = self.root / "project"
        for d in (self.home, self.bin, self.project):
            d.mkdir()

    def shim(self, name: str, stdout: str = "", code: int = 0) -> None:
        path = self.bin / name
        path.write_text(f"#!/bin/sh\nprintf '%s\\n' {json.dumps(stdout)}\nexit {code}\n")
        path.chmod(0o755)

    def env(self, **extra: str) -> dict[str, str]:
        env = {
            "HOME": str(self.home),
            "PATH": f"{self.bin}:/usr/bin:/bin:/usr/local/bin:{os.path.dirname(sys.executable)}",
            "CLAUDE_PROJECT_DIR": str(self.project),
            "AGENT_TOOLKIT_BUILD_DIR": str(self.root / "build"),
        }
        env.update(extra)
        return env

    def run(self, argv: list[str], stdin: str = "", **env: str) -> subprocess.CompletedProcess:
        return subprocess.run(argv, input=stdin, capture_output=True, text=True, env=self.env(**env), check=False)

    def cleanup(self) -> None:
        self.tmp.cleanup()


def claude_bash(command: str, cwd: str | None = None) -> str:
    return json.dumps({"tool_name": "Bash", "tool_input": {"command": command}, "cwd": cwd})


def ag_command(command: str, cwd: str | None = None) -> str:
    return json.dumps(
        {
            "conversationId": "c1",
            "workspacePaths": [cwd or "/tmp/ws"],
            "toolCall": {"name": "run_command", "args": {"CommandLine": command, "Cwd": cwd or "/tmp/ws"}},
        }
    )
