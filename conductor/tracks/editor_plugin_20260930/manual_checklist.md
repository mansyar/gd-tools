# Manual Testing Checklist — Godot Editor Plugin

Executed at each phase checkpoint per the track's Testing Approach Note
(GDScript plugin UI cannot run in headless CI). Target: Godot 4.5+;
verify on at least one of 4.5 / 4.6 / 4.7 and document the version used.

## Phase 2 — Dock Panel

| # | Check | Steps | Expected |
|---|-------|-------|----------|
| 2.1 | Plugin enable | Open the project in Godot → Project → Project Settings → Plugins tab → enable **gd-tools** | A **gd-tools** dock appears in the editor's right panel; no errors in the Output pane |
| 2.2 | Run Tests (happy path) | Click **Run Tests** | Buttons disable while running; status shows "Running gd-tools test ..."; on completion: `Finished: N passed, M failed, K skipped in Xs`; failed tests listed with suite.test names and assertion messages; artifact path shown |
| 2.3 | Re-click guard | Double-click **Run Tests** quickly | Second click while running is ignored (no second process; UI stays consistent) |
| 2.4 | Run Coverage | Click **Run Coverage** | Same as 2.2 plus a `Coverage: lines X%, branches Y%` summary line (branches `n/a` when the plan has no branch points) |
| 2.5 | Missing CLI fallback | Temporarily remove `gd-tools` from PATH (or uninstall) and restart the editor, then click **Run Tests** | Friendly message: "gd-tools CLI not found" with `pip install gd-tools-cli` hint and restart note; buttons re-enabled |
| 2.6 | cwd independence | Launch the editor from a working directory *outside* the project (`godot --path <project> -e`) and run 2.2 | Run still succeeds — the dock passes `--project <res://>` explicitly |
| 2.7 | Plugin disable | Uncheck **gd-tools** in Project Settings → Plugins | Dock disappears cleanly; no errors; re-enabling restores it |

## Phase 3 — Coverage Heatmap Overlay

| # | Check | Steps | Expected |
|---|-------|-------|----------|
| 3.1 | Colors after coverage | Run **Run Coverage** from the dock, then open a covered script in the script editor | Executed lines highlighted green, never-executed lines red |
| 3.2 | Partial branches | Open a script with partially-taken branch points | Lines with some (not all) branch points covered show yellow |
| 3.3 | Auto-refresh after dock run | With a script open, run Coverage again after editing tests | Overlay updates without reopening the script |
| 3.4 | Load on editor open | Restart the editor with existing `.gd-tools/coverage/` data | Overlay loads from artifacts on open |
| 3.5 | Stale flag | Touch/save a covered source file after the coverage run | Lines for that file are marked stale (visually distinct, never shown as fresh) |
| 3.6 | Toggle off/on | Disable then re-enable the plugin | Overlay clears on disable and restores on enable |
