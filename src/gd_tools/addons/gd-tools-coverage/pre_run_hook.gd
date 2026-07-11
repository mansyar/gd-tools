extends GutHookScript

## Pre-run hook for GUT test runner.
## Instruments GDScript source files with coverage tracking calls
## before tests are executed.


func run() -> void:
	# Phase 2: Read GD_TOOLS_COVERAGE_PLAN env var, parse plan JSON.
	# Phase 3: Instrument source files, activate tracker.
	pass
