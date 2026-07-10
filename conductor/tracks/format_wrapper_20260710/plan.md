<protect>

# Implementation Plan: Format Wrapper (format_wrapper_20260710)

## Phase 1: Shared File Discovery Refactor [checkpoint: a413bd9]

- [x] Task: Read spec.md and workflow.md to review requirements and TDD methodology
    - [x] Read conductor/tracks/format_wrapper_20260710/spec.md
    - [x] Read conductor/workflow.md

- [x] Task: Write tests for file_discovery.py module `d51db2b`
    - [x] Test discover_gd_files discovers .gd files recursively
    - [x] Test discover_gd_files skips excluded directories (addons, .godot, etc.)
    - [x] Test discover_gd_files handles case-insensitive .gd extension
    - [x] Test discover_gd_files returns empty list when no .gd files found
    - [x] Test discover_gd_files uses DEFAULT_EXCLUDES when excludes=None
    - [x] Verify: Tests fail (Red) — module does not exist yet

- [x] Task: Create file_discovery.py and extract discover_gd_files `d51db2b`
    - [x] Create src/gd_tools/file_discovery.py
    - [x] Move discover_gd_files function and its imports from lint_runner.py
    - [x] Verify: file_discovery tests pass (Green)

- [x] Task: Update lint_runner.py to import from file_discovery.py `d51db2b`
    - [x] Replace local discover_gd_files definition with import from file_discovery
    - [x] Remove now-unused imports from lint_runner.py if applicable
    - [x] Verify: All existing lint tests still pass (no regressions)

- [x] Task: Run full test suite and verify coverage `d51db2b`
    - [x] Run pytest — all tests pass (190 tests)
    - [x] Verify file_discovery.py coverage >80% line / >70% branch (100% line)
    - [x] Run ruff check and black --check

- [x] Task: Commit Phase 1 changes `d51db2b`
    - [x] git add and commit: refactor(format): Extract shared file_discovery.py from lint_runner
    - [x] Add git note summarizing Phase 1 completion

- [x] Task: Conductor - User Manual Verification 'Phase 1: Shared File Discovery Refactor' (Protocol in workflow.md)

## Phase 2: FormatResult Dataclass and run_format Function [checkpoint: 1515e50]

- [x] Task: Read spec.md and workflow.md to review requirements and TDD methodology
    - [x] Read conductor/tracks/format_wrapper_20260710/spec.md
    - [x] Read conductor/workflow.md

- [x] Task: Write tests for FormatResult dataclass `d030fc1`
    - [x] Test FormatResult instantiation with default values
    - [x] Test FormatResult with all fields populated
    - [x] Verify: Tests fail (Red) — FormatResult does not exist yet

- [x] Task: Implement FormatResult dataclass `d030fc1`
    - [x] Create src/gd_tools/format_runner.py
    - [x] Define FormatResult dataclass with fields: files_checked, files_formatted, files_needing_format, diffs
    - [x] Add docstrings
    - [x] Verify: FormatResult tests pass (Green)

- [x] Task: Write tests for run_format default mode (format in place) `d030fc1`
    - [x] Test run_format formats an unformatted .gd file in place
    - [x] Test run_format returns FormatResult with correct files_formatted count
    - [x] Test run_format on already-formatted files makes no changes
    - [x] Test run_format uses discover_gd_files for file enumeration
    - [x] Verify: Tests fail (Red)

- [x] Task: Implement run_format default mode `d030fc1`
    - [x] Import gdformat API from gdtoolkit (investigate gdtoolkit formatter API)
    - [x] Implement run_format with check=False, diff=False path
    - [x] Format each file in place via gdtoolkit Python API
    - [x] Verify: Default mode tests pass (Green)

- [x] Task: Write tests for run_format --check mode `d030fc1`
    - [x] Test --check reports files_needing_format count for unformatted files
    - [x] Test --check returns 0 files_needing_format for already-formatted files
    - [x] Test --check does not modify files on disk
    - [x] Verify: Tests fail (Red)

- [x] Task: Implement run_format --check mode `d030fc1`
    - [x] Add check=True branch: compare formatted vs original, count differences
    - [x] Populate files_needing_format in FormatResult
    - [x] Verify: --check mode tests pass (Green)

- [x] Task: Write tests for run_format --diff mode `d030fc1`
    - [x] Test --diff returns list of unified diff strings
    - [x] Test --diff does not modify files on disk
    - [x] Test --diff returns empty diffs list for already-formatted files
    - [x] Verify: Tests fail (Red)

- [x] Task: Implement run_format --diff mode `d030fc1`
    - [x] Add diff=True branch: generate unified diff per file using difflib
    - [x] Populate diffs list in FormatResult
    - [x] Verify: --diff mode tests pass (Green)

- [x] Task: Write tests for run_format mutual exclusion `d030fc1`
    - [x] Test check=True and diff=True raises FormatError with exit_code=2
    - [x] Test error message is "--check and --diff are mutually exclusive"
    - [x] Verify: Tests fail (Red)

- [x] Task: Implement run_format mutual exclusion guard `d030fc1`
    - [x] Add early check: if check and diff, raise FormatError(msg, exit_code=2)
    - [x] Verify: Mutual exclusion tests pass (Green)

- [x] Task: Write tests for run_format syntax error handling `d030fc1`
    - [x] Test syntax-error .gd file produces clear error, does not crash
    - [x] Test syntax error includes file path in error message
    - [x] Test run_format continues processing remaining files after a syntax error
    - [x] Verify: Tests fail (Red)

- [x] Task: Implement run_format syntax error handling `d030fc1`
    - [x] Catch gdtoolkit parse exceptions (LarkError or equivalent)
    - [x] Report file path and error description, continue processing
    - [x] Verify: Syntax error tests pass (Green)

- [x] Task: Write tests for run_format no files found `d030fc1`
    - [x] Test run_format on empty directory returns FormatResult with all zeros
    - [x] Test no crash, graceful handling
    - [x] Verify: Tests fail (Red)

- [x] Task: Implement run_format no files found handling `d030fc1`
    - [x] Return FormatResult(files_checked=0, files_formatted=0, files_needing_format=0, diffs=[])
    - [x] Verify: No files found tests pass (Green)

- [x] Task: Refactor and verify run_format `d030fc1`
    - [x] Review for code duplication, extract helpers if needed
    - [x] Run ruff check and black --check on format_runner.py
    - [x] Verify format_runner.py coverage >80% line / >70% branch (100% line)

- [x] Task: Commit Phase 2 changes `d030fc1`
    - [x] git add and commit: feat(format): Implement FormatResult and run_format function
    - [x] Add git note summarizing Phase 2 completion

- [x] Task: Conductor - User Manual Verification 'Phase 2: FormatResult Dataclass and run_format Function' (Protocol in workflow.md)

## Phase 3: CLI Format Command Implementation

- [x] Task: Read spec.md and workflow.md to review requirements and TDD methodology
    - [x] Read conductor/tracks/format_wrapper_20260710/spec.md
    - [x] Read conductor/workflow.md

- [x] Task: Write tests for CLI format command (default mode) `101e883`
    - [x] Test `gd-tools format <path>` formats files and prints summary
    - [x] Test exit code 0 on success
    - [x] Test path defaults to '.' when not provided
    - [x] Verify: Tests fail (Red) — command still raises NotImplementedError

- [x] Task: Implement CLI format command (default mode) `101e883`
    - [x] Replace NotImplementedError with actual implementation
    - [x] Update @click.argument to required=False, default='.'
    - [x] Load config via load_config()
    - [x] Call run_format(config, path) and print summary
    - [x] Handle ConfigError (exit 2)
    - [x] Verify: Default mode CLI tests pass (Green)

- [x] Task: Write tests for CLI format --check mode `101e883`
    - [x] Test `gd-tools format --check <path>` lists unformatted files
    - [x] Test exit code 1 when files need formatting
    - [x] Test exit code 0 when all files are formatted
    - [x] Verify: Tests fail (Red)

- [x] Task: Implement CLI format --check mode `101e883`
    - [x] Call run_format(config, path, check=True)
    - [x] Print list of files needing formatting
    - [x] Exit 1 if files_needing_format > 0, else exit 0
    - [x] Verify: --check CLI tests pass (Green)

- [x] Task: Write tests for CLI format --diff mode `101e883`
    - [x] Test `gd-tools format --diff <path>` renders diffs via rich Console
    - [x] Test diffs include file path headers
    - [x] Test green/red syntax highlighting in diff output
    - [x] Test exit code 0
    - [x] Verify: Tests fail (Red)

- [x] Task: Implement CLI format --diff mode `101e883`
    - [x] Call run_format(config, path, diff=True)
    - [x] Render each diff with rich Console (green additions, red deletions)
    - [x] Prefix each diff block with file path
    - [x] Verify: --diff CLI tests pass (Green)

- [x] Task: Write tests for CLI --check + --diff conflict `101e883`
    - [x] Test `gd-tools format --check --diff <path>` prints error message
    - [x] Test exit code 2
    - [x] Verify: Tests fail (Red)

- [x] Task: Implement CLI --check + --diff conflict handling `101e883`
    - [x] Add early check: if check and diff, echo error, exit 2
    - [x] Verify: Conflict handling tests pass (Green)

- [x] Task: Refactor and verify CLI format command `101e883`
    - [x] Review for consistency with lint command pattern
    - [x] Run ruff check and black --check on cli.py
    - [x] Verify cli.py format-related coverage >80% line / >70% branch (100% line, 100% branch)

- [x] Task: Commit Phase 3 changes `101e883`
    - [x] git add and commit: feat(format): Implement CLI format command with --check and --diff modes
    - [x] Add git note summarizing Phase 3 completion

- [ ] Task: Conductor - User Manual Verification 'Phase 3: CLI Format Command Implementation' (Protocol in workflow.md)

> **Deviation Note:** Added `files_needing_format_paths: list[str]` field to
> `FormatResult` in `format_runner.py` (not in original Phase 3 plan) to satisfy
> spec FR-4 point 7: "Print list of files needing formatting." Updated
> `test_format_runner.py` with assertions for the new field.

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
