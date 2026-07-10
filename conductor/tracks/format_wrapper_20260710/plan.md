<protect>

# Implementation Plan: Format Wrapper (format_wrapper_20260710)

## Phase 1: Shared File Discovery Refactor

- [ ] Task: Read spec.md and workflow.md to review requirements and TDD methodology
    - [ ] Read conductor/tracks/format_wrapper_20260710/spec.md
    - [ ] Read conductor/workflow.md

- [ ] Task: Write tests for file_discovery.py module
    - [ ] Test discover_gd_files discovers .gd files recursively
    - [ ] Test discover_gd_files skips excluded directories (addons, .godot, etc.)
    - [ ] Test discover_gd_files handles case-insensitive .gd extension
    - [ ] Test discover_gd_files returns empty list when no .gd files found
    - [ ] Test discover_gd_files uses DEFAULT_EXCLUDES when excludes=None
    - [ ] Verify: Tests fail (Red) — module does not exist yet

- [ ] Task: Create file_discovery.py and extract discover_gd_files
    - [ ] Create src/gd_tools/file_discovery.py
    - [ ] Move discover_gd_files function and its imports from lint_runner.py
    - [ ] Verify: file_discovery tests pass (Green)

- [ ] Task: Update lint_runner.py to import from file_discovery.py
    - [ ] Replace local discover_gd_files definition with import from file_discovery
    - [ ] Remove now-unused imports from lint_runner.py if applicable
    - [ ] Verify: All existing lint tests still pass (no regressions)

- [ ] Task: Run full test suite and verify coverage
    - [ ] Run pytest — all tests pass
    - [ ] Verify file_discovery.py coverage >80% line / >70% branch
    - [ ] Run ruff check and black --check

- [ ] Task: Commit Phase 1 changes
    - [ ] git add and commit: refactor(format): Extract shared file_discovery.py from lint_runner
    - [ ] Add git note summarizing Phase 1 completion

- [ ] Task: Conductor - User Manual Verification 'Phase 1: Shared File Discovery Refactor' (Protocol in workflow.md)

## Phase 2: FormatResult Dataclass and run_format Function

- [ ] Task: Read spec.md and workflow.md to review requirements and TDD methodology
    - [ ] Read conductor/tracks/format_wrapper_20260710/spec.md
    - [ ] Read conductor/workflow.md

- [ ] Task: Write tests for FormatResult dataclass
    - [ ] Test FormatResult instantiation with default values
    - [ ] Test FormatResult with all fields populated
    - [ ] Verify: Tests fail (Red) — FormatResult does not exist yet

- [ ] Task: Implement FormatResult dataclass
    - [ ] Create src/gd_tools/format_runner.py
    - [ ] Define FormatResult dataclass with fields: files_checked, files_formatted, files_needing_format, diffs
    - [ ] Add docstrings
    - [ ] Verify: FormatResult tests pass (Green)

- [ ] Task: Write tests for run_format default mode (format in place)
    - [ ] Test run_format formats an unformatted .gd file in place
    - [ ] Test run_format returns FormatResult with correct files_formatted count
    - [ ] Test run_format on already-formatted files makes no changes
    - [ ] Test run_format uses discover_gd_files for file enumeration
    - [ ] Verify: Tests fail (Red)

- [ ] Task: Implement run_format default mode
    - [ ] Import gdformat API from gdtoolkit (investigate gdtoolkit formatter API)
    - [ ] Implement run_format with check=False, diff=False path
    - [ ] Format each file in place via gdtoolkit Python API
    - [ ] Verify: Default mode tests pass (Green)

- [ ] Task: Write tests for run_format --check mode
    - [ ] Test --check reports files_needing_format count for unformatted files
    - [ ] Test --check returns 0 files_needing_format for already-formatted files
    - [ ] Test --check does not modify files on disk
    - [ ] Verify: Tests fail (Red)

- [ ] Task: Implement run_format --check mode
    - [ ] Add check=True branch: compare formatted vs original, count differences
    - [ ] Populate files_needing_format in FormatResult
    - [ ] Verify: --check mode tests pass (Green)

- [ ] Task: Write tests for run_format --diff mode
    - [ ] Test --diff returns list of unified diff strings
    - [ ] Test --diff does not modify files on disk
    - [ ] Test --diff returns empty diffs list for already-formatted files
    - [ ] Verify: Tests fail (Red)

- [ ] Task: Implement run_format --diff mode
    - [ ] Add diff=True branch: generate unified diff per file using difflib
    - [ ] Populate diffs list in FormatResult
    - [ ] Verify: --diff mode tests pass (Green)

- [ ] Task: Write tests for run_format mutual exclusion
    - [ ] Test check=True and diff=True raises FormatError with exit_code=2
    - [ ] Test error message is "--check and --diff are mutually exclusive"
    - [ ] Verify: Tests fail (Red)

- [ ] Task: Implement run_format mutual exclusion guard
    - [ ] Add early check: if check and diff, raise FormatError(msg, exit_code=2)
    - [ ] Verify: Mutual exclusion tests pass (Green)

- [ ] Task: Write tests for run_format syntax error handling
    - [ ] Test syntax-error .gd file produces clear error, does not crash
    - [ ] Test syntax error includes file path in error message
    - [ ] Test run_format continues processing remaining files after a syntax error
    - [ ] Verify: Tests fail (Red)

- [ ] Task: Implement run_format syntax error handling
    - [ ] Catch gdtoolkit parse exceptions (LarkError or equivalent)
    - [ ] Report file path and error description, continue processing
    - [ ] Verify: Syntax error tests pass (Green)

- [ ] Task: Write tests for run_format no files found
    - [ ] Test run_format on empty directory returns FormatResult with all zeros
    - [ ] Test no crash, graceful handling
    - [ ] Verify: Tests fail (Red)

- [ ] Task: Implement run_format no files found handling
    - [ ] Return FormatResult(files_checked=0, files_formatted=0, files_needing_format=0, diffs=[])
    - [ ] Verify: No files found tests pass (Green)

- [ ] Task: Refactor and verify run_format
    - [ ] Review for code duplication, extract helpers if needed
    - [ ] Run ruff check and black --check on format_runner.py
    - [ ] Verify format_runner.py coverage >80% line / >70% branch

- [ ] Task: Commit Phase 2 changes
    - [ ] git add and commit: feat(format): Implement FormatResult and run_format function
    - [ ] Add git note summarizing Phase 2 completion

- [ ] Task: Conductor - User Manual Verification 'Phase 2: FormatResult Dataclass and run_format Function' (Protocol in workflow.md)

## Phase 3: CLI Format Command Implementation

- [ ] Task: Read spec.md and workflow.md to review requirements and TDD methodology
    - [ ] Read conductor/tracks/format_wrapper_20260710/spec.md
    - [ ] Read conductor/workflow.md

- [ ] Task: Write tests for CLI format command (default mode)
    - [ ] Test `gd-tools format <path>` formats files and prints summary
    - [ ] Test exit code 0 on success
    - [ ] Test path defaults to '.' when not provided
    - [ ] Verify: Tests fail (Red) — command still raises NotImplementedError

- [ ] Task: Implement CLI format command (default mode)
    - [ ] Replace NotImplementedError with actual implementation
    - [ ] Update @click.argument to required=False, default='.'
    - [ ] Load config via load_config()
    - [ ] Call run_format(config, path) and print summary
    - [ ] Handle ConfigError (exit 2)
    - [ ] Verify: Default mode CLI tests pass (Green)

- [ ] Task: Write tests for CLI format --check mode
    - [ ] Test `gd-tools format --check <path>` lists unformatted files
    - [ ] Test exit code 1 when files need formatting
    - [ ] Test exit code 0 when all files are formatted
    - [ ] Verify: Tests fail (Red)

- [ ] Task: Implement CLI format --check mode
    - [ ] Call run_format(config, path, check=True)
    - [ ] Print list of files needing formatting
    - [ ] Exit 1 if files_needing_format > 0, else exit 0
    - [ ] Verify: --check CLI tests pass (Green)

- [ ] Task: Write tests for CLI format --diff mode
    - [ ] Test `gd-tools format --diff <path>` renders diffs via rich Console
    - [ ] Test diffs include file path headers
    - [ ] Test green/red syntax highlighting in diff output
    - [ ] Test exit code 0
    - [ ] Verify: Tests fail (Red)

- [ ] Task: Implement CLI format --diff mode
    - [ ] Call run_format(config, path, diff=True)
    - [ ] Render each diff with rich Console (green additions, red deletions)
    - [ ] Prefix each diff block with file path
    - [ ] Verify: --diff CLI tests pass (Green)

- [ ] Task: Write tests for CLI --check + --diff conflict
    - [ ] Test `gd-tools format --check --diff <path>` prints error message
    - [ ] Test exit code 2
    - [ ] Verify: Tests fail (Red)

- [ ] Task: Implement CLI --check + --diff conflict handling
    - [ ] Add early check: if check and diff, echo error, exit 2
    - [ ] Verify: Conflict handling tests pass (Green)

- [ ] Task: Refactor and verify CLI format command
    - [ ] Review for consistency with lint command pattern
    - [ ] Run ruff check and black --check on cli.py
    - [ ] Verify cli.py format-related coverage >80% line / >70% branch

- [ ] Task: Commit Phase 3 changes
    - [ ] git add and commit: feat(format): Implement CLI format command with --check and --diff modes
    - [ ] Add git note summarizing Phase 3 completion

- [ ] Task: Conductor - User Manual Verification 'Phase 3: CLI Format Command Implementation' (Protocol in workflow.md)

## Phase 4: Integration and gdformatrc Verification

- [ ] Task: Read spec.md and workflow.md to review requirements and TDD methodology
    - [ ] Read conductor/tracks/format_wrapper_20260710/spec.md
    - [ ] Read conductor/workflow.md

- [ ] Task: Write integration tests for gdformatrc + format runner
    - [ ] Test gd-tools init generates valid gdformatrc
    - [ ] Test format runner respects excludes from gdformatrc
    - [ ] Test addons/ directory excluded by default
    - [ ] Verify: Tests fail or pass (integration — may already pass from Track 2)

- [ ] Task: Verify gdformatrc integration
    - [ ] Run gd-tools init in a temp project, confirm gdformatrc created
    - [ ] Run gd-tools format on project with addons/, confirm addons excluded
    - [ ] Confirm gdformat works standalone with generated gdformatrc
    - [ ] Verify: All integration tests pass

- [ ] Task: Run full test suite and final verification
    - [ ] Run pytest — all tests pass (existing + new)
    - [ ] Verify no regressions in lint tests
    - [ ] Verify overall coverage thresholds maintained (>80% line / >70% branch)
    - [ ] Run ruff check --fix on entire codebase
    - [ ] Run black --check on entire codebase
    - [ ] Run mypy type checking if configured

- [ ] Task: Commit Phase 4 changes
    - [ ] git add and commit: test(format): Add integration tests for gdformatrc verification
    - [ ] Add git note summarizing Phase 4 completion and track completion

- [ ] Task: Conductor - User Manual Verification 'Phase 4: Integration and gdformatrc Verification' (Protocol in workflow.md)

</protect>
