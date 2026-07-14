extends GutHookScript

## Pre-run hook for GUT test runner.
## Activates the coverage tracker after all autoloads have initialized.
## Instrumentation is handled by _GDTCoverage._ready() (the first autoload),
## which runs before any other autoload creates instances.


func run() -> void:
	_GDTCoverage.set_active(true)
