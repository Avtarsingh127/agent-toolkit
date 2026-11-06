"""Build + install into a throwaway HOME for both agents; idempotency and uninstall."""

from __future__ import annotations

import json
import os
import shutil
import sys
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import REPO, Sandbox

TOOLKIT = [sys.executable, str(REPO / "tools" / "toolkit.py")]


def frontmatter(path: Path) -> dict:
    text = path.read_text()
    assert text.startswith("---\n"), path
    return yaml.safe_load(text.split("---\n")[1])


class ToolkitTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sb = Sandbox()
        claude = cls.sb.home / ".claude"
        claude.mkdir()
        # Pre-existing user state that must survive install/uninstall.
        (claude / "settings.json").write_text(json.dumps({
            "model": "opus",
            "permissions": {"allow": ["Bash(make *)"]},
            "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "my-own-hook"}]},
                                     {"matcher": "Bash", "hooks": [{"type": "command",
                                      "command": "python3 \"/old/.claude/hooks/pre_bash_guard.py\""}]}]},
        }))  # fmt: skip
        (claude / "skills").mkdir()
        (claude / "skills" / "my-skill").mkdir()
        (claude / "skills" / "my-skill" / "SKILL.md").write_text("---\nname: my-skill\ndescription: x\n---\n")
        (claude / "skills" / "tf-plan-review").mkdir()  # a copied v1 kit skill: conflict
        gem = cls.sb.home / ".gemini" / "config"
        gem.mkdir(parents=True)
        (gem / "hooks.json").write_text(json.dumps({"mine": {"Stop": []}}))
        cls.first = cls.sb.run([*TOOLKIT, "install"])
        cls.forced = cls.sb.run([*TOOLKIT, "install", "--force"])
        cls.second = cls.sb.run([*TOOLKIT, "install"])

    @classmethod
    def tearDownClass(cls) -> None:
        cls.sb.cleanup()

    def test_conflict_reported_then_forced(self) -> None:
        self.assertEqual(self.first.returncode, 1, self.first.stdout + self.first.stderr)
        self.assertIn("conflict", self.first.stdout)
        self.assertEqual(self.forced.returncode, 0, self.forced.stdout + self.forced.stderr)
        backups = list((self.sb.home / ".agent-toolkit-backups").rglob("tf-plan-review"))
        self.assertTrue(backups, "old skill should be backed up")

    def test_idempotent(self) -> None:
        self.assertEqual(self.second.returncode, 0, self.second.stdout + self.second.stderr)
        self.assertNotIn("linked", self.second.stdout)
        self.assertNotIn("merged", self.second.stdout)

    def test_claude_layout(self) -> None:
        c = self.sb.home / ".claude"
        self.assertTrue((c / "CLAUDE.md").is_symlink())
        text = (c / "CLAUDE.md").read_text()
        self.assertIn("Compact instructions", text)
        self.assertNotIn("<!--", text)
        self.assertEqual(
            frontmatter(c / "rules" / "terragrunt.md"),
            {"paths": frontmatter(REPO / "rules" / "terragrunt.md")["globs"]},
        )
        self.assertNotIn("---", (c / "rules" / "terraform.md").read_text().split("\n")[0][3:])
        fm = frontmatter(c / "skills" / "challenge-architecture" / "SKILL.md")
        self.assertEqual(fm["context"], "fork")
        self.assertEqual(fm["agent"], "architecture-critic")
        self.assertNotIn("claude", fm)
        body = (c / "skills" / "infra-review" / "SKILL.md").read_text()
        self.assertIn("!`python3 ${CLAUDE_SKILL_DIR}/scripts/diff_context.py $ARGUMENTS`", body)
        self.assertNotIn("only:antigravity", body)
        self.assertTrue((c / "skills" / "infra-review" / "scripts" / "diff_context.py").exists())
        self.assertTrue((c / "agents" / "architecture-critic.md").is_symlink())
        self.assertTrue((c / "skills" / "my-skill" / "SKILL.md").exists(), "user skill untouched")

    def test_claude_settings_merge(self) -> None:
        s = json.loads((self.sb.home / ".claude" / "settings.json").read_text())
        self.assertEqual(s["model"], "opus")
        self.assertIn("Bash(make *)", s["permissions"]["allow"])
        self.assertIn("Bash(terragrunt * destroy *)", s["permissions"]["deny"])
        cmds = [h["command"] for g in s["hooks"]["PreToolUse"] for h in g["hooks"]]
        self.assertIn("my-own-hook", cmds)
        self.assertEqual(sum("pre_bash_guard.py" in c for c in cmds), 1, cmds)  # old kit hook replaced, no dupes
        self.assertTrue(any(str(REPO) in c and "--target claude" in c for c in cmds))

    def test_antigravity_layout(self) -> None:
        g = self.sb.home / ".gemini" / "config"
        self.assertNotIn("Compact instructions", (g / "AGENTS.md").read_text())
        fm = frontmatter(g / "rules" / "crossplane.md")
        self.assertEqual(fm["trigger"], "glob")
        self.assertIn("**/xrd*.yaml", fm["globs"])
        self.assertIsInstance(fm["globs"], str)
        skill = (g / "skills" / "infra-review" / "SKILL.md").read_text()
        self.assertNotIn("!`", skill)
        self.assertIn(str(g / "skills" / "infra-review") + "/scripts/diff_context.py", skill)
        sfm = frontmatter(g / "skills" / "challenge-architecture" / "SKILL.md")
        self.assertEqual(set(sfm), {"name", "description"})
        self.assertNotIn("{{ARGS}}", (g / "skills" / "grill-me" / "SKILL.md").read_text())
        self.assertFalse((g / "agents").exists())

    def test_antigravity_hooks_and_permissions(self) -> None:
        hooks = json.loads((self.sb.home / ".gemini" / "config" / "hooks.json").read_text())
        self.assertIn("mine", hooks)
        self.assertEqual(hooks["agent-toolkit-guard"]["PreToolUse"][0]["matcher"], "run_command")
        self.assertIn("--target antigravity", hooks["agent-toolkit-guard"]["PreToolUse"][0]["hooks"][0]["command"])
        self.assertIsInstance(hooks["agent-toolkit-session-context"]["SessionStart"][0]["command"], str)
        cli = json.loads((self.sb.home / ".gemini" / "antigravity-cli" / "settings.json").read_text())
        self.assertIn("command(terraform destroy)", cli["permissions"]["deny"])
        self.assertIn(f"read_file({self.sb.home}/.ssh)", cli["permissions"]["deny"])

    def test_local_guardrails_created(self) -> None:
        self.assertTrue((self.sb.home / ".config" / "agent-toolkit" / "guardrails.json").exists())

    def test_zz_exclude_and_uninstall(self) -> None:
        cfg = self.sb.root / "toolkit.yaml"
        shutil.copy(REPO / "toolkit.yaml", cfg)
        (self.sb.root / "toolkit.local.yaml").write_text(
            "target_components:\n  antigravity:\n    skills: {include: ['*'], exclude: ['handoff']}\n"
        )
        proc = self.sb.run([*TOOLKIT, "--config", str(cfg), "install"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("removed stale", proc.stdout)
        self.assertFalse(os.path.lexists(self.sb.home / ".gemini" / "config" / "skills" / "handoff"))
        self.assertTrue((self.sb.home / ".claude" / "skills" / "handoff").exists())
        proc = self.sb.run([*TOOLKIT, "uninstall"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        c = self.sb.home / ".claude"
        self.assertFalse(os.path.lexists(c / "CLAUDE.md"))
        self.assertTrue((c / "skills" / "my-skill").exists())
        s = json.loads((c / "settings.json").read_text())
        self.assertEqual(s["permissions"]["allow"], ["Bash(make *)"])
        self.assertEqual([h["command"] for g in s["hooks"]["PreToolUse"] for h in g["hooks"]], ["my-own-hook"])
        hooks = json.loads((self.sb.home / ".gemini" / "config" / "hooks.json").read_text())
        self.assertEqual(list(hooks), ["mine"])
        # restore install state for any later test
        self.sb.run([*TOOLKIT, "install", "--force"])


class DefaultsTest(unittest.TestCase):
    def test_runs_without_env_overrides(self) -> None:
        import subprocess

        env = {k: v for k, v in os.environ.items() if not k.startswith("AGENT_TOOLKIT_")}
        proc = subprocess.run([*TOOLKIT, "--help"], capture_output=True, text=True, env=env, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)


class InitProjectTest(unittest.TestCase):
    def test_init_project(self) -> None:
        sb = Sandbox()
        try:
            (sb.project / ".gitignore").write_text("node_modules/\n")
            proc = sb.run([*TOOLKIT, "init-project", str(sb.project)])
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual((sb.project / "CLAUDE.md").read_text().strip(), "@AGENTS.md")
            self.assertTrue((sb.project / ".agents" / "guardrails.json").exists())
            gi = (sb.project / ".gitignore").read_text()
            self.assertIn(".tgplan/", gi)
            self.assertIn("node_modules/", gi)
        finally:
            sb.cleanup()


if __name__ == "__main__":
    unittest.main()
