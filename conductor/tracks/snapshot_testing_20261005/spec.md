# Track Spec: Snapshot Testing in the Native Runtime

- **Track ID:** `snapshot_testing_20261005`
- **Type:** Feature
- **Branch:** `feature/snapshot-testing-20261005`
- **Status:** new

## Overview

Add Jest-style snapshot testing to the native GdToolsTest runtime via a new
`assert_snapshot(value, name)` assertion. Snapshot testing freezes a value's
serialized representation on first run and compares against it on every
subsequent run, giving Godot projects a low-effort regression guard for
complex values, object state, and scene trees — the things that are painful
to hand-write assertions for.

## Background

The runtime already offers targeted assertions (spy, signal, property), but
verifying large composite state (a Dictionary of game data, an inventory
Object, a spawned scene tree) requires verbose manual checks. Snapshot
testing captures the whole state once and diffs it automatically, a proven
pattern from Jest/pytest.

## Functional Requirements

### FR1 — Assertion API

- `assert_snapshot(value: Variant, name := "")` on `GdToolsTest`, consistent
  with the existing `assert_*` family.
- Returns a pass/fail `bool` like other assertions and participates in
  existing failure diagnostics.
- Auto-naming: `<test_method>_<call_index>` when `name` is omitted; explicit
  `name` used verbatim when given. Multiple snapshots per test are supported
  (distinct names/call indices).

### FR2 — Serialization (3 tiers, deterministic)

1. **Values:** primitives, Arrays, Dictionaries — dict keys sorted so output
   is stable across runs/platforms.
2. **Objects:** structural dump of the object's declared script properties
   (property name → serialized value, recursive).
3. **Nodes:** textual scene-tree dump — node path, class, and serialized
   properties, rendered as an indented tree.
- Deterministic: same input → byte-identical output.
- Cycle-safe (repeated references rendered as references, no infinite
  recursion).

### FR3 — Storage

- Snapshots stored under `<project_root>/.gd-tools/snapshots/<suite>/<test>/<name>.snap`.
- `.snap` files are human-readable text with a small versioned header
  (format version, suite, test, name) so they diff well in PRs and are
  reviewable.
- LF line endings enforced regardless of platform.

### FR4 — Comparison & failure behavior

- First run (no stored snapshot): snapshot is written and the test passes;
  the summary reports `N new snapshots written`.
- Subsequent mismatch: test fails with a unified expected-vs-actual diff
  consistent with existing assertion diagnostics.
- Snapshot I/O errors (unwritable path, malformed existing file) fail the
  test with a clear diagnostic — fail-closed, not fail-open.

### FR5 — CLI: `gd-tools test --snapshot-update`

- Rewrites stored snapshots from actual values instead of comparing. New
  snapshots are written; mismatches are replaced; a summary line reports how
  many were updated.

### FR6 — Obsolete snapshots

- Snapshot files whose owning suite/test no longer runs are detected at the
  end of a test run and reported in the summary as obsolete
  (non-destructive).
- `gd-tools clean` gains snapshot-aware removal (e.g.
  `gd-tools clean --snapshots`, consistent with existing `--cache` behavior).

### FR7 — Reporting & docs

- Summary output includes counts: written, passed, failed (mismatched),
  obsolete.
- README (usage section + example), ARCHITECTURE (snapshot subsystem
  description), and the JSON schema/config docs updated as needed.

## Non-Functional Requirements

- Snapshot format is versioned; unknown-format files produce a clear
  diagnostic rather than a crash.
- No new Python dependencies; serialization/diffing implemented with the
  existing stack (runtime-side GDScript, Python-side reporting glue only if
  needed).
- Performance: comparing reads one file per snapshot; no startup penalty
  when a suite uses no snapshots.
- Works under `--parallel`, `--watch`, and `--changed` without extra
  configuration.

## Acceptance Criteria

1. `assert_snapshot` passes on first run and writes the snapshot; the
   summary reports the count.
2. A subsequent changed value fails with a unified diff naming the snapshot
   file.
3. `--snapshot-update` rewrites and the next run passes.
4. All three serialization tiers produce stable, deterministic `.snap`
   content (verified by repeated runs).
5. Obsolete snapshots are reported; `gd-tools clean --snapshots` removes
   them.
6. Existing suites are unaffected; full test matrix (`CI=true pytest`) green;
   coverage targets met for new source.

## Out of Scope

- Editor plugin display integration for snapshots.
- Interactive accept/reject review prompts.
- Auto-pruning of obsolete snapshots.
- Binary/`.tscn` scene snapshots; cross-runtime (GdUnit4) support.
