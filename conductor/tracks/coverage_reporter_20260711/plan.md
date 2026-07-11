<protect>
# Track 12: Coverage Reporter -- Implementation Plan

## Phase 1: Test Fixtures & Data Models

- [x] Task: Read `spec.md` and `workflow.md` for context before starting this phase
- [x] Task: Update existing test fixtures to Track 11 runtime format [36c648f]
    - [ ] Update `tests/fixtures/coverage_data/full_coverage.json` -- replace `"path"` key with `"file_id"` + `"hits"` (string keys)
    - [ ] Update `tests/fixtures/coverage_data/partial_coverage.json` -- same format change
    - [ ] Update `tests/fixtures/coverage_data/zero_coverage.json` -- same format change
    - [ ] Create or verify `tests/fixtures/coverage_plans/` directory with matching plan fixtures (containing `file_id`, `path`, `source_hash`, `lines`)
- [ ] Task: Write tests for data models and JSON I/O (Red)
    - [ ] Test `CoverageData` and `FileCoverage` dataclass construction and field access
    - [ ] Test `read_coverage_json()` with valid fixture files (full, partial, zero)
    - [ ] Test `read_coverage_json()` raises `CoveragePlanError` on version mismatch
    - [ ] Test `read_coverage_json()` handles string keys in `hits` dict correctly
    - [ ] Test `merge_coverage_data()` sums hit counts across multiple files for same `file_id`/`line_id`
    - [ ] Test `merge_coverage_data()` with empty list returns empty `CoverageData`
- [ ] Task: Implement data models and JSON I/O (Green)
    - [ ] Implement `CoverageData`, `FileCoverage` dataclasses (with `file_id: int`, NOT `path: str`)
    - [ ] Implement `CoverageSummary`, `FileSummary`, `ReportResult` dataclasses
    - [ ] Implement `read_coverage_json(path: Path) -> CoverageData` with version validation
    - [ ] Implement `merge_coverage_data(files: list[Path]) -> CoverageData`
- [ ] Task: Conductor - User Manual Verification 'Test Fixtures & Data Models' (Protocol in workflow.md)

## Phase 2: Coverage Metrics Computation

- [ ] Task: Read `spec.md` and `workflow.md` for context before starting this phase
- [ ] Task: Write tests for coverage computation (Red)
    - [ ] Test `compute_file_summary()` with full coverage (100% line, 100% branch)
    - [ ] Test `compute_file_summary()` with partial coverage (e.g., 15/20 lines = 75% line rate)
    - [ ] Test `compute_file_summary()` with zero coverage (0% line, 0% branch)
    - [ ] Test `compute_file_summary()` correctly identifies `uncovered_lines` list
    - [ ] Test `compute_file_summary()` branch coverage for `if_true`/`if_false` pair
    - [ ] Test `compute_file_summary()` branch coverage for `elif_true`, `loop_body`, `match_case`
    - [ ] Test `compute_summary()` aggregates across multiple files correctly
    - [ ] Test `compute_summary()` includes zero-coverage files (not omitted)
    - [ ] Test `compute_summary()` with file in plan but missing from coverage data (all hits = 0)
- [ ] Task: Implement coverage computation (Green)
    - [ ] Implement `compute_file_summary(file_plan: FilePlan, file_data: FileCoverage) -> FileSummary`
    - [ ] Implement `compute_summary(plan: CoveragePlan, data: CoverageData) -> CoverageSummary`
    - [ ] Handle case where file is in plan but not in coverage data (treat as 0 hits)
- [ ] Task: Conductor - User Manual Verification 'Coverage Metrics Computation' (Protocol in workflow.md)

## Phase 3: Report Dispatch & Threshold Check

- [ ] Task: Read `spec.md` and `workflow.md` for context before starting this phase
- [ ] Task: Write tests for report dispatch and threshold (Red)
    - [ ] Test `generate_report()` with `format="terminal"` returns `ReportResult` with correct format
    - [ ] Test `generate_report()` with `format="lcov"` dispatches to LCOV reporter
    - [ ] Test `generate_report()` with `format="cobertura"` dispatches to Cobertura reporter
    - [ ] Test `generate_report()` with `format="html"` dispatches to HTML reporter
    - [ ] Test `generate_report()` with unsupported format raises appropriate error
    - [ ] Test `generate_report()` with `min_threshold=0.80` and line_rate=0.79 raises `CoverageThresholdError`
    - [ ] Test `generate_report()` with `min_threshold=0.80` and line_rate=0.80 does NOT raise
    - [ ] Test `generate_report()` with `min_threshold=None` never raises threshold error
    - [ ] Test `ReportResult` contains correct `summary`, `file_summaries`, `threshold_met` fields
- [ ] Task: Implement report dispatch and threshold (Green)
    - [ ] Implement `generate_report()` dispatching to format-specific reporters
    - [ ] Implement threshold check logic (compare `line_rate` against `min_threshold`, raise `CoverageThresholdError` if below)
    - [ ] Set `threshold_met` field on `ReportResult`
    - [ ] Initially wire to terminal reporter only (others implemented in later phases); use placeholder/stub calls that will be replaced
- [ ] Task: Conductor - User Manual Verification 'Report Dispatch & Threshold Check' (Protocol in workflow.md)

## Phase 4: LCOV Reporter

- [ ] Task: Read `spec.md` and `workflow.md` for context before starting this phase
- [ ] Task: Write tests for LCOV reporter (Red)
    - [ ] Test output file contains `TN:` record
    - [ ] Test output file contains `SF:<res_path>` for each file in plan
    - [ ] Test output file contains `DA:<line>,<hit_count>` records for all tracked lines
    - [ ] Test output file contains `BRDA:<line>,<block>,<branch>,<taken>` records for branch lines
    - [ ] Test output file contains `BRF:`, `BRH:`, `LF:`, `LH:` summary records per file
    - [ ] Test output file contains `end_of_record` after each file section
    - [ ] Test zero-coverage files are included (all `DA` entries with hit_count=0)
    - [ ] Test LCOV output is valid (parseable, correct record ordering)
- [ ] Task: Implement LCOV reporter (Green)
    - [ ] Implement `generate_lcov_report(plan: CoveragePlan, data: CoverageData, output_path: Path) -> Path`
    - [ ] Generate LCOV records: `TN:`, `SF:`, `DA:`, `BRDA:`, `BRF:`, `BRH:`, `LF:`, `LH:`, `end_of_record`
    - [ ] Resolve file paths from plan via `file_id` cross-reference
    - [ ] Include zero-coverage files
- [ ] Task: Conductor - User Manual Verification 'LCOV Reporter' (Protocol in workflow.md)

## Phase 5: Cobertura Reporter

- [ ] Task: Read `spec.md` and `workflow.md` for context before starting this phase
- [ ] Task: Write tests for Cobertura reporter (Red)
    - [ ] Test output XML is well-formed (parseable by `xml.etree.ElementTree`)
    - [ ] Test root element is `<coverage>` with `line-rate` and `branch-rate` attributes
    - [ ] Test `<class>` element exists for each file in plan
    - [ ] Test `<line>` elements have `number`, `hits`, `branch` attributes
    - [ ] Test branch lines have `condition-coverage` attribute
    - [ ] Test zero-coverage files are included (all `hits=0`)
    - [ ] Test `line-rate` and `branch-rate` values match computed metrics
- [ ] Task: Implement Cobertura reporter (Green)
    - [ ] Implement `generate_cobertura_report(plan: CoveragePlan, data: CoverageData, output_path: Path) -> Path`
    - [ ] Build XML tree: `<coverage>` -> `<packages>` -> `<package>` -> `<classes>` -> `<class>` -> `<lines>` -> `<line>`
    - [ ] Set `line-rate` and `branch-rate` on root and per-class elements
    - [ ] Use `xml.etree.ElementTree` (stdlib)
    - [ ] Include zero-coverage files
- [ ] Task: Conductor - User Manual Verification 'Cobertura Reporter' (Protocol in workflow.md)

## Phase 6: HTML Reporter

- [ ] Task: Read `spec.md` and `workflow.md` for context before starting this phase
- [ ] Task: Create Jinja2 HTML templates
    - [ ] Create `src/gd_tools/coverage/templates/index.html` -- summary table with sortable columns
    - [ ] Create `src/gd_tools/coverage/templates/file.html` -- per-file source view with highlighting
    - [ ] Inline CSS (green/yellow/red classes, table styling, summary bar)
    - [ ] Inline JS (column sorting, no external dependencies)
- [ ] Task: Write tests for HTML reporter (Red)
    - [ ] Test `generate_html_report()` creates `index.html` in output directory
    - [ ] Test `generate_html_report()` creates one HTML file per source file
    - [ ] Test index page contains summary table with file, line %, branch % columns
    - [ ] Test index page shows overall coverage percentages
    - [ ] Test per-file page contains source code with line numbers
    - [ ] Test per-file page has CSS classes: `covered` (green), `uncovered` (red), `partial` (yellow)
    - [ ] Test zero-coverage files appear in index with 0% metrics
    - [ ] Test file paths use `res://` convention
    - [ ] Test HTML output is valid (parseable, no unclosed tags)
- [ ] Task: Implement HTML reporter (Green)
    - [ ] Implement `generate_html_report(plan: CoveragePlan, data: CoverageData, output_dir: Path) -> Path`
    - [ ] Load Jinja2 templates from `templates/` directory
    - [ ] Generate index page with summary table
    - [ ] Generate per-file pages with source highlighting (read source files for line-by-line display)
    - [ ] Apply CSS classes based on coverage status (covered/uncovered/partial-branch)
    - [ ] Include zero-coverage files in index
- [ ] Task: Conductor - User Manual Verification 'HTML Reporter' (Protocol in workflow.md)

## Phase 7: Terminal Reporter

- [ ] Task: Read `spec.md` and `workflow.md` for context before starting this phase
- [ ] Task: Write tests for terminal reporter (Red)
    - [ ] Test `generate_terminal_report()` returns a string (not None)
    - [ ] Test output contains Rich table with columns: File, Lines Found, Lines Hit, Line %, Branches Found, Branches Hit, Branch %
    - [ ] Test output contains overall summary at bottom
    - [ ] Test zero-coverage files appear in table with 0% metrics
    - [ ] Test output includes all files from plan
    - [ ] Test color coding logic (green >=80%, yellow 50-79%, red <50%) -- verify color markers present
- [ ] Task: Implement terminal reporter (Green)
    - [ ] Implement `generate_terminal_report(plan: CoveragePlan, data: CoverageData) -> str`
    - [ ] Build Rich `Table` with coverage columns
    - [ ] Add per-file rows with color-coded percentages
    - [ ] Add overall summary row
    - [ ] Use `rich.console.Console` to render table to string
    - [ ] Include zero-coverage files
- [ ] Task: Conductor - User Manual Verification 'Terminal Reporter' (Protocol in workflow.md)

## Phase 8: Final Integration & Coverage Verification

- [ ] Task: Read `spec.md` and `workflow.md` for context before starting this phase
- [ ] Task: Wire all reporters into `generate_report()` dispatch
    - [ ] Replace any stub/placeholder calls in `generate_report()` with actual reporter implementations
    - [ ] Verify all four formats (html, lcov, cobertura, terminal) work end-to-end via `generate_report()`
- [ ] Task: Run full test suite and verify coverage thresholds
    - [ ] Run `ruff check src/ tests/` -- must pass with no errors
    - [ ] Run `black --check src/ tests/` -- must pass with no changes needed
    - [ ] Run `CI=true pytest` -- all tests must pass
    - [ ] Run `CI=true pytest --cov=src/gd_tools/coverage --cov-report=term-missing` -- verify >80% line coverage and >70% branch coverage for all new modules
    - [ ] Manually verify HTML report renders correctly in a browser (visual spot-check)
    - [ ] Manually verify LCOV output with `lcov --summary` if available, or validate format manually
    - [ ] Manually verify Cobertura XML parses with a standard XML parser
- [ ] Task: Conductor - User Manual Verification 'Final Integration & Coverage Verification' (Protocol in workflow.md)
</protect>
