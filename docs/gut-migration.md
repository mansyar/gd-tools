# Migrating from GUT to the native runtime

`gd-tools` runs GDScript tests with its own native runtime. Suites that
`extend GdToolsTest` run directly on that runtime.

Version 0.6.0 **removed the GUT compatibility bridge** that shipped in
v0.5.0. The bundled `GutTest` base class is gone, and `extends GutTest`
no longer resolves. Suites still extending `GutTest` are rejected by
test discovery with exit code 2:

```
test/legacy_suite.gd extends GutTest. GUT runtime support was removed
in v0.6.0. Run `gd-tools migrate` or see docs/gut-migration.md.
```

`gd-tools migrate` is the supported path from GUT to the native runtime.
This guide explains what changed, what the native runtime provides in
place of the old GUT API, and how to migrate a suite.

## What changed in v0.6.0

| Removed | Replacement |
|---|---|
| Bundled `class_name GutTest` shim (`extends GutTest` no longer resolves) | `extends GdToolsTest` |
| `gd-tools init --with-gut` (option removed; exits 2) | `gd-tools init` bootstraps the native runtime only |
| `--runtime gut` CLI flag (rejected with exit 2) | `--runtime native` (the default; the flag can be dropped) |
| `test.runtime = "gut"` in `gd-tools.toml` (hard validation error, exit 2) | Remove the line; the native runtime is the default |
| GUT Installed / GUT Version / GUT Suites / GUT Config doctor checks | One informational **Legacy GUT** advisory pointing at `gd-tools migrate` |
| Pre-run bridge preflight scan | The same construct catalog is reported by `gd-tools migrate` |

`gd-tools doctor` still detects leftover GUT artifacts — `addons/gut`,
`.gutconfig.json`, and `extends GutTest` suites — as an informational
advisory; it never blocks, and the fix hint points at `gd-tools migrate`.

## What the native runtime provides

The native runtime covers the core of the GUT 9.x API that the bridge
used to provide. Suites extending `GdToolsTest` get:

| Family | Members |
|---|---|
| Lifecycle hooks | `before_all`, `after_all`, `before_each`, `after_each`, `prerun_setup`, `postrun_teardown` |
| Value & comparison assertions | `assert_true`, `assert_false`, `assert_eq`, `assert_ne`, `assert_gt`, `assert_gte`, `assert_lt`, `assert_lte`, `assert_almost_eq`, `assert_almost_ne`, `assert_between`, `assert_not_between`, `assert_null`, `assert_not_null`, `assert_has`, `assert_does_not_have`, `assert_has_method`, `assert_is`, `assert_same`, `assert_not_same`, `assert_eq_deep`, `assert_ne_deep`, `assert_typeof`, `assert_not_typeof` |
| String assertions | `assert_string_contains`, `assert_string_starts_with`, `assert_string_ends_with` |
| File assertions | `assert_file_exists`, `assert_file_does_not_exist`, `assert_file_empty`, `assert_file_not_empty` |
| Signal assertions | `watch_signals`, `assert_signal_emitted`, `assert_signal_not_emitted`, `assert_signal_emitted_with_args` (element-wise matching with the `"any"` wildcard), `assert_signal_emitted_after` (awaitable), `assert_signal_emit_count` |
| Async helpers | `wait_seconds`, `wait_for_signal(signal, timeout)` (bounded), `wait_process_frame`, `wait_physics_frames` |
| Parameterization | `parameterize`, `use_parameters` (pytest-style case names) |
| Mocking | `double()`, `partial_double()`, `stub()`, `assert_called`, `assert_not_called`, `assert_call_count` |
| Skipping & misc | `skip_test`, `fail`, `pending_test` |

Results use the native result contract: the same statuses
(`passed`/`failed`/`skipped`/`error`/`timeout`), the same output table,
JUnit XML, exit codes (`0` pass, `1` failures, `2` infrastructure
error), and the same coverage reporting.

## What has no native equivalent

These GUT constructs were never supported by the bridge and have no
native counterpart. The `gd-tools migrate` report flags them per file
and line:

| Category | Constructs | Migrate to |
|---|---|---|
| Property/orphan/interactive assertions | `assert_setget()`, `assert_accessors()`, `assert_exports()`, `assert_property_with_backing_variable()`, `assert_freed()`, `assert_no_new_orphans()`, `pause_before_teardown()` | Direct `get`/`set` assertions; `is_instance_valid()` checks; cleanup in `postrun_teardown` |
| Engine-error assertions | `assert_engine_error()`, `assert_engine_error_count()`, `assert_push_error()`, `assert_push_warning()`, and count variants | GdToolsTest collects engine errors and warnings natively; use its diagnostics |
| Signal helpers without a native equivalent | `assert_signal_emitted_with_parameters` (rename to `assert_signal_emitted_with_args`), `assert_has_signal`, `assert_connected`, `assert_not_connected` | Rework around `watch_signals` + `assert_signal_emitted*`, or assert connection state directly |
| Legacy async aliases | `yield_for`, `yield_to`, `yield_frames`, `wait_until`, `wait_while`, `wait_frames`, `wait_idle_frames`, `wait_process_frames` | The native `wait_seconds`, `wait_for_signal`, `wait_process_frame`, `wait_physics_frames` equivalents, or plain `await` |
| Version-gated skips | `skip_if_godot_version_lt()`, `skip_if_godot_version_ne()` | `skip_test()` guarded by an `Engine.get_version_info()` check |

Signal note: `watch_signals`, `assert_signal_emitted`,
`assert_signal_not_emitted`, `assert_signal_emit_count`, and
`assert_signal_emitted_with_args` are native on `GdToolsTest`.

## Recommended migration steps

1. **Run `gd-tools migrate`.** The read-only report inventories every
   legacy suite with its unsupported constructs and line numbers, lists
   legacy aliases (`assert_in`, `pending_test`) with their native
   spellings, and shows unified diffs of the proposed base-class
   rewrites. Nothing is written (exit `1` when items are found).
2. **Migrate unsupported constructs** by hand using the table above.
   Suites containing them are never rewritten automatically.
3. **Apply the mechanical rewrites:** `gd-tools migrate --apply`
   renames every clean suite's `extends GutTest` to
   `extends GdToolsTest` (diff previewed first) and translates
   `.gutconfig.json` into `gd-tools.toml` — merge, never clobber:
   values you already set are kept and the conflict is reported.
   Unmapped keys are listed, never silently dropped, and
   `.gutconfig.json` itself is preserved on disk. `--config-only`
   translates configuration only.
4. **Remove stale artifacts:** `addons/gut` and `.gutconfig.json` are
   not read by gd-tools. `gd-tools doctor` lists them in the Legacy GUT
   advisory until they are gone.
5. **Verify:** `gd-tools test` should now discover and run every suite;
   `gd-tools test --coverage` confirms coverage still reports. No GUT
   autoload or hook scripts are involved.

Exit codes for `gd-tools migrate`: `0` nothing to migrate, `1` migration
items found (dry run, nothing written), `2` infrastructure error
(unreadable or unparseable files).

## Where to go next

- [User guide](./USER_GUIDE.md) — the full native runtime API and CLI reference.
- [Roadmap](./ROADMAP.md) — the native runtime transition history.
