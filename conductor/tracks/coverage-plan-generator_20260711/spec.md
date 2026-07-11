<protect>
# Track 9: Coverage Plan Generator

## Overview

The Coverage Plan Generator is the Python-side component of the hybrid coverage architecture (Architecture C). It parses GDScript source files using `gdtoolkit`'s Lark parser, walks the resulting AST to identify executable statements and branch points, and emits an instrumentation plan JSON file. This plan is consumed by the GDScript runtime tracker (Track 10) and pre/post-run hooks (Track 11) to instrument code coverage tracking.

**Phase**: 3 — MVP2  
**Effort**: 3-4 days  
**Risk**: MEDIUM-HIGH (Lark AST traversal, statement classification)  
**Dependencies**: Track 0 (spike — completed), Track 2 (config excludes — completed)

## Functional Requirements

### FR-1: Data Structures

The module defines three dataclass-based structures representing the plan:

- `CoveragePlan` — top-level container with `version` (int, =1), `generated_by` (str), `files` (list[FilePlan])
- `FilePlan` — per-file entry with `file_id` (int, sequential 0-indexed), `path` (str, `res://` prefixed), `source_hash` (str, `sha256:` prefixed), `lines` (list[LinePlan])
- `LinePlan` — per-trackable-point entry with `line` (int, 1-indexed), `id` (int, unique within file), `type` ("statement" | "branch"), `branch_type` (str | None)

### FR-2: Statement Classification

The generator classifies GDScript AST nodes into three categories:

**Tracked as statements:**
- `expr_stmt`, `return_stmt`, `func_var_assigned`, `func_var_typed_assgnd`, `func_var_inf`, `break_stmt`, `continue_stmt`

**Tracked as branches:**
- `if_branch` → `if_true`
- `elif_branch` → `elif_true`
- `else_branch` → `if_false`
- `while_stmt` → `loop_body`
- `for_stmt` → `loop_body`
- `for_stmt_typed` → `loop_body`
- `match_branch` → `match_case`

**Not tracked (declarative/skip):**
- `pass_stmt`, `breakpoint_stmt` (skip)
- `const_stmt`, `class_var_stmt`, `signal_stmt`, `enum_stmt`, `func_def`, `static_func_def`, `extends_stmt`, `classname_stmt` (declarative)
- `func_var_empty`, `func_var_typed` (declarations without assignment)

### FR-3: AST Traversal

- Uses `gdtoolkit.parser.parse(source, gather_metadata=True)` to obtain a Lark AST tree.
- Implements a `CoverageVisitor` class subclassing `lark.visitors.Visitor` with methods per node type.
- Each visitor method calls `_add_point(tree, type, branch_type)` which extracts `tree.meta.line` and assigns the next sequential ID via a per-file counter.
- For `if_stmt`, iterates children to find `if_branch`, `elif_branch`, and `else_branch` nodes.
- For `match_stmt`, iterates `match_branch` children.
- Traversal order does not affect plan correctness (it only matters for instrumentation in Track 11).

### FR-4: File Discovery

- Reuses the existing `discover_gd_files(path, excludes)` function from `src/gd_tools/file_discovery.py` (extracted in Track 5).
- Filters out test directories from coverage targets using a one-line filter in `plan_generator.py` (files in `test_dirs` are excluded from coverage).
- Respects coverage excludes from `CoverageConfig` (defaults: `addons`, `.godot`, `.gd-tools`, `.git`).

### FR-5: Plan JSON I/O

- `write_plan_json(plan, output_path) -> None` — serializes a `CoveragePlan` to JSON file.
- `read_plan_json(path) -> CoveragePlan` — deserializes JSON to `CoveragePlan` object. Raises `CoveragePlanError` (already defined in `errors.py`, exit_code=2) if the file is missing, malformed, or schema-invalid.
- JSON structure follows TDD §5.1 data contract exactly, including `file_id` field.

### FR-6: Source Hashing

- Each file entry includes a `source_hash` field computed as SHA-256 of the file's raw source content.
- Hash is prefixed with `sha256:` in the JSON output.
- Used for staleness detection: if source changes, the plan is regenerated.

### FR-7: Fixture Generation Script

- Implements `tools/generate_expected_plans.py` — a utility script that regenerates expected plan JSON fixtures from the `.gd` test fixtures.
- Run manually after modifying GDScript fixtures. Output must be manually verified before committing.

## Non-Functional Requirements

### NFR-1: Performance
- Plan generation for a 100-file project must complete in <1 second.

### NFR-2: Code Quality
- Type hints on all public functions.
- Docstrings on all public functions.
- Passes `ruff check` and `black --check`.
- Test coverage >80% line, >70% branch for `plan_generator.py`.

### NFR-3: Error Handling
- `read_plan_json` raises `CoveragePlanError` for: missing file, invalid JSON, schema mismatch (wrong version, missing required fields).
- Parse errors from `gdtoolkit.parser` propagate as-is (syntax errors in source .gd files are not the plan generator's responsibility to handle gracefully — they indicate broken source code).

## Acceptance Criteria

1. **AC-1**: `simple.gd` fixture generates correct line IDs with no branch entries.
2. **AC-2**: `branches.gd` fixture generates correct `if_true`, `elif_true`, and `if_false` branch IDs.
3. **AC-3**: `loops.gd` fixture generates correct `loop_body` branch IDs for `for`, `while`, and `for_typed`.
4. **AC-4**: `match_stmt.gd` fixture generates correct `match_case` branch IDs for each match branch.
5. **AC-5**: `nested.gd` fixture generates correct branch IDs for deeply nested control flow.
6. **AC-6**: `edge_cases.gd` fixture handles: pass (not tracked), break (tracked), continue (tracked), ternary return (tracked as return_stmt), signal/enum (not tracked), empty function (no lines).
7. **AC-7**: Generated plan JSON matches the schema in TDD §5.1, including `file_id`, `source_hash`, and `branch_type` fields.
8. **AC-8**: `addons/` directory is excluded from coverage by default.
9. **AC-9**: `source_hash` is included for each file with `sha256:` prefix.
10. **AC-10**: Performance benchmark confirms <1s for a 100-file project.
11. **AC-11**: `read_plan_json` raises `CoveragePlanError` on invalid input.
12. **AC-12**: `tools/generate_expected_plans.py` regenerates all 6 expected plan JSON fixtures.

## Out of Scope

- GDScript runtime tracker implementation (Track 10)
- Pre-run / post-run hooks for GUT integration (Track 11)
- Coverage data JSON parsing/reporting (Track 12)
- HTML/text coverage report generation (Track 12)
- CLI command wiring (`gd-tools coverage` subcommand — Track 13)
- Actual code instrumentation (modifying .gd files with `hit()` calls — Track 11)
- Coverage threshold enforcement / CI exit codes (Track 13)
</protect>
