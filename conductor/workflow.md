<protect>
# Project Workflow

## Guiding Principles

1. **The Plan is the Source of Truth:** All work must be tracked in `plan.md`
2. **The Tech Stack is Deliberate:** Changes to the tech stack must be documented in `tech-stack.md` *before* implementation
3. **Test-Driven Development:** Write unit tests before implementing functionality
4. **High Code Coverage:** Aim for >80% code coverage for all source code modules
5. **User Experience First:** Every decision should prioritize user experience
6. **Non-Interactive & CI-Aware:** Prefer non-interactive commands. Use `CI=true` for watch-mode tools (tests, linters) to ensure single execution.

## AI Agent Behavioral Guidelines

When an AI agent (such as Claude, Cursor, Roo, or Conductor itself) is executing tasks in this repository, it MUST adhere to the following code of conduct:

**1. Think Before Coding**
- State assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

**2. Simplicity First**
- Write the minimum code that solves the problem. Nothing speculative.
- No features beyond what was asked. No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- Ask: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

**3. Surgical Changes**
- Touch only what you must. Clean up only your own mess.
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken. Match existing style.
- Remove imports/variables/functions that YOUR changes made unused, but don't delete pre-existing dead code unless asked.

**4. Goal-Driven Execution**
- Define success criteria and loop until verified.
- Transform tasks into verifiable goals (e.g., "Fix the bug" → "Write a test that reproduces it, then make it pass").
- For multi-step tasks, state a brief plan and verify each step.

## Task Workflow

All tasks follow a strict lifecycle:

### Standard Task Workflow

1. **Select Task:** Choose the next available task from `plan.md` in sequential order

2. **Mark In Progress:** Before beginning work, edit `plan.md` and change the task from `[ ]` to `[~]`

3. **Write Failing Tests (Red Phase):**
   - Create a new test file for the feature or bug fix.
   - Write one or more unit tests that clearly define the expected behavior and acceptance criteria for the task.
   - **CRITICAL:** Tests are only required for source code files (`.py`, `.gd`). Configuration files (`.toml`, `.json`, `.yaml`), documentation (`.md`), and other non-code assets do NOT require tests.
   - **CRITICAL:** Run the tests and confirm that they fail as expected. This is the "Red" phase of TDD. Do not proceed until you have failing tests.

4. **Implement to Pass Tests (Green Phase):**
   - Write the minimum amount of application code necessary to make the failing tests pass.
   - Run the test suite again and confirm that all tests now pass. This is the "Green" phase.

5. **Refactor (Optional but Recommended):**
   - With the safety of passing tests, refactor the implementation code and the test code to improve clarity, remove duplication, and enhance performance without changing the external behavior.
   - Rerun tests to ensure they still pass after refactoring.

6. **Verify Coverage:** Run coverage reports using the project's chosen tools:
   ```bash
   pytest --cov=gd_tools --cov-report=html --cov-branch
   ```
   Target: >80% line coverage and >70% branch coverage for new source code. Coverage is measured against source code only (`.py` files in `src/gd_tools/`), not config files or documentation.

7. **Document Deviations:** If implementation differs from tech stack:
   - **STOP** implementation
   - Update `tech-stack.md` with new design
   - Add dated note explaining the change
   - Resume implementation

8. **Commit Code Changes:**
   - Stage all code changes related to the task.
   - Propose a clear, concise commit message e.g, `feat(config): Implement gd-tools.toml loading and validation`.
   - Perform the commit.

9. **Attach Task Summary with Git Notes:**
   - **Step 9.1: Get Commit Hash:** Obtain the hash of the *just-completed commit* (`git log -1 --format="%H"`).
   - **Step 9.2: Draft Note Content:** Create a detailed summary for the completed task. This should include the task name, a summary of changes, a list of all created/modified files, and the core "why" for the change.
   - **Step 9.3: Attach Note:** Use the `git notes` command to attach the summary to the commit.
     ```bash
     # The note content from the previous step is passed via the -m flag.
     git notes add -m "<note content>" <commit_hash>
     ```

10. **Get and Record Task Commit SHA:**
    - **Step 10.1: Update Plan:** Read `plan.md`, find the line for the completed task, update its status from `[~]` to `[x]`, and append the first 7 characters of the *just-completed commit's* commit hash.
    - **Step 10.2: Write Plan:** Write the updated content back to `plan.md`.

11. **Commit Plan Update:**
    - **Action:** Stage the modified `plan.md` file.
    - **Action:** Commit this change with a descriptive message (e.g., `conductor(plan): Mark task 'Implement config loading' as complete`).

### Phase Completion Verification and Checkpointing Protocol

**Trigger:** This protocol is executed immediately after a task is completed that also concludes a phase in `plan.md`.

1.  **Announce Protocol Start:** Inform the user that the phase is complete and the verification and checkpointing protocol has begun.

2.  **Ensure Test Coverage for Phase Changes:**
    -   **Step 2.1: Determine Phase Scope:** To identify the files changed in this phase, you must first find the starting point. Read `plan.md` to find the Git commit SHA of the *previous* phase's checkpoint. If no previous checkpoint exists, the scope is all changes since the first commit.
    -   **Step 2.2: List Changed Files:** Execute `git diff --name-only <previous_checkpoint_sha> HEAD` to get a precise list of all files modified during this phase.
    -   **Step 2.3: Verify and Create Tests:** For each file in the list:
        -   **CRITICAL:** First, check its extension. Exclude non-code files (e.g., `.json`, `.md`, `.yaml`, `.toml`). Only source code files (`.py`, `.gd`) require tests.
        -   For each remaining source code file, verify a corresponding test file exists.
        -   If a test file is missing, you **must** create one. Before writing the test, **first, analyze other test files in the repository to determine the correct naming convention and testing style.** The new tests **must** validate the functionality described in this phase's tasks (`plan.md`).

3.  **Execute Automated Tests with Proactive Debugging:**
    -   Before execution, you **must** announce the exact shell command you will use to run the tests.
    -   **Example Announcement:** "I will now run the automated test suite to verify the phase. **Command:** `CI=true pytest`"
    -   Execute the announced command.
    -   If tests fail, you **must** inform the user and begin debugging. You may attempt to propose a fix a **maximum of two times**. If the tests still fail after your second proposed fix, you **must stop**, report the persistent failure, and ask the user for guidance.

4.  **Propose a Detailed, Actionable Manual Verification Plan:**
    -   **CRITICAL:** To generate the plan, first analyze `product.md`, `product-guidelines.md`, and `plan.md` to determine the user-facing goals of the completed phase.
    -   You **must** generate a step-by-step plan that walks the user through the verification process, including any necessary commands and specific, expected outcomes.
    -   The plan you present to the user **must** follow this format:

        **For a CLI Feature Change:**
        ```
        The automated tests have passed. For manual verification, please follow these steps:

        **Manual Verification Steps:**
        1.  **Ensure gd-tools is installed:** `pip install -e .`
        2.  **Run the command:** `gd-tools <command> [options]`
        3.  **Confirm that you see:** The expected output (e.g., lint results in a rich table, coverage summary, exit code 0).
        ```

        **For a Coverage System Change:**
        ```
        The automated tests have passed. For manual verification, please follow these steps:

        **Manual Verification Steps:**
        1.  **Ensure a Godot test project is available** with GUT installed (`gd-tools init`).
        2.  **Run coverage:** `gd-tools test --coverage --min 80`
        3.  **Confirm that you see:** Coverage reports generated in `.gd-tools/coverage/html/`, with correct line and branch percentages.
        ```

5.  **Await Explicit User Feedback:**
    -   After presenting the detailed plan, ask the user for confirmation: "**Does this meet your expectations? Please confirm with yes or provide feedback on what needs to be changed.**"
    -   **PAUSE** and await the user's response. Do not proceed without an explicit yes or confirmation.

6.  **Create Checkpoint Commit:**
    -   Stage all changes. If no changes occurred in this step, proceed with an empty commit.
    -   Perform the commit with a clear and concise message (e.g., `conductor(checkpoint): Checkpoint end of Phase X`).

7.  **Attach Auditable Verification Report using Git Notes:**
    -   **Step 7.1: Draft Note Content:** Create a detailed verification report including the automated test command, the manual verification steps, and the user's confirmation.
    -   **Step 7.2: Attach Note:** Use the `git notes` command and the full commit hash from the previous step to attach the full report to the checkpoint commit.

8.  **Get and Record Phase Checkpoint SHA:**
    -   **Step 8.1: Get Commit Hash:** Obtain the hash of the *just-created checkpoint commit* (`git log -1 --format="%H"`).
    -   **Step 8.2: Update Plan:** Read `plan.md`, find the heading for the completed phase, and append the first 7 characters of the commit hash in the format `[checkpoint: <sha>]`.
    -   **Step 8.3: Write Plan:** Write the updated content back to `plan.md`.

9. **Commit Plan Update:**
    - **Action:** Stage the modified `plan.md` file.
    - **Action:** Commit this change with a descriptive message following the format `conductor(plan): Mark phase '<PHASE NAME>' as complete`.

10.  **Announce Completion:** Inform the user that the phase is complete and the checkpoint has been created, with the detailed verification report attached as a git note.

### Quality Gates

Before marking any task complete, verify:

- [ ] All tests pass
- [ ] Code coverage meets requirements (>80% line, >70% branch for source code)
- [ ] Code follows project's code style guidelines (as defined in `code_styleguides/`)
- [ ] All public functions/methods are documented (Python docstrings, GDScript comments)
- [ ] Type safety is enforced (Python type hints)
- [ ] No linting or static analysis errors (`ruff check`, `black --check`)
- [ ] Documentation updated if needed
- [ ] No security vulnerabilities introduced

## Development Commands

### Setup
```bash
# Install gd-tools in editable mode with dev dependencies
pip install -e ".[dev]"
```

### Daily Development
```bash
# Run the full test suite
CI=true pytest

# Run tests with coverage
CI=true pytest --cov=gd_tools --cov-branch --cov-report=term-missing

# Run a specific test file
CI=true pytest tests/test_config.py

# Lint the codebase
ruff check src/ tests/

# Format check (without modifying)
black --check src/ tests/

# Format the codebase
black src/ tests/

# Run gd-tools itself
gd-tools --version
gd-tools --help
gd-tools doctor
```

### Before Committing
```bash
# Run all pre-commit checks: lint, format check, and tests
ruff check src/ tests/ && black --check src/ tests/ && CI=true pytest
```

## Testing Requirements

### Unit Testing
- Every source code module (`.py` files in `src/gd_tools/`) must have corresponding tests.
- **Tests are only required for source code.** Configuration files (`.toml`, `.json`, `.yaml`), documentation (`.md`), and other non-code assets do NOT require tests.
- Use `pytest` fixtures for setup/teardown.
- Mock external dependencies (Godot binary, GUT subprocess, network requests, file system).
- Test both success and failure cases.
- Test exit codes (0 = success, 1 = failure, 2 = config error).

### Integration Testing
- Test complete CLI command flows (e.g., `gd-tools lint`, `gd-tools test`).
- Use fixture GDScript files for lint/format/coverage tests.
- Mock Godot subprocess invocations where possible.
- Test config loading with real `gd-tools.toml` fixtures.

### End-to-End Testing
- Full `gd-tools test --coverage` run on a sample Godot project with GUT.
- Verify JUnit XML and coverage JSON are produced correctly.
- Test cross-platform path handling (Windows, macOS, Linux).

## Code Review Process

### Self-Review Checklist
Before requesting review:

1. **Functionality**
   - Feature works as specified
   - Edge cases handled
   - Error messages are actionable with fix hints

2. **Code Quality**
   - Follows style guide (`code_styleguides/python.md`)
   - DRY principle applied
   - Clear variable/function names (snake_case for Python)
   - Appropriate comments (explain *why*, not *what*)

3. **Testing**
   - Unit tests comprehensive
   - Integration tests pass
   - Coverage adequate (>80% line, >70% branch)

4. **Security**
   - No hardcoded secrets
   - Input validation present
   - Safe subprocess invocation (no shell injection)
   - Safe file path handling

5. **Performance**
   - Lark parsing efficient for large projects
   - Subprocess invocation minimized
   - No unnecessary file I/O

## Commit Guidelines

### Message Format
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting, missing semicolons, etc.
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `test`: Adding missing tests
- `chore`: Maintenance tasks

### Examples
```bash
git commit -m "feat(config): Implement gd-tools.toml loading and validation"
git commit -m "fix(godot): Correct Godot 4.6 version detection"
git commit -m "test(coverage): Add tests for plan generator branch detection"
git commit -m "docs(prd): Update coverage architecture section"
```

## Definition of Done

A task is complete when:

1. All source code implemented to specification
2. Unit tests written and passing (source code only)
3. Code coverage meets project requirements (>80% line, >70% branch)
4. Documentation complete (if applicable)
5. Code passes all configured linting and static analysis checks (`ruff`, `black`)
6. Implementation notes added to `plan.md`
7. Changes committed with proper message
8. Git note with task summary attached to the commit

## Emergency Procedures

### Critical Bug in Published Release
1. Create hotfix branch from main
2. Write failing test for bug
3. Implement minimal fix
4. Test thoroughly
5. Bump patch version, publish to PyPI
6. Document in plan.md

### Release Failure (PyPI)
1. Verify package builds: `python -m build`
2. Run `twine check dist/*`
3. Test on TestPyPI first
4. If corruption: yank the release on PyPI
5. Document incident and update release process

## Deployment Workflow

### Pre-Release Checklist
- [ ] All tests passing (`CI=true pytest`)
- [ ] Coverage >80% line, >70% branch
- [ ] No linting errors (`ruff check`)
- [ ] No formatting issues (`black --check`)
- [ ] `pyproject.toml` metadata correct
- [ ] Package builds (`python -m build`)
- [ ] `twine check` passes
- [ ] Tested on TestPyPI

### Release Steps
1. Merge all feature branches to main
2. Tag release with version (`git tag v0.1.0`)
3. Build package: `python -m build`
4. Upload to TestPyPI: `twine upload --repository testpypi dist/*`
5. Verify TestPyPI install works
6. Upload to PyPI: `twine upload dist/*`
7. Verify `pip install gd-tools` works
8. Create GitHub release with release notes

### Post-Release
1. Monitor PyPI download stats
2. Check for issue reports
3. Gather user feedback
4. Plan next iteration

## Continuous Improvement

- Review workflow weekly
- Update based on pain points
- Document lessons learned
- Optimize for user happiness
- Keep things simple and maintainable

</protect>
