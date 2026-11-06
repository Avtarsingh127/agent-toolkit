#!/usr/bin/env python3
"""Merge a kit settings file into an existing Claude Code settings.json.

- Objects merge recursively; existing scalar values win (your choices are kept).
- permissions.allow/ask/deny: union, order preserved, no duplicates.
- hooks.<Event>: matcher groups appended unless an identical group already exists.
- Writes a timestamped backup next to the target before changing it.

Usage: merge_settings.py <kit-settings.json> <target-settings.json> [--replace TOKEN=VALUE ...]
"""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path
from typing import Any


def merge(existing: Any, incoming: Any, path: tuple[str, ...] = ()) -> Any:
    if isinstance(existing, dict) and isinstance(incoming, dict):
        out = dict(existing)
        for key, value in incoming.items():
            out[key] = merge(existing[key], value, path + (key,)) if key in existing else value
        return out
    if isinstance(existing, list) and isinstance(incoming, list):
        out = list(existing)
        for item in incoming:
            if item not in out:
                out.append(item)
        return out
    return existing  # scalar conflict: keep the user's value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("kit")
    parser.add_argument("target")
    parser.add_argument("--replace", action="append", default=[], help="TOKEN=VALUE substitution in the kit file")
    args = parser.parse_args()

    raw = Path(args.kit).read_text(encoding="utf-8")
    for pair in args.replace:
        token, value = pair.split("=", 1)
        raw = raw.replace(token, value)
    incoming = json.loads(raw)

    target = Path(args.target)
    if target.exists():
        existing = json.loads(target.read_text(encoding="utf-8") or "{}")
        backup = target.with_name(f"{target.name}.bak-{time.strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(target, backup)
        print(f"  backup: {backup}")
    else:
        existing = {}
        target.parent.mkdir(parents=True, exist_ok=True)

    merged = merge(existing, incoming)
    target.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
    print(f"  merged: {target}")


if __name__ == "__main__":
    main()
