"""The bash guard must make the same decision for Claude Code and Antigravity payloads."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import REPO, Sandbox, ag_command, claude_bash

GUARD = [sys.executable, str(REPO / "hooks" / "pre_bash_guard.py")]

DENY = [
    "terraform -chdir=stacks/dev destroy",
    "terraform apply -auto-approve tfplan",
    "terraform state rm module.db.google_sql_database_instance.this",
    "terragrunt destroy",
    "terragrunt run --all apply",
    "terragrunt run --all --filter 'dev/**' -- apply",
    "terragrunt run-all apply",
    "kubectl delete xrd postgresdbs.platform.example.org",
    "kubectl delete composition postgresdb-gcp",
    "kubectl delete providers.pkg.crossplane.io provider-gcp-sql",
    "kubectl -n team-a delete databaseinstances.sql.gcp.m.upbound.io main",
    "kubectl delete managed --all",
    "kubectl delete ns payments",
    "git push --force origin main",
    "gcloud projects delete acme-dev",
]
ASK_PROD = [
    "gcloud container clusters resize c1 --num-nodes 0 --project acme-prod",
    "CLOUDSDK_CORE_PROJECT=team-prd-01 gcloud compute instances delete vm1",
    "kubectl --context gke_acme-prod_asia-south1_c1 rollout restart deploy/api",
    "terragrunt apply --working-dir live/prod/asia-south1/alloydb",
    "crossplane xpkg push -c gke_acme-prod_x xpkg.example.io/acme/platform:v1",
]
ALLOW = [
    "terraform plan -out=tfplan",
    "terragrunt run --all --filter 'prod/**' --out-dir .tgplan --json-out-dir .tgplan plan",
    "gcloud container clusters list --project acme-prod",
    "kubectl get pods -A --context gke_acme-prod_asia-south1_c1",
    "kubectl --context gke_acme-dev_x delete pod api-1",
    "crossplane composition render xr.yaml composition.yaml functions.yaml",
    "ls -la",
]


class GuardTest(unittest.TestCase):
    def setUp(self) -> None:
        self.sb = Sandbox()
        # Disable live resolution so results don't depend on this machine's gcloud/kubectl.
        local = self.sb.root / "local.json"
        local.write_text(json.dumps({"prod": {"resolve_active_gcloud_project": False,
                                              "resolve_active_kube_context": False}}))  # fmt: skip
        self.env = {"AGENT_TOOLKIT_GUARDRAILS": str(local)}

    def tearDown(self) -> None:
        self.sb.cleanup()

    def decide(self, command: str, target: str) -> str:
        payload = claude_bash(command, str(self.sb.project)) if target == "claude" else ag_command(command)
        proc = self.sb.run([*GUARD, "--target", target], payload, **self.env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        if not proc.stdout.strip():
            return "none"
        out = json.loads(proc.stdout)
        if target == "claude":
            return out["hookSpecificOutput"]["permissionDecision"]
        return out["decision"]

    def test_hard_blocks(self) -> None:
        for target in ("claude", "antigravity"):
            for cmd in DENY:
                with self.subTest(target=target, cmd=cmd):
                    self.assertEqual(self.decide(cmd, target), "deny")

    def test_prod_mutations_ask(self) -> None:
        for target in ("claude", "antigravity"):
            for cmd in ASK_PROD:
                with self.subTest(target=target, cmd=cmd):
                    self.assertEqual(self.decide(cmd, target), "ask")

    def test_read_only_and_non_prod_pass(self) -> None:
        expected = {"claude": "none", "antigravity": "allow"}
        for target in ("claude", "antigravity"):
            for cmd in ALLOW:
                with self.subTest(target=target, cmd=cmd):
                    self.assertEqual(self.decide(cmd, target), expected[target])

    def test_active_context_resolution(self) -> None:
        self.sb.shim("gcloud", "acme-payments-prod")
        self.sb.shim("kubectl", "gke_acme-payments-prod_asia-south1_core")
        proc = self.sb.run([*GUARD], claude_bash("kubectl scale deploy/api --replicas 0"))
        self.assertIn('"ask"', proc.stdout)
        proc = self.sb.run([*GUARD], claude_bash("gcloud compute instances delete vm1 --zone z"))
        self.assertIn("active gcloud config", proc.stdout)

    def test_kubectl_container_flag_is_not_a_context(self) -> None:
        self.sb.shim("kubectl", "gke_acme-payments-prod_asia-south1_core")
        proc = self.sb.run([*GUARD], claude_bash("kubectl set image deploy/api -c api api=img:2"))
        self.assertIn('"ask"', proc.stdout)

    def test_repo_override_appends(self) -> None:
        agents = self.sb.project / ".agents"
        agents.mkdir()
        (agents / "guardrails.json").write_text(
            json.dumps({"hard_block_extra": [{"pattern": "make nuke", "reason": "repo rule"}]})
        )
        self.assertEqual(self.decide("make nuke", "claude"), "deny")
        self.assertEqual(self.decide("terraform destroy", "claude"), "deny")  # defaults still present

    def test_broken_config_fails_closed(self) -> None:
        broken = self.sb.root / "broken.json"
        broken.write_text("{nope")
        for target, payload in (("claude", claude_bash("ls")), ("antigravity", ag_command("ls"))):
            proc = self.sb.run([*GUARD, "--target", target], payload, AGENT_TOOLKIT_GUARDRAILS=str(broken))
            self.assertIn("deny", proc.stdout)

    def test_antigravity_other_tools_ignored(self) -> None:
        payload = json.dumps({"toolCall": {"name": "view_file", "args": {"AbsolutePath": "/x"}}})
        proc = self.sb.run([*GUARD, "--target", "antigravity"], payload, **self.env)
        self.assertEqual(json.loads(proc.stdout), {"decision": "allow"})

    def test_target_autodetect(self) -> None:
        proc = self.sb.run([*GUARD], ag_command("terraform destroy"), **self.env)
        self.assertEqual(json.loads(proc.stdout)["decision"], "deny")


class PostEditTest(unittest.TestCase):
    def setUp(self) -> None:
        self.sb = Sandbox()

    def tearDown(self) -> None:
        self.sb.cleanup()

    def test_python_fix_then_report(self) -> None:
        import shutil

        if not shutil.which("ruff"):
            self.skipTest("ruff not installed")
        self.sb.bin.joinpath("ruff").symlink_to(shutil.which("ruff"))
        f = self.sb.project / "bad.py"
        f.write_text("import os, sys\ndef f(x):\n    try:\n        return  x+1\n    except:\n        return nope\n")
        hook = [sys.executable, str(REPO / "hooks" / "post_edit_check.py")]
        payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": str(f)}, "cwd": str(self.sb.project)})
        out = json.loads(self.sb.run(hook, payload).stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("E722", out)
        self.assertIn("F821", out)
        self.assertNotIn("F401", out)
        self.assertIn("return x + 1", f.read_text())  # formatted in place
        ag = json.dumps({"toolCall": {"name": "write_to_file", "args": {"TargetFile": str(f)}}})
        self.assertEqual(json.loads(self.sb.run(hook, ag).stdout), {})  # Antigravity: format-only


class SessionContextTest(unittest.TestCase):
    def test_both_formats(self) -> None:
        sb = Sandbox()
        try:
            sb.shim("gcloud", "acme-prod")
            sb.shim("kubectl", "gke_acme-dev_x")
            hook = [sys.executable, str(REPO / "hooks" / "session_context.py")]
            text = sb.run([*hook, "--target", "claude"], "{}").stdout
            self.assertIn("acme-prod", text)
            self.assertIn("PROD", text)
            ag = json.loads(sb.run([*hook, "--target", "antigravity"], "{}").stdout)
            self.assertIn("acme-prod", ag["injectSteps"][0]["systemMessage"]["systemMessage"])
        finally:
            sb.cleanup()


if __name__ == "__main__":
    unittest.main()
