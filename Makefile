# agent-toolkit — run `make help`.
# Uses uv when present (PyYAML pulled automatically), else a local .venv.

UV := $(shell command -v uv 2>/dev/null)
ifeq ($(UV),)
PY := .venv/bin/python
DEPS := .venv/bin/python
else
PY := uv run --quiet --script
DEPS :=
endif
TOOLKIT := $(PY) tools/toolkit.py

.PHONY: help build install install-force dry-run uninstall status doctor test lint scan new-skill new-rule init-project git-hooks

help: ## Show targets
	@grep -E '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-14s %s\n", $$1, $$2}'

.venv/bin/python:
	python3 -m venv .venv && .venv/bin/pip install --quiet pyyaml

build: $(DEPS) ## Render build/<agent>/ from the sources
	$(TOOLKIT) build

install: $(DEPS) ## Build and link into Claude Code and Antigravity (keeps conflicts untouched)
	$(TOOLKIT) install

install-force: $(DEPS) ## Install, backing up and replacing conflicting files (e.g. the old kit)
	$(TOOLKIT) install --force

dry-run: $(DEPS) ## Show what install would change
	$(TOOLKIT) install --dry-run

uninstall: $(DEPS) ## Remove links and managed hooks/permissions
	$(TOOLKIT) uninstall

status: $(DEPS) ## Installed state, conflicts, always-on token cost
	$(TOOLKIT) status

doctor: $(DEPS) ## Check tools and smoke-test the guard for both agents
	$(TOOLKIT) doctor

test: $(DEPS) ## Run the test suite
	$(if $(UV),uv run --quiet --with pyyaml python,$(PY)) -m unittest discover -s tests -v

lint: ## ruff over the repo
	ruff check . && ruff format --check .

scan: ## Scan files and git history for secrets (needs gitleaks; CI runs it on every push)
	@command -v gitleaks >/dev/null || { echo "gitleaks not found: brew install gitleaks"; exit 1; }
	gitleaks git . --redact && gitleaks git . --pre-commit --redact

new-skill: $(DEPS) ## Scaffold a skill: make new-skill NAME=my-skill
	$(TOOLKIT) new-skill $(NAME)

new-rule: $(DEPS) ## Scaffold a rule: make new-rule NAME=my-rule
	$(TOOLKIT) new-rule $(NAME)

init-project: $(DEPS) ## Add AGENTS.md/CLAUDE.md/.agents to a repo: make init-project REPO=~/code/x
	$(TOOLKIT) init-project $(REPO)

git-hooks: ## Rebuild automatically after git pull/checkout
	printf '#!/bin/sh\nmake -s -C "$$(git rev-parse --show-toplevel)" build >/dev/null\n' > .git/hooks/post-merge
	cp .git/hooks/post-merge .git/hooks/post-checkout
	chmod +x .git/hooks/post-merge .git/hooks/post-checkout
	@echo "installed post-merge and post-checkout hooks"
