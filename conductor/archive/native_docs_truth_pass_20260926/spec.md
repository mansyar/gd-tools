# Native Documentation Truth Pass

**Track ID:** `native_docs_truth_pass_20260926`
**Type:** Bug
**Status:** Draft — approved for planning
**Origin:** Surfaced during a Conductor codebase review of `main` @ `afb58c2`, after `native_scene_integration_20260925` completed. Closes the gap between the shipped native runtime and every document that describes the product.

> **Type note.** This track was drafted as a documentation chore and reclassified as a Bug during planning. The reclassification reflects R1: `docs/USER_GUIDE.md` states a retention guarantee that the code does not honor, and a user-created directory can be deleted. That is a correctness defect, and the documentation corrections in R2–R6 exist to describe the fixed behavior rather than to paper over it. The scope itself is unchanged.

## 1. Problem

Two substantial tracks completed on 2026-09-25 — the native test runtime foundation and native scene/resource integration — adding 3,005 lines of new code (1,544 GDScript, 1,461 Python) and establishing a new default execution path. The documentation was never updated to match. Four concrete failures result.

### 1.1 A documented safety guarantee is false

`docs/USER_GUIDE.md:578-580` states that only "directories carrying this tool's own run markers are pruned." `_is_run_directory` (`src/gd_tools/native_test/artifacts.py:231-235`) also returns `True` for any directory containing a `native/` or `preflight/` subdirectory:

```python
def _is_run_directory(path: Path) -> bool:
    if (path / "artifacts.json").exists():
        return True
    return (path / "native").is_dir() or (path / "preflight").is_dir()
```

A directory a user created under `.gd-tools/artifacts/` that happens to contain a `native/` or `preflight/` subfolder is therefore passed to `shutil.rmtree` (`artifacts.py:228`) with no `onerror` handler. The same overstated claim is repeated in two docstrings — `publish_artifact_index` at `artifacts.py:111-112` and `_prune_old_runs` at `artifacts.py:218-219`.

The existing test `test_prune_keeps_directories_that_are_not_runs` (`tests/unit/test_native_artifacts.py:139-157`) creates a user directory holding only `notes.txt`. It passes, and it does not cover the failing case.

### 1.2 README describes a product that is no longer the default

`README.md` presents GUT as the framework `gd-tools test` drives. Every one of the following is now inaccurate or incomplete:

| Location | Current claim |
|----------|---------------|
| `README.md:16-20` | "It wraps mature, community-trusted tools (GUT for testing, gdtoolkit for linting and formatting)" |
| `README.md:29` | "`gd-tools init` gets a project fully set up ... GUT installed, coverage addon deployed" |
| `README.md:32` | "gdlint, gdformat, and GUT continue to work if invoked directly" |
| `README.md:67-71` | "`gd-tools init` installs GUT, deploys the coverage addon, and creates ... (`.gutconfig.json`, ...)" |
| `README.md:77` | "`gd-tools init` — Bootstrap a Godot project -- install GUT, deploy coverage addon" |
| `README.md:78` | "`gd-tools doctor` — Diagnose ... Godot, GUT, coverage addon, tooling" |
| `README.md:79` | "`gd-tools test` — Run GUT tests with optional coverage" |
| `README.md:84` | "`gd-tools version` — Display versions of all gd-tools components (gd-tools, Godot, GUT, gdtoolkit, Python)" |
| `README.md:172-195` | `[test]` config sample omits `runtime`, `timeout_seconds`, `retries`, and `tags`, all of which exist in `config.py:48-73` |
| `README.md:230` | `pytest --cov=src/gd_tools` — `workflow.md` and `pyproject.toml` use `--cov=gd_tools`; the `CI=true` prefix the project workflow requires is also missing |
| `README.md:247` | GUT described as "the GDScript test framework that `gd-tools test` drives" |

The file contains zero mentions of `GdToolsTest`, `--runtime`, `--tag`, `--test-timeout`, `--with-gut`, or the artifact system. It is the first thing a new user reads.

### 1.3 ARCHITECTURE.md documents the coverage system only

`docs/ARCHITECTURE.md` is 520 lines covering Architecture C, the instrumentation plan, `coverage.gd`, the hooks, and the reporter. A grep for `GdToolsTest|gd_tools_test|native_test` across the file returns zero matches. The entire native runtime — five GDScript addon scripts and six Python modules — is architecturally undocumented.

### 1.4 Status headers are stale by up to two months

| Location | Current text |
|----------|--------------|
| `docs/ROADMAP.md:3-5` | "Version: 0.2.0 (draft)", "Date: 2026-07-14" |
| `docs/ROADMAP.md:1553` | §8 header reads "Status: Planning" while Phases 1 and 2 are checked off and marked Delivered |
| `docs/TESTING_STRATEGY.md:3-5` | "Version: 0.1.0 (draft)", "Status: Phase 4 In Progress — Test Suite Implemented (Track 14)", against ~1,033 existing tests |

## 2. Requirements

### R1 — Retention recognizes only unambiguous run markers

`_is_run_directory` must stop treating a bare `native/` or `preflight/` subdirectory as proof of tool ownership. A run must be identified by a marker this tool writes and that a user directory cannot plausibly contain.

Constraints, each of which rules out the simpler alternative:

- A run that crashes **before** publishing its index must remain prunable. Therefore the marker must be written at run *start*, not at publication time.
- Run directories created by earlier versions — identified only by `artifacts.json` — must remain prunable. Therefore the fix cannot require the new marker exclusively, or pre-existing runs would be stranded under the artifact root indefinitely.
- The current run is never pruned, and symlinks and plain files are never pruned. Both already hold and must be preserved.

The approved design is to accept **either** marker: a start-of-run sentinel, or `artifacts.json`.

### R2 — The documented guarantee becomes true

Once R1 lands, `docs/USER_GUIDE.md:578-580` and both docstrings (`artifacts.py:111-112`, `artifacts.py:218-219`) describe actual behavior. No wording is weakened to accommodate the defect, and the user guide gains a statement of what retention does and does not touch.

### R3 — README is native-first

The overview, features table, quick start, `init` description, command summary, configuration sample, and acknowledgements describe the native runtime as the default path and GUT as a selectable legacy runtime. Add a **native vs. GUT capability matrix** so a migrating user can see exactly what each path supports. Correct the test command at `README.md:230` to match `workflow.md`.

### R4 — ARCHITECTURE.md gains a native runtime section

The new section mirrors the structure of the existing coverage documentation: architecture overview, the Python/Godot responsibility boundary, protocol v2 data formats, per-component detail for the five GDScript addon scripts and six Python modules, and design decisions with rationale. ASCII diagrams stay within 80 columns per `product-guidelines.md` §1.

### R5 — Stale status headers are corrected

`docs/ROADMAP.md:3-5`, `docs/ROADMAP.md:1553`, and `docs/TESTING_STRATEGY.md:3-5` are corrected to reflect actual state. Corrections must not advance any roadmap item's completion status.

### R6 — The rest of USER_GUIDE.md is left intact

`docs/USER_GUIDE.md` is currently accurate and is the model the README change copies from. Only the R2 correction and any cross-reference needed for internal consistency are touched.

## 3. Non-functional requirements

| Requirement | Statement |
|-------------|-----------|
| Surgical | `docs/PRD.md` and `docs/ROADMAP_v1.md` are historical records and are not rewritten. The existing coverage half of `ARCHITECTURE.md` is not reorganized — the native section is additive. |
| Honest | No capability is documented that the code does not have. Real limitations — no mocking, no parameterized tests, no parallel execution, no editor plugin — are stated rather than omitted. `USER_GUIDE.md:554-580` already sets this precedent. |
| Tested where required | Per `workflow.md`, only `.py` and `.gd` source changes require tests. R1 is a source change and carries a full Red/Green TDD cycle. R2–R6 are documentation and carry no test obligation. |
| No scope absorption | If R1 uncovers a defect beyond marker recognition, that is a decision point, not work to absorb silently. |

## 4. Acceptance criteria

| # | Criterion |
|---|----------|
| 1 | A directory containing a `native/` or `preflight/` subdirectory but no run marker survives `publish_artifact_index` retention, proven by a test written and confirmed failing before the fix. |
| 2 | A run directory carrying the start-of-run marker but no published index is pruned. |
| 3 | A run directory carrying only `artifacts.json` — the pre-marker shape — is still pruned. |
| 4 | The current run, symlinks, and plain files under the artifact root remain unpruned. |
| 5 | `docs/USER_GUIDE.md` and both `artifacts.py` docstrings state a guarantee that R1 makes true. No wording was weakened to fit existing behavior. |
| 6 | `README.md` names the native runtime as the default and mentions `GdToolsTest`, `--runtime`, `--tag`, `--test-timeout`, `--with-gut`, and the artifact system. |
| 7 | `README.md` contains a native vs. GUT capability matrix, and its `[test]` configuration sample includes `runtime`, `timeout_seconds`, `retries`, and `tags`. |
| 8 | `README.md:230`'s test command matches `workflow.md` — `CI=true` prefix and `--cov=gd_tools`. |
| 9 | `docs/ARCHITECTURE.md` gains a native runtime section with overview, Python/Godot boundary, data formats, per-component detail for all eleven modules, and design decisions. |
| 10 | `docs/ROADMAP.md` and `docs/TESTING_STRATEGY.md` status headers no longer claim pre-native-runtime state. |
| 11 | `ruff check src/ tests/`, `black --check src/ tests/`, and the full `CI=true pytest` suite pass. The ≥80% line / ≥70% branch self-coverage gate is unchanged or better. |
| 12 | `git diff --check` is clean. |

## 5. Out of scope

- **Version bump, changelog, and release.** The native runtime is unreleased — `pyproject.toml` and `CHANGELOG.md` are both at `0.4.0`, tagged 2026-07-16, roughly 2.5 months and +4,702 lines behind `main`. That is a separate track.
- **Retention policy for crashed runs.** Whether a crashed run's artifacts should be *retained* for diagnosis is a product decision, distinct from whether a user directory can be deleted. R1 keeps crashed runs prunable, which is the status quo. Changing that is not this track.
- **Every other review finding** — the unbounded Godot import timeout at `native_test/command.py:115`, the missing engine-log fallback at `native_test/orchestrator.py:217-228`, coverage shard provenance, the two divergent coverage mergers, per-test tags, and the CI coverage gate measuring unit tests only. Each is a candidate for its own track.
- **Rewriting the coverage half of `docs/ARCHITECTURE.md`**, and any content change to `docs/PRD.md` or `docs/ROADMAP_v1.md`.
- **Roadmap item completion.** R5 corrects stale status text; it does not mark Phases 3–5 of the migration roadmap as anything.
- **`docs/CONTRIBUTING.md`.** It is updated only if the implementation discovers it documents CI job layout or a command surface that R3 changes. Per `workflow.md`'s surgical-changes principle, content that was not there is not added.

## 6. Open questions

None. The two decisions that would otherwise block planning were settled before this spec was drafted:

1. **Whether to fix the code or weaken the documentation.** Resolved: fix the code. A user guide that documents a data-loss footgun is not an acceptable outcome, and the fix is a few lines with a test.
2. **How to identify a run unambiguously.** Resolved: a start-of-run sentinel, accepted alongside `artifacts.json`, so neither crashed runs nor pre-existing runs are stranded.

## 7. Notes for the implementer

- **Read before writing.** `tests/unit/test_native_artifacts.py` already contains `test_prune_keeps_directories_that_are_not_runs` (line 139) and the `_write_run` helper (line 49). The new tests extend that file's established style: module docstring, `pytestmark = pytest.mark.unit`, one-line test docstrings, arrange/act/assert.
- **`_write_run` will need updating.** It writes `artifacts.json` only. Once a sentinel exists, helper usage must reflect a real run's shape so existing tests continue to represent production layout rather than passing by accident.
- **The marker's write site matters.** `NativeArtifactLayout.create` is a pure constructor exercised by `test_layout_uses_safe_run_scoped_stable_names` (line 18) without filesystem side effects. Writing the marker there would make an unrelated test depend on disk state. The natural site is `native_test/command.py:118`, immediately after layout creation and before `run_native_preflight` at line 120 — early enough that a crash during preflight is still prunable, late enough that a failed `_import_project` at line 115 leaves no directory behind.
- **`artifacts.py` coverage is currently 83% line / 75% branch** (recorded at the Phase 7 checkpoint of `native_scene_integration_20260925`). New branches must not pull it below the gate.
- **Correction 5 is a source file.** Editing the two `artifacts.py` docstrings means the track's final quality gate covers Python, not only Markdown.
