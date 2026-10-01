# Migrating from GUT to the gd-tools bridge and native runtime

`gd-tools` runs GDScript tests with its own native runtime. Suites that
`extend GdToolsTest` run directly on that runtime. Suites that still
`extend GutTest` run through the **GUT compatibility bridge**: the same
native runner executes them, and a bundled `GutTest` base class provides
the documented core subset of the GUT 9.x API — **without GUT installed**.

The bridge is a temporary, one-release migration path. It exists so that
existing GUT suites keep running while you migrate them; it is not a
permanent GUT replacement.

## What the bridge supports

| Family | Members |
|---|---|
| Lifecycle hooks | `before_all`, `after_all`, `before_each`, `after_each`, `prerun_setup`, `postrun_teardown` |
| Value & comparison assertions | `assert_true`, `assert_false`, `assert_eq`, `assert_ne`, `assert_gt`, `assert_gte`, `assert_lt`, `assert_lte`, `assert_almost_eq`, `assert_almost_ne`, `assert_between`, `assert_not_between`, `assert_null`, `assert_not_null`, `assert_has`, `assert_does_not_have`, `assert_has_method`, `assert_is`, `assert_same`, `assert_not_same`, `assert_eq_deep`, `assert_ne_deep`, `assert_typeof`, `assert_not_typeof` |
| String assertions | `assert_string_contains`, `assert_string_starts_with`, `assert_string_ends_with` |
| File assertions | `assert_file_exists`, `assert_file_does_not_exist`, `assert_file_empty`, `assert_file_not_empty` |
| Signal assertions | `watch_signals`, `assert_signal_emitted`, `assert_signal_not_emitted`, `assert_signal_emitted_with_parameters`, `assert_signal_emit_count`, `assert_has_signal`, `assert_connected`, `assert_not_connected` |
| Async helpers | `wait_seconds`, `wait_for_signal` (bounded), `wait_frames`, `wait_physics_frames`, `wait_idle_frames`, `wait_process_frames`, `wait_until`, `wait_while`, `yield_for`, `yield_to`, `yield_frames` |
| Skipping | `skip_test`, `skip_if_godot_version_lt`, `skip_if_godot_version_ne` |
| Parameterization | `parameterize`, `use_parameters` (native expansion, pytest-style case names) |
| Misc | `fail`, `pending_test` |

Results normalize into the native result contract: the same statuses
(`passed`/`failed`/`skipped`/`error`/`timeout`), the same output table,
JUnit XML, exit codes (`0` pass, `1` failures, `2` infrastructure error),
and the same coverage reporting. A project can mix `GdToolsTest` and
`GutTest` suites in a single `gd-tools test` invocation — each file is
routed automatically by its base class.

## What the bridge refuses

Some GUT features have no equivalent in the native runtime. The bridge
**statically scans bridge suites before any test runs**; if an
unsupported construct is found, the whole run fails at preflight (exit
code 2) with a per-file, per-line list:

| Category | Constructs | Migrate to |
|---|---|---|
| Property/orphan/interactive assertions | `assert_setget()`, `assert_accessors()`, `assert_exports()`, `assert_property_with_backing_variable()`, `assert_freed()`, `assert_no_new_orphans()`, `pause_before_teardown()` | Direct `get`/`set` assertions; `is_instance_valid()` checks; cleanup in `postrun_teardown` |
| Engine-error assertions | `assert_engine_error()`, `assert_engine_error_count()`, `assert_push_error()`, `assert_push_warning()`, and count variants | GdToolsTest collects engine errors and warnings natively; migrate the suite to `GdToolsTest` and use its diagnostics |

Parameterization (`parameterize()` / `use_parameters()`) is no longer
refused: it is native now, and bridge suites use the same declaration
validation, case expansion, and pytest-style case naming as `GdToolsTest`
suites (see the parameterized-tests section of the user guide). Malformed
declarations fail at preflight with exit code 2, exactly as they do for
native suites.

Mocking constructs (`double()`, `partial_double()`, `stub()`, and the
`assert_called*` family) are no longer refused: the native runtime
implements them and bridge suites inherit them from `GdToolsTest` with
identical semantics (see the mocking section of the user guide).

Unsupported GUT features beyond this list also fail the preflight scan
with actionable guidance naming the construct.

## GUT must not be installed

The bridge provides `class_name GutTest` itself. If `addons/gut` is
present, the two definitions collide, so preflight fails with:

```
GUT is installed at 'res://addons/gut'. The GUT compatibility bridge
provides GutTest natively, so the GUT addon would create a duplicate
class_name GutTest. Remove addons/gut to run through the bridge.
```

Remove `addons/gut` (and the GUT plugin entry if you enabled it in the
editor) before running tests. `gd-tools init --with-gut` is no longer
part of the recommended workflow; the bridge replaces it.

## The legacy `--runtime gut` flag is gone

The old subprocess execution path (`--runtime gut` on the CLI and
`test.runtime = "gut"` in `gd-tools.toml`) has been removed. Both are
rejected with migration guidance instead of silently remapping. Remove
the flag/config line; suites are routed automatically.

`gd-tools doctor` reports the new reality: GUT is never required, an
installed GUT addon is flagged as a bridge conflict, and existing
`GutTest` suites are listed as bridge-eligible.

## Recommended migration steps

1. **Remove `addons/gut`** from the project (see above).
2. **Run `gd-tools test`.** Bridge suites run as-is if they only use the
   supported subset; failures at this stage are the preflight scan
   telling you exactly which constructs to migrate, per file and line.
3. **Migrate unsupported constructs** using the table above.
4. **Optional — rename the base class.** `extends GutTest` keeps working
   through the bridge, but `extends GdToolsTest` is the end state. Most
   suites need nothing more than renaming the base class and, where you
   relied on GUT-only spelling (`assert_in`, `pending_test`), keeping
   the bridge-compatible aliases until you are ready to rename them.
   `gd-tools migrate --apply` performs this rename for every clean
   suite and shows the diff first.
5. **Verify coverage still reports** with `gd-tools test --coverage`;
   bridge suites participate in the same coverage tracker and plan
   schema. No GUT autoload or hook scripts are involved.
6. **Remove stale configuration**: `.gutconfig.json` is not read by the
   native runtime or the bridge. Run `gd-tools migrate --config-only`
   to translate the options it maps into `gd-tools.toml` under `[test]`
   (the file itself is preserved on disk). Test selectors, timeouts,
   and tags live in `gd-tools.toml` under `[test]`.

## Guided migration (`gd-tools migrate`)

`gd-tools migrate` automates the mechanical parts of the steps above:

```bash
gd-tools migrate                 # read-only report (exit 1 when items are found)
gd-tools migrate --config-only   # translate .gutconfig.json only
gd-tools migrate --apply         # apply rewrites and config translation
```

- **Report (default):** inventories every bridge suite with the
  unsupported constructs and line numbers the bridge preflight reports,
  lists bridge-only aliases (`assert_in`, `pending_test`) that work
  today but have native spellings, and shows unified diffs of the
  proposed base-class rewrites. Nothing is written.
- **Config translation:** known `.gutconfig.json` options are mapped
  into `[test]` in `gd-tools.toml` — merge, never clobber: values you
  already set are kept and the conflict is reported. Unmapped keys are
  listed, never silently dropped, and `.gutconfig.json` itself is
  preserved on disk.
- **Rewrites (`--apply`):** clean suites (no unsupported constructs)
  get `extends GutTest` renamed to `extends GdToolsTest`. Files with
  unsupported constructs are never rewritten — migrate those constructs
  by hand, then re-run.

Exit codes: `0` nothing to migrate, `1` migration items found (dry run,
nothing written), `2` infrastructure error (unreadable or unparseable
files).

## Where the bridge is heading

After the bounded migration period the bridge itself is removed and
`extends GutTest` stops resolving. Plan your suites to end on
`extends GdToolsTest`; the bridge exists to make that move incremental
rather than big-bang. See the [Native Runtime Transition
section](./ROADMAP.md#native-runtime-transition-completed-foundation)
in the roadmap for the migration status.

The native runtime now covers signal assertions directly on `GdToolsTest`:
`watch_signals`, `assert_signal_emitted`, `assert_signal_not_emitted`,
`assert_signal_emit_count`, `assert_signal_emitted_with_args`
(element-wise matching with the `"any"` wildcard), and the awaitable
`assert_signal_emitted_after`. When migrating a GUT suite off the bridge,
map `assert_signal_emitted_with_parameters` to
`assert_signal_emitted_with_args`; `assert_has_signal`, `assert_connected`,
and `assert_not_connected` have no native equivalent yet.
