# Track 26: Shell Completion

## Overview

`gd-tools` is built on Click, which provides native shell completion support (since Click 8.0). However, gd-tools does not currently document or expose this capability. Users on bash, zsh, fish, and PowerShell receive no tab completion for commands, subcommands, options, or flags.

This track adds a `gd-tools completion [shell]` subcommand that outputs the appropriate completion script for the user's shell, along with documentation in README and USER_GUIDE covering setup instructions for each supported shell.

## Functional Requirements

### FR-1: Completion Subcommand
- Add a `gd-tools completion <shell>` subcommand to the CLI.
- The `<shell>` argument accepts one of: `bash`, `zsh`, `fish`, `powershell`.
- The command outputs the completion script for the specified shell to stdout.
- The completion script is generated via Click's built-in shell completion infrastructure.
- If an unsupported shell name is provided, the command exits with an error message and exit code 2 (usage error).

### FR-2: Static Completion Only
- Completion covers all gd-tools commands, subcommands, options, and flags.
- No dynamic value completion (e.g., file paths, config names) is required for this track.
- Click handles static completion automatically based on the command/option definitions.

### FR-3: No Init Integration
- Shell completion setup is NOT part of `gd-tools init`.
- Completion is a user-environment concern, not a project concern. Users install it independently.

### FR-4: Documentation
- Add a "Shell Completion" section to README with brief setup instructions for each shell.
- Add a "Shell Completion" section to USER_GUIDE with detailed setup instructions for each shell, including:
  - **Bash**: How to source the script (e.g., `eval "$(gd-tools completion bash)"` or source from a file).
  - **Zsh**: How to add to `~/.zshrc`.
  - **Fish**: How to save to `~/.config/fish/completions/`.
  - **PowerShell**: How to add to the PowerShell profile.
- Document Click's built-in environment variable approach (`_GD_TOOLS_COMPLETE=<shell>_source gd-tools`) as an alternative for advanced users.

## Non-Functional Requirements

- **Cross-platform**: Completion scripts must work on Windows (PowerShell), macOS (zsh/bash), and Linux (bash/fish/zsh).
- **Performance**: Completion script generation must be near-instantaneous (no network calls, no file I/O beyond reading Click's command tree).
- **Exit codes**: 0 on success, 2 on invalid shell argument.

## Acceptance Criteria

1. `gd-tools completion bash` prints a valid bash completion script to stdout.
2. `gd-tools completion zsh` prints a valid zsh completion script to stdout.
3. `gd-tools completion fish` prints a valid fish completion script to stdout.
4. `gd-tools completion powershell` prints a valid PowerShell completion script to stdout.
5. `gd-tools completion <invalid>` exits with code 2 and an error message.
6. README includes a "Shell Completion" section with setup instructions.
7. USER_GUIDE includes a "Shell Completion" section with detailed per-shell setup instructions.
8. Click's environment variable approach is documented as an alternative.

## Out of Scope

- Dynamic completion of argument values (file paths, config names, report formats).
- Automatic installation of completion scripts into shell profiles (no `--install` flag).
- Integration with `gd-tools init`.
- Completion for shells other than bash, zsh, fish, and PowerShell.
- Testing that completion scripts actually function in real shells (only script generation is tested).
