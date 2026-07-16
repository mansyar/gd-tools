# Implementation Plan: Track 26 — Shell Completion

## Phase 1: Completion Command Implementation

- [ ] Task: Write failing tests for the `completion` command
    - [ ] Create `tests/unit/test_completion.py`
    - [ ] Test `gd-tools completion bash` outputs a valid bash completion script (non-empty, contains shell completion markers)
    - [ ] Test `gd-tools completion zsh` outputs a valid zsh completion script
    - [ ] Test `gd-tools completion fish` outputs a valid fish completion script
    - [ ] Test `gd-tools completion powershell` outputs a valid PowerShell completion script
    - [ ] Test `gd-tools completion <invalid>` exits with code 2 and prints an error message
    - [ ] Run tests and confirm they fail (Red phase)

- [ ] Task: Implement the `completion` command in `cli.py`
    - [ ] Add `completion` subcommand to the `cli` group using Click's shell completion infrastructure (`click.shell_completion`)
    - [ ] Accept a `shell` argument restricted to `bash`, `zsh`, `fish`, `powershell` via `click.Choice`
    - [ ] Generate and output the completion script to stdout for the requested shell
    - [ ] Run tests and confirm they pass (Green phase)
    - [ ] Refactor if needed; rerun tests to confirm still passing

- [ ] Task: Verify coverage and quality gates
    - [ ] Run `CI=true pytest --cov=gd_tools --cov-branch --cov-report=term-missing` and confirm >80% line / >70% branch for new code
    - [ ] Run `ruff check src/ tests/` and `black --check src/ tests/` — both must pass
    - [ ] Commit code changes with message `feat(cli): Add shell completion command`
    - [ ] Attach git note with task summary to the commit

- [ ] Task: Conductor - User Manual Verification 'Completion Command' (Protocol in workflow.md)

## Phase 2: Documentation

- [ ] Task: Add Shell Completion section to README
    - [ ] Add brief setup instructions for bash, zsh, fish, and PowerShell
    - [ ] Mention Click's env-var approach (`_GD_TOOLS_COMPLETE=<shell>_source gd-tools`) as an alternative
    - [ ] Commit with message `docs(readme): Add shell completion setup instructions`

- [ ] Task: Add Shell Completion section to USER_GUIDE
    - [ ] Add detailed per-shell setup instructions:
        - Bash: `eval "$(gd-tools completion bash)"` or source from file
        - Zsh: Add to `~/.zshrc`
        - Fish: Save to `~/.config/fish/completions/`
        - PowerShell: Add to PowerShell profile
    - [ ] Document Click's env-var approach as an alternative for advanced users
    - [ ] Commit with message `docs(user-guide): Add detailed shell completion instructions`

- [ ] Task: Conductor - User Manual Verification 'Documentation' (Protocol in workflow.md)
