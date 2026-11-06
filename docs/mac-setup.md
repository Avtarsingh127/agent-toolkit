# Mac setup

About 30 minutes on a fresh Mac; 10 if the CLIs are already there. Commands assume Apple Silicon and zsh.

## 1. Base tools
```bash
xcode-select --install                         # git, make, compilers (skip if already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"   # if no Homebrew
brew install git uv jq yq ripgrep shellcheck tflint helm kubectl kubeconform argocd gh glab terraform-docs ruff gitleaks
brew tap hashicorp/tap && brew install hashicorp/tap/terraform
brew install terragrunt
brew install --cask google-cloud-sdk
gcloud components install gke-gcloud-auth-plugin
```

Crossplane CLI (the install script downloads into the current directory):
```bash
cd /tmp && curl -sfL "https://cli.crossplane.io/install.sh" | sh && sudo mv crossplane /usr/local/bin/
crossplane --version
```
`crossplane composition render` runs functions in containers, so you need a container runtime: Docker Desktop, OrbStack or Colima (`brew install colima docker && colima start`).

## 2. The agents
```bash
curl -fsSL https://claude.ai/install.sh | bash      # Claude Code CLI (or: brew install --cask claude-code)
claude doctor
```
VS Code: install the **Claude Code** extension from the marketplace. It shares `~/.claude` with the CLI.

Antigravity: install the desktop App/IDE from antigravity.google, and the CLI if you want it:
```bash
curl -fsSL https://antigravity.google/cli/install.sh | bash    # installs ~/.local/bin/agy
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc
```
If you installed the App with Homebrew and the CLI complains that `agy` isn't found, link it: `sudo ln -s /opt/homebrew/bin/antigravity /usr/local/bin/agy`.

## 3. Get the toolkit
Pick a permanent location: the installed hooks point at this folder, so if you move it, run `make install` again.
```bash
mkdir -p ~/code && cd ~/code
git clone https://github.com/Avtarsingh127/agent-toolkit.git
cd agent-toolkit
make doctor          # checks tools; smoke-tests the guard for both agents
make test            # all tests should pass
make dry-run         # shows every link and settings change
```

## 4. Install
First install, coming from the v1 `claude-gcp-kit` (it copied files into `~/.claude`):
```bash
make install-force   # backs up conflicting files to ~/.agent-toolkit-backups/<timestamp>/ then links
```
Fresh machine: `make install`.

Then clean up v1 leftovers that are no longer referenced:
```bash
rm -rf ~/.claude/skills/arch-doc
rm -f ~/.claude/hooks/{pre_bash_guard,post_edit_check,session_context,_guardrails_config}.py
# move any prod patterns from the old ~/.claude/guardrails.json into the new local file, then:
rm -f ~/.claude/guardrails.json
```

## 5. Tell the guard what prod looks like
Edit `~/.config/agent-toolkit/guardrails.json` (created by install, not in git):
```json
{
  "prod": {
    "gcp_project_patterns_extra": ["<regex for prod project IDs>"],
    "kube_context_patterns_extra": ["<regex for prod GKE contexts>"],
    "path_patterns_extra": ["<regex for prod Terragrunt dirs>"]
  }
}
```
The defaults already catch `prod`/`prd` tokens. Test it: `make doctor`, then in either agent ask it to run `kubectl --context <a prod context> scale deploy/x --replicas 0` and confirm it asks first.

## 6. Antigravity App permissions
The App keeps permissions in its UI, not a file. Open `build/antigravity/app-permissions.txt` and paste the lists into **Settings > General > Global Permissions**. (The CLI's `~/.gemini/antigravity-cli/settings.json` was merged automatically.) Check **Settings > Customizations > Hooks** lists the three `agent-toolkit-*` hooks.

## 7. Verify both agents
| Check | Claude Code | Antigravity |
|---|---|---|
| Instructions loaded | `/context` shows CLAUDE.md ~0.6K | Customizations shows the global AGENTS.md |
| Skills | `/` menu lists `discuss`, `grill-me`, `poc`, … | `/discuss` in the App; skills listed in Customizations |
| Hooks | `/hooks` shows 3 | Customizations > Hooks shows 3 (CLI: `/hooks`) |
| Guard | ask it to run `terraform destroy` in a scratch dir → refused | same |
| Session context | first reply knows your active gcloud project | same |

## 8. Per repository
```bash
make init-project REPO=~/code/<infra-repo>
```
Writes `AGENTS.md` (fill the placeholders), `CLAUDE.md` (`@AGENTS.md`, so both agents read the same file), `.agents/guardrails.json`, `.claude/settings.json` and `.gitignore` lines. Commit them so the team shares them.

## 9. Keep it in Git
The repo is public at https://github.com/Avtarsingh127/agent-toolkit. CI runs the tests and a gitleaks secret scan on every push and pull request.
```bash
gh auth login         # once, so you can push
make git-hooks        # rebuild automatically after git pull/checkout
```
Daily loop for changes: edit → `make test` → `make scan` → `make install` → commit → push (or open a pull request). On another Mac: `git pull` (rebuilds), then `make install` if you added or removed skills or rules.

Because the repo is public, anything specific to you or your employer goes in the files that are never committed: `~/.config/agent-toolkit/guardrails.json`, `toolkit.local.yaml`, or a work repo's own `.agents/guardrails.json`.
