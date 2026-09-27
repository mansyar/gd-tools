extends GdToolsTest

class_name NativeEngineErrorSuite

# Raised by the code review: `_capture_engine_diagnostics` matched only lines
# beginning "ERROR:", but GDScript reports a runtime script error as
# "SCRIPT ERROR:". Every such error was therefore written to the captured log
# and then ignored, leaving `engine_errors` empty and the run short of the
# exit-2 escalation that is supposed to catch a broken run.
#
# This suite produces one on purpose so the capture is testable. It is the only
# fixture in the project that is expected to exit 2.

func test_raises_a_runtime_script_error() -> void:
	# The variable is deliberately UNTYPED. With `var target := get_tree()` GDScript
	# resolves the member access at PARSE time and the whole suite fails to load,
	# which is the unloadable-suite path, not the runtime-script-error path this
	# fixture exists to produce. An untyped `var target =` forces a dynamic
	# lookup, so the failure happens at RUNTIME, after the suite has loaded and
	# the test has started -- which is what a real type mismatch inside a helper
	# looks like from the engine's side.
	var target = get_tree()
	target.no_such_method_exists()

func test_after_the_error_also_reports() -> void:
	# A second test proves the runner kept going and still recorded results, so
	# the escalation is attributable to the captured error rather than to the
	# suite simply aborting.
	assert_true(true, "unrelated passing assertion")
