# Product Guidelines

## 1. Prose & Documentation Style

### 1.1 Voice and Tone
- **Technical and precise.** Write for developers who value accuracy over hand-holding.
- **Direct.** No filler phrases ("In this section, we will..."). State what the thing does, then how.
- **Active voice.** "The CLI invokes Godot" — not "Godot is invoked by the CLI."
- **Em-dash asides.** Use em-dashes (—) for parenthetical clarifications, matching the established PRD/ROADMAP style.

### 1.2 Structure
- **Numbered sections** with clear hierarchy (`## 1.`, `### 1.1`).
- **Tables for structured data.** Use Markdown tables for command references, option lists, dependency listings, and comparison matrices — as seen throughout the PRD.
- **ASCII diagrams** for architecture and flow visualization. Keep them within 80-column width where possible.
- **Code blocks** with language tags for all examples: `gdscript`, `python`, `toml`, `json`, `bash`, `yaml`.
- **Short paragraphs.** One idea per paragraph. Break long explanations into bulleted or numbered lists.

### 1.3 Terminology
- Use the glossary terms from PRD §18 consistently (GUT, gdtoolkit, Lark, Architecture C, instrumentation plan, LCOV, Cobertura, JUnit XML).
- Refer to the tool as `gd-tools` (with backticks in prose, without in titles).
- Refer to the config file as `gd-tools.toml`.

---

## 2. Terminal Output Design

### 2.1 Rich & Colorful Output
The CLI uses the `rich` library for terminal output. Output should be:

- **Structured.** Use `rich.table.Table` for tabular data (test results, coverage summaries, doctor diagnostics).
- **Colored.** Semantic color coding:
  - Green = pass / covered / success
  - Red = fail / uncovered / error
  - Yellow = warning / partial coverage
  - Cyan = info / headers
  - Dim/gray = secondary info, file paths
- **Progress-aware.** Use `rich.progress` or spinners for long-running operations (GUT test runs, coverage instrumentation, GUT download).
- **Readable.** Human-friendly output by default; machine-readable via flags (`--report-format json`, `--junit-xml`).

### 2.2 Output Conventions
- **Exit codes are the contract.** 0 = success, 1 = test/lint/format failure or coverage below threshold, 2 = environment/config error. Document and enforce these consistently (PRD §15).
- **No interactive prompts in CI mode.** When `--non-interactive` is set or stdout is not a TTY, never block on user input.
- **Errors to stderr, results to stdout.** Keep stdout clean for piping.

---

## 3. Naming Conventions

Follow the conventions established in the PRD throughout the codebase:

| Context | Convention | Examples |
|---------|-----------|----------|
| CLI commands & flags | `kebab-case` | `gd-tools test`, `--junit-xml`, `--report-format` |
| Python modules & functions | `snake_case` | `test_runner.py`, `run_tests()`, `find_godot()` |
| Python classes | `PascalCase` | `Config`, `GodotInfo`, `TestResult`, `LintResult` |
| Python constants | `UPPER_SNAKE_CASE` | `DEFAULT_EXCLUDES`, `GUT_VERSION_MAP` |
| GDScript classes | `PascalCase` | `_GDTCoverage`, `GDTTracker` |
| GDScript functions | `snake_case` | `hit()`, `get_data()`, `set_active()` |
| GDScript variables | `snake_case` | `file_id`, `line_id`, `hit_count` |
| Config keys (TOML) | `snake_case` | `min_percent`, `output_dir`, `test_dirs` |
| Environment variables | `UPPER_SNAKE_CASE` | `GD_TOOLS_COVERAGE_PLAN`, `GODOT_BIN` |

---

## 4. Error Messages

### 4.1 Actionable Errors with Fix Hints
Every error message must be **actionable** — it tells the user not just what went wrong, but how to fix it.

**Structure:**
```
[Error] <What happened>

  Cause: <Why it happened>
  Fix:   <Concrete steps to resolve>
```

**Examples (from PRD):**
- Godot not found → "Godot binary not found. Tried: config, $GODOT_BIN, PATH, common locations. Install Godot 4.5+ from https://godotengine.org and set GODOT_BIN or add to PATH."
- Godot version too old → "Godot 4.4.1 detected, but gd-tools requires 4.5+. Upgrade at https://godotengine.org."
- GUT not installed → "GUT not found at addons/gut/gut.gd. Run `gd-tools init` to install, or see manual instructions: https://github.com/bitwes/Gut."

### 4.2 Principles
- **Name the thing that's missing.** "Godot binary not found" — not "Error occurred."
- **Include the attempted resolution.** For detection chains, list what was tried.
- **Provide a concrete fix.** A command to run, a URL to visit, or a config key to set.
- **Distinguish errors from warnings.** Errors block execution (exit 1 or 2); warnings continue with a note (e.g., GUT version mismatch).

---

## 5. Code Documentation

### 5.1 Python (gd-tools itself)
- **Docstrings** on all public functions and classes (Google or NumPy style — pick one and be consistent).
- **Type hints** on all function signatures (the project targets Python 3.10+).
- **Module-level docstrings** explaining the module's purpose and key TDD/PRD references.

### 5.2 GDScript (coverage addon)
- **Comments** explaining non-obvious instrumentation logic.
- **`@onready` / autoload annotations** documented where behavior depends on Godot lifecycle.

### 5.3 Inline Comments
- Comment *why*, not *what*. The code shows what it does; comments explain intent.
- Reference PRD/TDD sections where relevant: `# See PRD §9 for detection chain`.

---

## 6. Contributor Experience

### 6.1 Onboarding
- `README.md` provides a quick start: install, init, first command.
- `docs/CONTRIBUTING.md` covers dev setup, code style (ruff, black), testing requirements, and PR process.
- `gd-tools doctor` lets contributors self-diagnose their environment.

### 6.2 Code Quality Gates
- **Lint:** `ruff` on all Python code (gd-tools's own code).
- **Format:** `black` on all Python code.
- **Tests:** `pytest` with ≥80% line coverage, ≥70% branch coverage (per TESTING_STRATEGY.md).
- **Pre-commit:** These checks should run before commits land (Track 15 / future work).

---

## 7. Accessibility & Internationalization

- **Color is supplementary, not load-bearing.** All information conveyed by color must also be conveyed by text (✓/✗ symbols, exit codes, status words). Colorblind users must get full information.
- **No required interactive prompts.** Every interactive flow has a `--non-interactive` escape hatch for CI and scripting.
- **ASCII-only terminal output.** Avoid emoji in CLI output unless explicitly requested; use text symbols (✓/✗, [OK]/[FAIL]).
