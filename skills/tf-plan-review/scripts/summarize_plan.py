#!/usr/bin/env python3
"""Condense a Terraform plan into a short, review-ready summary.

Why: a raw `terraform plan` for a GKE/AlloyDB stack can be tens of thousands of
tokens. This script reads the machine-readable plan and prints only what a
reviewer needs: counts, every destructive change, risky changes, and changed
attribute *names* (never sensitive values). Typical output: 300-1,500 tokens.

Usage:
  summarize_plan.py <planfile | plan.json | directory> [...] [--chdir DIR]
  - planfile: binary file from `terraform plan -out=...` (needs `terraform` and an
    initialised root module; DIR defaults to the plan file's directory)
  - plan.json: output of `terraform show -json <planfile>`
  - directory: every plan JSON below it (plan_summary.plan_json_name, default
    tfplan.json), e.g. the --json-out-dir of
    `terragrunt run --all --out-dir .tgplan --json-out-dir .tgplan plan`.
    One summary per unit, quiet units collapsed into one line.

Limits and risk rules come from guardrails.json -> plan_summary.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULTS: dict[str, Any] = {
    "max_listed_per_action": 40,
    "plan_json_name": "tfplan.json",
    "risky_resource_types": [],
    "risky_attribute_values": {},
}


def load_config(cwd: str) -> dict[str, Any]:
    for parent in Path(__file__).resolve().parents:
        lib = parent / "hooks" / "lib"
        if (lib / "_guardrails_config.py").exists():
            sys.path.insert(0, str(lib))
            try:
                import _guardrails_config as gc  # type: ignore

                return {**DEFAULTS, **(gc.get(gc.load(cwd), "plan_summary", {}) or {})}
            except SystemExit as exc:
                print(f"(guardrails config ignored: {exc})")
            break
    return dict(DEFAULTS)


def load_plan(path: Path, chdir: Path | None) -> dict[str, Any]:
    if path.suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    if not shutil.which("terraform"):
        raise SystemExit("terraform not on PATH; pass a JSON plan instead (terraform show -json plan > plan.json)")
    workdir = chdir or path.resolve().parent
    proc = subprocess.run(
        ["terraform", f"-chdir={workdir}", "show", "-json", str(path.resolve())],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise SystemExit(f"terraform show failed:\n{proc.stderr.strip()[:2000]}")
    return json.loads(proc.stdout)


def action_of(actions: list[str]) -> str:
    if actions == ["no-op"] or actions == ["read"]:
        return "no-op"
    if "delete" in actions and "create" in actions:
        return "replace"
    return actions[0] if actions else "unknown"


def changed_keys(change: dict[str, Any]) -> list[str]:
    before = change.get("before") or {}
    after = change.get("after") or {}
    unknown = change.get("after_unknown") or {}
    keys = set(before) | set(after) | set(unknown)
    out = []
    for key in sorted(keys):
        if unknown.get(key) is True:
            out.append(f"{key}(known after apply)")
        elif before.get(key) != after.get(key):
            out.append(key)
    return out


def walk(node: Any, sensitive: Any, prefix: str = ""):
    """Yield (path, key, value) for non-sensitive leaves of a nested structure."""
    if sensitive is True:
        return
    if isinstance(node, dict):
        for key, value in node.items():
            sub_sensitive = sensitive.get(key) if isinstance(sensitive, dict) else None
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, (dict, list)):
                yield from walk(value, sub_sensitive, path)
            else:
                yield path, key, value
            if isinstance(value, list) and sub_sensitive is not True:
                for item in value:
                    if not isinstance(item, (dict, list)):
                        yield path, key, item
    elif isinstance(node, list):
        for i, item in enumerate(node):
            sub_sensitive = sensitive[i] if isinstance(sensitive, list) and i < len(sensitive) else None
            yield from walk(item, sub_sensitive, f"{prefix}[{i}]")


def risk_notes(rc: dict[str, Any], cfg: dict[str, Any], action: str) -> list[str]:
    notes: list[str] = []
    if action in ("no-op", "delete"):
        return notes
    rtype = rc.get("type", "")
    if rtype in cfg["risky_resource_types"]:
        notes.append(f"sensitive resource type `{rtype}` ({action})")
    change = rc.get("change", {})
    after = change.get("after") or {}
    sensitive = change.get("after_sensitive") or {}
    bad_values: dict[str, list[Any]] = cfg["risky_attribute_values"]
    for path, key, value in walk(after, sensitive):
        if key in bad_values and value in bad_values[key]:
            notes.append(f"`{path}` = {json.dumps(value)}")
    return sorted(set(notes))


def summarize(plan: dict[str, Any], cfg: dict[str, Any], title: str) -> tuple[str, bool]:
    """Return (markdown, has_changes)."""
    limit = int(cfg["max_listed_per_action"])
    buckets: dict[str, list[str]] = {k: [] for k in ("create", "update", "replace", "delete", "no-op")}
    risky: list[str] = []
    for rc in plan.get("resource_changes", []):
        if rc.get("mode") == "data":
            continue
        change = rc.get("change", {})
        action = action_of(change.get("actions", []))
        addr = rc.get("address", "?")
        if action == "update":
            keys = changed_keys(change)
            line = f"{addr}: {', '.join(keys[:12])}{' ...' if len(keys) > 12 else ''}"
        elif action == "replace":
            forcing = [".".join(map(str, p)) for p in rc.get("replace_paths", [])] if rc.get("replace_paths") else []
            line = f"{addr}" + (f" (forced by: {', '.join(forcing[:6])})" if forcing else "")
        else:
            line = addr
        buckets.setdefault(action, []).append(line)
        for note in risk_notes(rc, cfg, action):
            risky.append(f"{addr}: {note}")

    drift = [
        d.get("address", "?")
        for d in plan.get("resource_drift", [])
        if action_of(d.get("change", {}).get("actions", [])) != "no-op"
    ]
    outputs = [k for k, v in (plan.get("output_changes") or {}).items() if action_of(v.get("actions", [])) != "no-op"]
    counts = {k: len(buckets.get(k, [])) for k in ("create", "update", "replace", "delete")}
    has_changes = any(counts.values()) or bool(drift) or bool(outputs) or bool(plan.get("errored"))

    out = [f"## {title}", " | ".join(f"{k}: {v}" for k, v in counts.items())]
    if plan.get("errored"):
        out.append("\n**Plan reports errored=true; treat as incomplete.**")
    for heading, key in (("Deletes (all listed)", "delete"), ("Replacements (all listed)", "replace")):
        if buckets[key]:
            out += [f"\n### {heading}"] + [f"- {x}" for x in buckets[key]]
    if risky:
        out += ["\n### Risk flags"] + [f"- {x}" for x in risky[: limit * 2]]
    for heading, key in (("Updates", "update"), ("Creates", "create")):
        items = buckets[key]
        if items:
            out += [f"\n### {heading} (showing {min(len(items), limit)} of {len(items)})"]
            out += [f"- {x}" for x in items[:limit]]
    if drift:
        out += [f"\n### Drift detected outside Terraform ({len(drift)})"] + [f"- {x}" for x in drift[:limit]]
    if outputs:
        out.append(f"\n### Output changes: {', '.join(outputs[:limit])}")
    return "\n".join(out), has_changes


def collect(paths: list[str], cfg: dict[str, Any], chdir: Path | None) -> list[tuple[str, dict[str, Any]]]:
    plans: list[tuple[str, dict[str, Any]]] = []
    for raw in paths:
        path = Path(raw)
        if not path.exists():
            raise SystemExit(f"plan not found: {path}. Create one with: terraform plan -out=tfplan")
        if path.is_dir():
            found = sorted(p for p in path.rglob(cfg["plan_json_name"]) if ".terragrunt-cache" not in p.parts)
            if not found:
                raise SystemExit(
                    f"no {cfg['plan_json_name']} under {path}. For Terragrunt run: "
                    f"terragrunt run --all --out-dir {path} --json-out-dir {path} plan"
                )
            for p in found:
                unit = p.parent.relative_to(path).as_posix() or "."
                plans.append((f"Unit {unit}", json.loads(p.read_text(encoding="utf-8"))))
        else:
            plans.append((f"Plan {path.name}", load_plan(path, chdir)))
    return plans


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("plans", nargs="+")
    parser.add_argument("--chdir")
    args = parser.parse_args()

    cfg = load_config(str(Path.cwd()))
    plans = collect(args.plans, cfg, Path(args.chdir) if args.chdir else None)

    quiet: list[str] = []
    for title, plan in plans:
        text, has_changes = summarize(plan, cfg, "Terraform plan summary" if len(plans) == 1 else title)
        if has_changes or len(plans) == 1:
            print(text + "\n")
        else:
            quiet.append(title.removeprefix("Unit ").removeprefix("Plan "))
    if quiet:
        print(f"## No changes in {len(quiet)} unit(s)\n" + ", ".join(quiet))


if __name__ == "__main__":
    main()
