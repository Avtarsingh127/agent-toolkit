"""Plan summarizer (Terraform + Terragrunt dirs) and the Crossplane check script."""

from __future__ import annotations

import shutil
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import REPO, Sandbox

SUMMARIZE = [sys.executable, str(REPO / "skills" / "tf-plan-review" / "scripts" / "summarize_plan.py")]
XP_CHECK = [sys.executable, str(REPO / "skills" / "crossplane-dev" / "scripts" / "xp_check.py")]
REPO_MAP = [sys.executable, str(REPO / "skills" / "discuss" / "scripts" / "repo_map.py")]
FIXTURES = REPO / "tests" / "fixtures"


class PlanSummaryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.sb = Sandbox()

    def tearDown(self) -> None:
        self.sb.cleanup()

    def test_single_plan(self) -> None:
        out = self.sb.run([*SUMMARIZE, str(FIXTURES / "plan.json")]).stdout
        self.assertIn("create: 2 | update: 2 | replace: 1 | delete: 1", out)
        self.assertIn("forced by: network_config.0.network", out)
        self.assertIn('`source_ranges` = "0.0.0.0/0"', out)
        self.assertIn('`member` = "allUsers"', out)
        self.assertNotIn('"y"', out)  # sensitive value never printed
        self.assertIn("Drift detected", out)

    def test_terragrunt_dir(self) -> None:
        plans = self.sb.root / ".tgplan"
        for unit, src in (("dev/asia-south1/alloydb", "plan.json"), ("dev/asia-south1/vpc", "plan-noop.json")):
            (plans / unit).mkdir(parents=True)
            shutil.copy(FIXTURES / src, plans / unit / "tfplan.json")
        cache = plans / "dev" / ".terragrunt-cache" / "x"
        cache.mkdir(parents=True)
        shutil.copy(FIXTURES / "plan.json", cache / "tfplan.json")
        out = self.sb.run([*SUMMARIZE, str(plans)]).stdout
        self.assertIn("## Unit dev/asia-south1/alloydb", out)
        self.assertIn("## No changes in 1 unit(s)\ndev/asia-south1/vpc", out)
        self.assertNotIn(".terragrunt-cache", out)

    def test_missing_dir_hint(self) -> None:
        empty = self.sb.root / "empty"
        empty.mkdir()
        proc = self.sb.run([*SUMMARIZE, str(empty)])
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("--json-out-dir", proc.stderr)


class XpCheckTest(unittest.TestCase):
    def setUp(self) -> None:
        self.sb = Sandbox()
        api = self.sb.project / "apis" / "postgresdb"
        shutil.copytree(FIXTURES / "crossplane", api)
        (self.sb.project / "functions.yaml").write_text(
            "apiVersion: pkg.crossplane.io/v1\nkind: Function\nmetadata: {name: function-go-templating}\n"
            "spec: {package: xpkg.crossplane.io/crossplane-contrib/function-go-templating:v0.10.0}\n"
        )
        self.api = api
        # Fake crossplane CLI: render prints the XR + one composed MR without Orphan; validate succeeds.
        rendered = (FIXTURES / "crossplane-rendered.yaml").read_text()
        script = self.sb.bin / "crossplane"
        script.write_text(
            "#!/bin/sh\n"
            'case "$1 $2" in\n'
            f"  'composition render') cat <<'EOF'\n{rendered}EOF\n ;;\n"
            "  'resource validate') cat >/dev/null; echo '[!] could not find CRD for x (ignored)' ;;\n"
            "esac\n"
        )
        script.chmod(0o755)

    def tearDown(self) -> None:
        self.sb.cleanup()

    def test_render_validate_and_risks(self) -> None:
        proc = self.sb.run([*XP_CHECK, str(self.api)])
        out = proc.stdout
        self.assertIn("XRDs 1 | Compositions 1 | example XRs 1", out)
        self.assertIn("render ok: DatabaseInstance x1", out)
        self.assertIn("stateful resource can be deleted with the XR", out)
        self.assertIn("validate ok", out)
        self.assertIn("Result: PASS", out)

    def test_legacy_composition_flagged(self) -> None:
        comp = self.api / "composition.yaml"
        comp.write_text(comp.read_text().replace("mode: Pipeline", "mode: Resources"))
        out = self.sb.run([*XP_CHECK, str(self.api)]).stdout
        self.assertIn("mode: Resources (removed in Crossplane v2)", out)

    def test_missing_example(self) -> None:
        (self.api / "examples" / "small.yaml").unlink()
        proc = self.sb.run([*XP_CHECK, str(self.api)])
        self.assertEqual(proc.returncode, 1)
        self.assertIn("no example XR", proc.stdout)


class RepoMapTest(unittest.TestCase):
    def setUp(self) -> None:
        self.sb = Sandbox()
        p = self.sb.project
        files = {
            "README.md": "# demo\n",
            "root.hcl": "",
            "modules/net/main.tf": "",
            "modules/net/variables.tf": "",
            "live/dev/vpc/terragrunt.hcl": "",
            "apis/db/composition.yaml": "",
            ".terragrunt-cache/abc/main.tf": "",
            ".agents/notes/db-migration.md": "# Moving Cloud SQL to AlloyDB\n",
        }
        for rel, text in files.items():
            (p / rel).parent.mkdir(parents=True, exist_ok=True)
            (p / rel).write_text(text)
        git = ["git", "-C", str(p), "-c", "user.email=t@example.com", "-c", "user.name=t"]
        for args in (
            ["init", "-q", "-b", "main"],
            ["add", "-A"],
            ["commit", "-qm", "first commit"],
            ["remote", "add", "origin", "https://user:secret-token@github.com/acme/infra.git"],
        ):
            self.sb.run([*git, *args])

    def tearDown(self) -> None:
        self.sb.cleanup()

    def test_map(self) -> None:
        out = self.sb.run([*REPO_MAP, str(self.sb.project)]).stdout
        self.assertIn("modules/  (2 files: 2 .tf)", out)
        self.assertIn("- Terraform: 2 file(s)", out)  # .terragrunt-cache excluded
        self.assertIn("- Terragrunt: 2 file(s)", out)
        self.assertIn("- Crossplane: 1 file(s), mostly in apis/db", out)
        self.assertIn("- README.md", out)
        self.assertIn("first commit", out)
        self.assertIn("origin: https://github.com/acme/infra.git", out)
        self.assertNotIn("secret-token", out)
        self.assertIn(".agents/notes/db-migration.md: Moving Cloud SQL to AlloyDB", out)

    def test_project_override(self) -> None:
        (self.sb.project / ".agents" / "guardrails.json").write_text(
            '{"discuss": {"notes_dir": "docs/notes", "signals": {"Only HCL": ["*.hcl"]}}}'
        )
        out = self.sb.run([*REPO_MAP, str(self.sb.project)]).stdout
        self.assertIn("Notes folder: docs/notes/", out)
        self.assertIn("- Only HCL: 2 file(s)", out)  # dicts merge: added to the default signals
        self.assertIn("- Terraform:", out)
        self.assertNotIn(".terragrunt-cache", out)  # excluded dirs stay out of git activity too

    def test_not_a_dir(self) -> None:
        proc = self.sb.run([*REPO_MAP, str(self.sb.root / "missing")])
        self.assertEqual(proc.returncode, 0)
        self.assertIn("is not a directory", proc.stdout)


if __name__ == "__main__":
    unittest.main()
