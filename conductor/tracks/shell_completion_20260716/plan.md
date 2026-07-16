<protect>
# Implementation Plan: Track 26 — Shell Completion

## Phase 1: Completion Command Implementation

- [x] Task: Read `spec.md` and `workflow.md` to review requirements and TDD protocol before starting implementation
    - [x] Read `conductor/tracks/shell_completion_20260716/spec.md`
    - [x] Read `conductor/workflow.md`

- [x] Task: Write failing tests for the `completion` command
    - [x] Create `tests/unit/test_completion.py`
    - [x] Test `gd-tools completion bash` outputs a valid bash completion script (non-empty, contains shell completion markers)
    - [x] Test `gd-tools completion zsh` outputs a valid zsh completion script
    - [x] Test `gd-tools completion fish` outputs a valid fish completion script
    - [x] Test `gd-tools completion powershell` outputs a valid PowerShell completion script
    - [x] Test `gd-tools completion <invalid>` exits with code 2 and prints an error message
    - [x] Run tests and confirm they fail (Red phase)

- [x] Task: Implement the `completion` command in `cli.py`
    - [x] Add `completion` subcommand to the `cli` group using Click's shell completion infrastructure (`click.shell_completion`)
    - [x] Accept a `shell` argument restricted to `bash`, `zsh`, `fish`, `powershell` via `click.Choice`
    - [x] Generate and output the completion script to stdout for the requested shell
    - [x] Run tests and confirm they pass (Green phase)
    - [x] Refactor if needed; rerun tests to confirm still passing

- [x] Task: Verify coverage and quality gates
    - [x] Run `CI=true pytest --cov=gd_tools --cov-branch --cov-report=term-missing` and confirm >80% line / >70% branch for new code
    - [x] Run `ruff check src/ tests/` and `black --check src/ tests/` — both must pass
    - [x] Commit code changes with message `feat(cli): Add shell completion command` (39e4bfd)
    - [x] Attach git note with task summary to the commit

- [x] Task: Conductor - User Manual Verification 'Completion Command' (Protocol in workflow.md)

## Phase 2: Documentation

- [ ] Task: Read `spec.md` and `workflow.md` to review requirements and TDD protocol before starting implementation
    - [ ] Read `conductor/tracks/shell_completion_20260716/spec.md`
    - [ ] Read `conductor/workflow.md`

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
</protect>
