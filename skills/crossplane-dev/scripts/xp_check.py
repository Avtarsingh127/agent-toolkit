#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6"]
# ///
"""Render and schema-validate Crossplane compositions, print a short summary.

Usage:
  xp_check.py <dir> [--functions FILE] [--observed PATH] [--required PATH] [--extensions PATH ...]

<dir> is scanned (recursively) for YAML documents by kind:
  CompositeResourceDefinition -> extension + defines the XR kind
  Composition                 -> rendered against every example XR of its compositeTypeRef
  Function                    -> passed to render (or --functions)
  Provider / Configuration    -> extensions for schema validation
  <XR kind from the XRD>      -> example XRs (usually examples/*.yaml)
Functions/providers outside <dir> are found by walking up to the git root.

Static checks (no cluster needed): v1-style Compositions (mode: Resources), legacy
XRDs, and stateful managed resources without deletionPolicy: Orphan or a
managementPolicies list that excludes Delete.

Commands and risky kinds come from guardrails.json -> crossplane, so CLI changes
between Crossplane versions are a config edit. `crossplane ... render` runs
functions in containers: Docker (or a compatible runtime) must be running.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

DEFAULTS: dict[str, Any] = {
    "render": [
        "crossplane",
        "composition",
        "render",
        "{xr}",
        "{composition}",
        "{functions}",
        "--include-function-results",
    ],
    "render_extra_flags": {"observed": "--observed-resources={path}", "required": "--required-resources={path}"},
    "validate": ["crossplane", "resource", "validate", "{extensions}", "-", "--skip-success-results"],
    "risky_kinds_without_orphan": ["DatabaseInstance", "Cluster", "Instance", "Bucket", "CryptoKey", "KeyRing"],
}
MAX_LINES = 30


def load_config() -> dict[str, Any]:
    for parent in Path(__file__).resolve().parents:
        lib = parent / "hooks" / "lib"
        if (lib / "_guardrails_config.py").exists():
            sys.path.insert(0, str(lib))
            try:
                import _guardrails_config as gc  # type: ignore

                return {**DEFAULTS, **(gc.get(gc.load(), "crossplane", {}) or {})}
            except SystemExit as exc:
                print(f"(guardrails config ignored: {exc})")
            break
    return dict(DEFAULTS)


def git_root(start: Path) -> Path:
    proc = subprocess.run(["git", "-C", str(start), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return Path(proc.stdout.strip()) if proc.returncode == 0 else start


def scan(root: Path) -> list[tuple[Path, dict[str, Any]]]:
    docs: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted([*root.rglob("*.yaml"), *root.rglob("*.yml")]):
        if any(part.startswith(".") or part in ("node_modules", "vendor") for part in path.relative_to(root).parts):
            continue
        try:
            for doc in yaml.safe_load_all(path.read_text(encoding="utf-8")):
                if isinstance(doc, dict) and "kind" in doc:
                    docs.append((path, doc))
        except yaml.YAMLError:
            continue  # templates (go-templating, helm) are not plain YAML
    return docs


def tail(text: str, n: int = MAX_LINES) -> str:
    lines = [ln for ln in text.strip().splitlines() if ln.strip()]
    return "\n".join(lines[-n:])


def fill(argv: list[str], **values: str) -> list[str]:
    out = []
    for arg in argv:
        if arg in ("{functions}",) and not values.get("functions"):
            continue
        for key, value in values.items():
            arg = arg.replace("{" + key + "}", value)
        out.append(arg)
    return out


def static_checks(docs: list[tuple[Path, dict[str, Any]]], risky: list[str]) -> list[str]:
    notes = []
    for path, doc in docs:
        kind, api = doc.get("kind"), doc.get("apiVersion", "")
        if kind == "Composition" and (doc.get("spec") or {}).get("mode", "Pipeline") == "Resources":
            notes.append(f"{path}: Composition uses mode: Resources (removed in Crossplane v2); convert to Pipeline.")
        if kind == "CompositeResourceDefinition":
            scope = (doc.get("spec") or {}).get("scope")
            if api.endswith("/v1") or scope == "LegacyCluster":
                notes.append(
                    f"{path}: legacy XRD ({api}, scope {scope or 'LegacyCluster'}). New APIs should be v2 Namespaced."
                )
    return notes


def mr_risks(rendered: list[dict[str, Any]], risky: list[str]) -> list[str]:
    notes = []
    for doc in rendered:
        kind, api = doc.get("kind", ""), doc.get("apiVersion", "")
        spec = doc.get("spec") or {}
        is_mr = (".upbound.io/" in api or ".crossplane.io/" in api) and not api.startswith(
            ("apiextensions.", "pkg.", "protection.")
        )
        if kind in risky and is_mr:
            policies = spec.get("managementPolicies")
            orphan = spec.get("deletionPolicy") == "Orphan"
            no_delete = isinstance(policies, list) and "*" not in policies and "Delete" not in policies
            if not (orphan or no_delete):
                name = (doc.get("metadata") or {}).get("annotations", {}).get("crossplane.io/composition-resource-name")
                notes.append(f"{kind} ({name or 'unnamed'}): stateful resource can be deleted with the XR "
                             "(set deletionPolicy: Orphan or managementPolicies without Delete).")  # fmt: skip
    return notes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("dir", type=Path)
    parser.add_argument("--functions", type=Path)
    parser.add_argument("--observed", type=Path)
    parser.add_argument("--required", type=Path)
    parser.add_argument("--extensions", type=Path, action="append", default=[])
    args = parser.parse_args()
    cfg = load_config()

    if not shutil.which("crossplane"):
        sys.exit("crossplane CLI not on PATH. Install it (see the toolkit's Mac setup) and retry.")
    root = args.dir.resolve()
    docs = scan(root)
    repo_docs = scan(git_root(root)) if git_root(root) != root else docs

    xrds = [(p, d) for p, d in docs if d["kind"] == "CompositeResourceDefinition"]
    comps = [(p, d) for p, d in docs if d["kind"] == "Composition"]
    functions_files = sorted({p for p, d in repo_docs if d["kind"] == "Function"})
    provider_files = sorted({p for p, d in repo_docs if d["kind"] in ("Provider", "Configuration")})
    xr_kinds = {(d["spec"]["group"], d["spec"]["names"]["kind"]) for _, d in xrds if "spec" in d}
    examples = [(p, d) for p, d in docs if (d.get("apiVersion", "").split("/")[0], d["kind"]) in xr_kinds]

    print(f"## Crossplane check: {root}")
    print(f"XRDs {len(xrds)} | Compositions {len(comps)} | example XRs {len(examples)} | "
          f"function files {len(functions_files)} | provider/config files {len(provider_files)}")  # fmt: skip

    notes = static_checks(docs, cfg["risky_kinds_without_orphan"])
    if notes:
        print("\n### Static findings")
        print("\n".join(f"- {n}" for n in notes))

    functions = args.functions or (functions_files[0] if len(functions_files) == 1 else None)
    if not functions and len(functions_files) > 1:
        print(f"\nSeveral Function files found; pass --functions. Candidates: {', '.join(map(str, functions_files))}")
    extensions = [str(p) for p, _ in xrds] + [str(p) for p in provider_files] + [str(p) for p in args.extensions]

    failures = 0
    for comp_path, comp in comps:
        ref = (comp.get("spec") or {}).get("compositeTypeRef") or {}
        targets = [(p, d) for p, d in examples
                   if d.get("apiVersion") == ref.get("apiVersion") and d["kind"] == ref.get("kind")]  # fmt: skip
        if not targets:
            print(f"\n### {comp_path.name}: no example XR for {ref.get('kind')}; add one under examples/")
            failures += 1
            continue
        for xr_path, _ in targets:
            print(f"\n### {comp_path.relative_to(root)} x {xr_path.relative_to(root)}")
            argv = fill(cfg["render"], xr=str(xr_path), composition=str(comp_path),
                        functions=str(functions) if functions else "")  # fmt: skip
            for key, value in (("observed", args.observed), ("required", args.required)):
                if value:
                    argv.append(cfg["render_extra_flags"][key].replace("{path}", str(value)))
            proc = subprocess.run(argv, capture_output=True, text=True)
            if proc.returncode != 0:
                failures += 1
                print("render FAILED:\n```\n" + tail(proc.stderr or proc.stdout) + "\n```")
                continue
            rendered = [d for d in yaml.safe_load_all(proc.stdout) if isinstance(d, dict)]
            results = [d for d in rendered if d.get("kind") == "Result"]
            composed = [d for d in rendered if d.get("kind") != "Result"][1:]  # first doc is the XR
            print("render ok: " + ", ".join(f"{k} x{n}" for k, n in Counter(d.get("kind") for d in composed).items()))
            for r in results:
                sev = r.get("severity", "")
                if sev and sev != "SEVERITY_NORMAL":
                    print(f"- function result {sev}: {r.get('message', '')}")
            for note in mr_risks(composed, cfg["risky_kinds_without_orphan"]):
                print(f"- risk: {note}")
            if extensions:
                vargv = fill(cfg["validate"], extensions=",".join(extensions))
                vproc = subprocess.run(vargv, input=proc.stdout, capture_output=True, text=True)
                out = tail(vproc.stdout + vproc.stderr)
                if vproc.returncode != 0:
                    failures += 1
                    print("validate FAILED:\n```\n" + out + "\n```")
                else:
                    print("validate ok" + (f":\n```\n{out}\n```" if out else ""))
            else:
                print("validate skipped: no XRD or Provider manifests found to validate against")
    print(f"\nResult: {'FAIL' if failures else 'PASS'} ({failures} problem(s))")
    print(json.dumps({"failures": failures}))
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
