# Track 12: Coverage Reporter

## Overview

The Coverage Reporter module reads instrumentation plan JSON (from Track 9) and coverage data JSON (from Track 11), cross-references them by `file_id` to compute line and branch coverage metrics, and generates reports in four formats: HTML, LCOV, Cobertura XML, and terminal (Rich table). It also enforces a `--min N` threshold check that exits with code 1 if coverage falls below the specified percentage.

This module is the final reporting layer of the hybrid coverage system (Architecture C: Python plan gen -> GDScript runtime instrumentation -> Python reporting).

## Functional Requirements

### FR-1: Data Ingestion (`reporter.py`)

- **FR-1.1:** `read_coverage_json(path: Path) -> CoverageData` must read coverage JSON files matching the actual Track 11 runtime format (`file_id: int` + `hits: dict[str, int]` with string keys). It must NOT require a `path` field in the JSON.
- **FR-1.2:** `CoverageData` and `FileCoverage` dataclasses must store `file_id: int` (not `path: str` as originally specified in TDD section 3.11). Path resolution happens at report-generation time by cross-referencing the plan.
- **FR-1.3:** `merge_coverage_data(files: list[Path]) -> CoverageData` must merge multiple coverage data files (for parallel CI shards) by summing hit counts per `file_id`/`line_id`.
- **FR-1.4:** `read_coverage_json()` must validate the `version` field and raise `CoveragePlanError` on version mismatch.

### FR-2: Coverage Metrics Computation (`reporter.py`)

- **FR-2.1:** `compute_summary(plan: CoveragePlan, data: CoverageData) -> CoverageSummary` must compute overall coverage across all files.
- **FR-2.2:** `compute_file_summary(file_plan: FilePlan, file_data: FileCoverage) -> FileSummary` must compute per-file coverage breakdown.
- **FR-2.3:** **Line coverage:** `line_rate = covered_lines / total_executable_lines`. A line is "covered" if hit count > 0. "Executable lines" are all lines in the plan (type `statement` or `branch`).
- **FR-2.4:** **Branch coverage:** `branch_rate = covered_branches / total_branch_points`. Branch types: `if_true`, `if_false`, `elif_true`, `loop_body`, `match_case`. A branch is "covered" if hit count > 0.
- **FR-2.5:** `FileSummary` must include `uncovered_lines: list[int]` (line numbers with zero hits).
- **FR-2.6:** Files present in the plan but with zero coverage data (not in `CoverageData.files` or all hits = 0) must still appear in summaries with 0% coverage. Zero-coverage files must NOT be silently omitted.
- **FR-2.7:** Source hash mismatch between plan and coverage data (if trackable) should emit a warning but not fail.

### FR-3: Report Dispatch (`reporter.py`)

- **FR-3.1:** `generate_report(plan: CoveragePlan, data: CoverageData, output_dir: Path, format: str = "html", min_threshold: float | None = None) -> ReportResult` must dispatch to the format-specific reporter.
- **FR-3.2:** Supported formats: `"html"`, `"lcov"`, `"cobertura"`, `"terminal"`.
- **FR-3.3:** If `min_threshold` is set and the overall line coverage rate (0.0-1.0) is below the threshold, the function must raise `CoverageThresholdError` (exit code 1). Threshold defaults to line coverage.
- **FR-3.4:** `ReportResult` dataclass must include: `output_path: Path`, `format: str`, `summary: CoverageSummary`, `file_summaries: list[FileSummary]`, `threshold_met: bool`.

### FR-4: HTML Reporter (`html_reporter.py`)

- **FR-4.1:** `generate_html_report(plan: CoveragePlan, data: CoverageData, output_dir: Path) -> Path` must generate an `index.html` and one HTML page per file.
- **FR-4.2:** **Index page:** Summary table with columns: File, Lines (found/hit), Line %, Branches (found/hit), Branch %. Sortable columns. Overall summary bar at top.
- **FR-4.3:** **Per-file page:** Source code listing with line numbers. Covered lines highlighted green, uncovered lines highlighted red, partial-branch lines highlighted yellow.
- **FR-4.4:** CSS and JS must be bundled inline (no external dependencies). No CDN links.
- **FR-4.5:** Jinja2 templates stored as separate `.html` files in `src/gd_tools/coverage/templates/` (loaded via `FileSystemLoader` or `PackageLoader`).
- **FR-4.6:** File paths in the report must use the `res://` convention from the plan.

### FR-5: LCOV Reporter (`lcov_reporter.py`)

- **FR-5.1:** `generate_lcov_report(plan: CoveragePlan, data: CoverageData, output_path: Path) -> Path` must output a valid LCOV `.info` file.
- **FR-5.2:** Format: `TN:`, `SF:<res_path>`, `DA:<line>,<hit_count>`, `BRDA:<line>,<block>,<branch>,<taken>`, `BRF:<total_branches>`, `BRH:<hit_branches>`, `LF:<total_lines>`, `LH:<hit_lines>`, `end_of_record`.
- **FR-5.3:** Must be compatible with codecov.io, coveralls, and `genhtml`.
- **FR-5.4:** Zero-coverage files must be included (with all `DA` entries showing hit_count=0).

### FR-6: Cobertura Reporter (`cobertura_reporter.py`)

- **FR-6.1:** `generate_cobertura_report(plan: CoveragePlan, data: CoverageData, output_path: Path) -> Path` must output valid Cobertura XML.
- **FR-6.2:** Structure: `<coverage>` root with `line-rate` and `branch-rate` attributes, `<packages>`, `<package>`, `<classes>`, `<class>` per file, `<lines>` with `<line>` elements.
- **FR-6.3:** Each `<line>` must have: `number`, `hits`, `branch` (true/false), `condition-coverage` (for branch lines).
- **FR-6.4:** Compatible with Jenkins and GitLab CI coverage parsers.

### FR-7: Terminal Reporter (`terminal_reporter.py`)

- **FR-7.1:** `generate_terminal_report(plan: CoveragePlan, data: CoverageData) -> str` must return a formatted Rich table string.
- **FR-7.2:** Table columns: File, Lines Found, Lines Hit, Line %, Branches Found, Branches Hit, Branch %.
- **FR-7.3:** Overall summary at the bottom: total line rate and branch rate.
- **FR-7.4:** Color coding: green for >=80% coverage, yellow for 50-79%, red for <50%. (Terminal colors only; output remains ASCII-compatible per product guidelines.)
- **FR-7.5:** Zero-coverage files must appear in the table.

## Non-Functional Requirements

### NFR-1: Code Quality
- Follow existing code style (ruff + black, line length 88).
- All source code must have >80% line coverage and >70% branch coverage.
- Type hints required on all public functions.
- Error messages follow the Cause/Fix format defined in product-guidelines.md.

### NFR-2: Performance
- HTML report generation for 100-file projects should complete in <2 seconds.
- LCOV/Cobertura generation for 100-file projects should complete in <1 second.

### NFR-3: Compatibility
- Python 3.10+ (match project minimum).
- Jinja2 for HTML templating (already in tech-stack).
- Rich for terminal output (already in tech-stack).
- xml.etree.ElementTree for Cobertura XML (stdlib, no external dependency).

### NFR-4: Test Fixtures
- Existing test fixtures at `tests/fixtures/coverage_data/` must be updated to use the actual Track 11 runtime format (`file_id` + `hits` with string keys) instead of `path`.
- Corresponding plan fixtures must be created or already exist at `tests/fixtures/coverage_plans/` to enable cross-referencing.

## Acceptance Criteria

1. **AC-1:** HTML report shows correct coverage percentages (verified against computed metrics from mock data).
2. **AC-2:** HTML source view highlights covered lines green, uncovered lines red, partial-branch lines yellow.
3. **AC-3:** LCOV output contains valid `SF:`, `DA:`, `BRDA:`, `BRF:`, `BRH:`, `LF:`, `LH:`, `end_of_record` records.
4. **AC-4:** Cobertura XML is well-formed, has `<coverage>` root with `line-rate`/`branch-rate`, `<class>` per file, `<line>` with `hits`.
5. **AC-5:** Terminal output is a readable Rich table with per-file and overall summaries, color-coded.
6. **AC-6:** `--min 0.80` raises `CoverageThresholdError` when line rate is 0.79; does NOT raise when line rate is 0.80+.
7. **AC-7:** Files in the plan with zero coverage data appear in ALL report formats (HTML, LCOV, Cobertura, terminal) -- not silently omitted.
8. **AC-8:** Branch coverage is computed correctly for: `if_true`/`if_false`, `elif_true`, `loop_body`, `match_case` branch types.
9. **AC-9:** `merge_coverage_data()` correctly sums hit counts across multiple data files for the same `file_id`/`line_id`.
10. **AC-10:** Test fixtures at `tests/fixtures/coverage_data/` use the `file_id` + `hits` format matching Track 11 runtime output.

## Out of Scope

- CLI command wiring (Track 13: CLI Integration will connect `coverage report`, `coverage merge`, `coverage show` commands to these reporter functions).
- Coverage data collection (handled by Track 11 hooks).
- Plan generation (handled by Track 9).
- Trend/historical reporting (future enhancement beyond MVP2).
- Diff coverage (only changed lines) -- future enhancement.
- Custom report themes or templates -- future enhancement.
- Integration with external CI services beyond standard format compliance (no direct API uploads to codecov.io/coveralls; just generating compatible files).
