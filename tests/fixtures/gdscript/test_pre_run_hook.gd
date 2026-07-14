extends GutTest

## GUT tests for the simplified pre_run_hook.gd.
## After Phase 3, pre_run_hook.gd only calls _GDTCoverage.set_active(true).
## Instrumentation logic has been moved to coverage.gd._ready() and is
## tested in test_coverage_instrumentation.gd.

var _hook


func before_each():
	_hook = load("res://addons/gd-tools-coverage/pre_run_hook.gd").new()
	_GDTCoverage.set_active(false)


func after_each():
	_hook = null
	_GDTCoverage.set_active(false)


func test_run_activates_tracker():
	_hook.run()
	assert_true(_GDTCoverage.is_active(), "tracker should be active after run()")


func test_hook_has_no_instrumentation_methods():
	assert_false(_hook.has_method("_load_plan"), "should not have _load_plan")
	assert_false(_hook.has_method("_validate_plan"), "should not have _validate_plan")
	assert_false(_hook.has_method("_validate_file_entry"), "should not have _validate_file_entry")
	assert_false(_hook.has_method("_instrument_files"), "should not have _instrument_files")
	assert_false(_hook.has_method("_instrument_file"), "should not have _instrument_file")
	assert_false(_hook.has_method("_inject_trackers"), "should not have _inject_trackers")
	assert_false(_hook.has_method("_extract_indent"), "should not have _extract_indent")
	assert_false(_hook.has_method("_detect_body_indent"), "should not have _detect_body_indent")
	assert_false(_hook.has_method("_activate_tracker"), "should not have _activate_tracker")
