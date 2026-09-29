extends SceneTree

## Headless entrypoint for the gd-tools native test runtime.
##
## The Python orchestrator writes a manifest and result path into the
## environment before launching Godot with this script. The runner executes
## one manifest and exits with 0 for passing tests, 1 for test failures, and
## 2 for protocol/runtime errors.

signal test_call_completed

const PROTOCOL_VERSION := 2
const TEST_CONTEXT_SCRIPT = preload("res://addons/gd-tools-test/gd_tools_test_context.gd")
const PARAMETER_NAMING = preload("res://addons/gd-tools-test/gd_tools_parameter_naming.gd")

var _test_results: Array[Dictionary] = []
var _run_status := "passed"
var _active_test_token := 0
var _test_timeout_reached := false
var _test_completed := false
var _coverage_enabled := false
var _run_started_at := ""
var _run_finished_at := ""
var _engine_errors: Array[String] = []
var _engine_warnings: Array[String] = []
# Engine errors Godot printed while the collector attempted instrumentation.
# They are the omission's evidence (R1/R4), not a run failure, so they are
# demoted to warnings before the engine-error promotion runs.
var _activation_engine_errors: Array[String] = []

var _coverage_omissions: Array = []
var _log_path := ""
var _current_windowed := false
var _screenshot_path := ""


func _init() -> void:
	_log_path = OS.get_environment("GD_TOOLS_NATIVE_LOG")
	call_deferred("_run")


func _run() -> void:
	_run_started_at = _timestamp()
	var manifest := _load_manifest()
	if manifest.is_empty():
		return

	if int(manifest.get("protocol_version", -1)) != PROTOCOL_VERSION:
		_finish_with_error(
			"Unsupported native protocol version: %s" % manifest.get("protocol_version", "")
		)
		return

	if not _activate_coverage(manifest.get("coverage", {})):
		return

	_emit_event({"event": "run_started", "protocol_version": PROTOCOL_VERSION})
	for suite_data in manifest.get("suites", []):
		await _run_suite(suite_data)

	_finish_with_status()


func _load_manifest() -> Dictionary:
	var manifest_path := OS.get_environment("GD_TOOLS_NATIVE_MANIFEST")
	if manifest_path.is_empty():
		_finish_with_error("GD_TOOLS_NATIVE_MANIFEST is not set")
		return {}

	if not FileAccess.file_exists(manifest_path):
		_finish_with_error("Native manifest not found: %s" % manifest_path)
		return {}

	var file := FileAccess.open(manifest_path, FileAccess.READ)
	if file == null:
		_finish_with_error("Unable to read native manifest: %s" % manifest_path)
		return {}

	var parsed: Variant = JSON.parse_string(file.get_as_text())
	if typeof(parsed) != TYPE_DICTIONARY:
		_finish_with_error("Native manifest must contain a JSON object")
		return {}
	return parsed


func _run_suite(suite_data: Dictionary) -> void:
	var suite_name := str(suite_data.get("name", ""))
	var suite_path := str(suite_data.get("path", ""))
	var integration: Variant = suite_data.get("integration", {})
	_current_windowed = (
		typeof(integration) == TYPE_DICTIONARY and integration.get("mode", "headless") == "windowed"
	)
	_screenshot_path = OS.get_environment("GD_TOOLS_NATIVE_SCREENSHOT")
	if _current_windowed and DisplayServer.get_name() == "headless":
		_record_suite_error(
			suite_name,
			"Windowed execution requires a display; the renderer is headless",
		)
		return
	var script := load(suite_path) as GDScript
	# A script with a parse error still loads as a GDScript resource in Godot
	# 4.7+; only `can_instantiate()` reveals the broken state. Calling `new()`
	# on such a script raises a script error that would abort this coroutine
	# silently, so the load guard has to cover both conditions.
	if script == null or not script.can_instantiate():
		_record_suite_error(suite_name, "Unable to load suite: %s" % suite_path)
		return

	var suite_context = script.new() as GdToolsTest
	if suite_context == null:
		_record_suite_error(suite_name, "Suite does not extend GdToolsTest")
		return
	get_root().add_child(suite_context)
	var suite_timeout := _suite_timeout(suite_data)

	var prerun_failure_count := suite_context.get_failures().size()
	if suite_context.has_method("prerun_setup"):
		var prerun_result := await _run_optional_call(suite_context, "prerun_setup", suite_timeout)
		_record_hook_result(
			suite_name,
			"prerun_setup",
			_failures_since(suite_context, prerun_failure_count),
			bool(prerun_result.get("timed_out", false)),
			suite_timeout
		)

	var before_failure_count := suite_context.get_failures().size()
	if suite_context.has_method("before_all"):
		var before_result := await _run_optional_call(suite_context, "before_all", suite_timeout)
		var before_failures := _failures_since(suite_context, before_failure_count)
		_record_hook_result(
			suite_name,
			"before_all",
			before_failures,
			bool(before_result.get("timed_out", false)),
			suite_timeout
		)

	for test_data in suite_data.get("tests", []):
		for case_data in _expand_test_cases(script, test_data):
			await _run_test(suite_context, script, suite_name, case_data)

	var after_failure_count := suite_context.get_failures().size()
	if suite_context.has_method("after_all"):
		var after_result := await _run_optional_call(suite_context, "after_all", suite_timeout)
		var after_failures := _failures_since(suite_context, after_failure_count)
		_record_hook_result(
			suite_name,
			"after_all",
			after_failures,
			bool(after_result.get("timed_out", false)),
			suite_timeout
		)

	var postrun_failure_count := suite_context.get_failures().size()
	if suite_context.has_method("postrun_teardown"):
		var postrun_result := await _run_optional_call(
			suite_context, "postrun_teardown", suite_timeout
		)
		_record_hook_result(
			suite_name,
			"postrun_teardown",
			_failures_since(suite_context, postrun_failure_count),
			bool(postrun_result.get("timed_out", false)),
			suite_timeout
		)

	suite_context.queue_free()
	await process_frame


func _expand_test_cases(script: GDScript, test_data: Dictionary) -> Array:
	## Expand a manifest test carrying parameter metadata into per-case entries.
	##
	## Signature-parameterized methods (arity > 0) receive their value set as
	## call arguments; zero-argument ``use_parameters`` methods read the
	## current case index from the instance instead. A declaration with an
	## empty values list collapses to a single skipped entry.
	var parameters: Variant = test_data.get("parameters")
	if typeof(parameters) != TYPE_DICTIONARY:
		return [test_data]
	var values: Variant = (parameters as Dictionary).get("values", [])
	if typeof(values) != TYPE_ARRAY:
		return [test_data]
	var method_name := str(test_data.get("name", ""))
	if (values as Array).is_empty():
		var skipped: Dictionary = test_data.duplicate(true)
		skipped.erase("parameters")
		skipped["skip_reason"] = "No parameter values declared."
		return [skipped]
	var arity := _method_arity(script, method_name)
	var cases: Array = []
	for case_index in (values as Array).size():
		var value_set := PARAMETER_NAMING.normalize_value_set(values[case_index])
		var case_data: Dictionary = test_data.duplicate(true)
		case_data.erase("parameters")
		case_data["name"] = (method_name + PARAMETER_NAMING.case_suffix(value_set, case_index))
		case_data["method"] = method_name
		if arity > 0:
			case_data["parameters_values"] = value_set
		case_data["parameters_index"] = case_index
		cases.append(case_data)
	return cases


func _method_arity(script: GDScript, method_name: String) -> int:
	for method_value: Variant in script.get_script_method_list():
		if typeof(method_value) != TYPE_DICTIONARY:
			continue
		var method: Dictionary = method_value
		if str(method.get("name", "")) != method_name:
			continue
		var arguments: Variant = method.get("args", [])
		if typeof(arguments) != TYPE_ARRAY:
			return 0
		return (arguments as Array).size()
	return 0


func _suite_timeout(suite_data: Dictionary) -> float:
	# The maximum across every test, not the first. This budget is handed to
	# `before_all` and `after_all`, so reading only the first entry made the
	# setup allowance depend on declaration order -- a suite whose first test
	# declared a short timeout starved its own setup.
	var tests: Array = suite_data.get("tests", [])
	if tests.is_empty():
		return 5.0
	var budget := 0.0
	for test_data in tests:
		budget = max(budget, float(test_data.get("timeout_seconds", 5.0)))
	return max(budget, 0.001)


func _run_test(
	suite_context: GdToolsTest, script: GDScript, suite_name: String, test_data: Dictionary
) -> void:
	var test_name := str(test_data.get("name", ""))
	_emit_event({"event": "test_started", "suite": suite_name, "name": test_name})
	var skip_reason := str(test_data.get("skip_reason", ""))
	if not skip_reason.is_empty():
		_record_test_result(suite_name, test_name, "skipped", 0.0, skip_reason, {})
		_emit_event(
			{
				"event": "test_finished",
				"suite": suite_name,
				"name": test_name,
				"status": "skipped",
				"attempts": 1,
			}
		)
		return
	var retry_count := max(int(test_data.get("retries", 0)), 0)
	var attempt := 1
	var total_duration := 0.0
	var final_result: Dictionary = {}

	while true:
		var attempt_result: Dictionary = await _run_test_attempt(
			suite_context, script, test_name, test_data
		)
		total_duration += float(attempt_result.get("duration_seconds", 0.0))
		final_result = attempt_result
		var status := str(final_result.get("status", "error"))
		var retryable := status == "failed" or status == "timeout"
		if not retryable or attempt > retry_count:
			break
		attempt += 1

	var final_status := str(final_result.get("status", "error"))
	_record_test_result(
		suite_name,
		test_name,
		final_status,
		total_duration,
		str(final_result.get("message", "")),
		final_result.get("diagnostics", {}),
		attempt,
		str(final_result.get("started_at", "")),
		str(final_result.get("finished_at", ""))
	)
	_emit_event(
		{
			"event": "test_finished",
			"suite": suite_name,
			"name": test_name,
			"status": final_status,
			"attempts": attempt,
		}
	)


func _run_test_attempt(
	suite_context: GdToolsTest, script: GDScript, test_name: String, test_data: Dictionary
) -> Dictionary:
	var test_context = _new_test_context(script, suite_context)
	if test_context == null:
		return {
			"status": "error",
			"duration_seconds": 0.0,
			"message": "Suite does not extend GdToolsTest",
			"diagnostics": {},
			"started_at": _timestamp(),
			"finished_at": _timestamp(),
		}

	get_root().add_child(test_context)
	var started_ticks := Time.get_ticks_msec()
	var started_at := _timestamp()
	var integration_result := _prepare_integration(test_context, test_data.get("integration", {}))
	if not bool(integration_result.get("ok", false)):
		var setup_message := str(integration_result.get("message", "Unable to prepare integration"))
		await _teardown_integration(test_context)
		test_context.queue_free()
		await process_frame
		return {
			"status": "error",
			"duration_seconds": float(Time.get_ticks_msec() - started_ticks) / 1000.0,
			"message": setup_message,
			"diagnostics": {},
			"started_at": started_at,
			"finished_at": _timestamp(),
		}
	var timeout_seconds := max(float(test_data.get("timeout_seconds", 5.0)), 0.001)
	_begin_test_timeout(timeout_seconds)
	var timed_out := false
	var method_name := str(test_data.get("method", test_name))

	if test_context.has_method("before_each"):
		await _await_test_call(test_context, "before_each")
		timed_out = _test_timeout_reached

	if not timed_out:
		if test_context.has_method(method_name):
			test_context._gd_tools_case_index = int(test_data.get("parameters_index", 0))
			await _await_test_call(
				test_context, method_name, test_data.get("parameters_values", [])
			)
			if _test_timeout_reached:
				timed_out = true
		else:
			timed_out = true
			_cancel_timeout()
			var missing_result := {
				"status": "error",
				"duration_seconds": float(Time.get_ticks_msec() - started_ticks) / 1000.0,
				"message": "Test method not found: %s" % method_name,
				"diagnostics": {},
				"started_at": started_at,
				"finished_at": _timestamp(),
			}
			await _teardown_integration(test_context)
			test_context.queue_free()
			await process_frame
			return missing_result

	var cleanup_failure_start: int = test_context.get_failures().size()
	var cleanup_failures: Array[Dictionary] = []
	var cleanup_timed_out := false
	if test_context.has_method("after_each"):
		if timed_out:
			await _run_cleanup(test_context, "after_each", timeout_seconds)
		else:
			await _await_test_call(test_context, "after_each")
		cleanup_timed_out = _test_timeout_reached
		if cleanup_timed_out:
			timed_out = true
		cleanup_failures = _failures_since(test_context, cleanup_failure_start)

	var failures: Array[Dictionary] = test_context.get_failures()
	var status := "failed" if not failures.is_empty() else "passed"
	var message := _failure_message(failures)
	if status == "passed" and test_context.is_skipped():
		# A skip is only reported when nothing actually failed, so a recorded
		# failure always outranks it. Cleanup failures and timeouts still
		# escalate below: they are infrastructure, not the test's verdict.
		status = "skipped"
		message = test_context.get_skip_reason()
	if not cleanup_failures.is_empty() or cleanup_timed_out:
		status = "error"
		# A cleanup failure is infrastructure, but the assertion that failed
		# first is the actionable part, so both are reported.
		var cleanup_message := (
			"after_each timed out after %.3f seconds" % timeout_seconds
			if cleanup_timed_out
			else "after_each failed: %s" % _failure_message(cleanup_failures)
		)
		message = (
			"%s; %s" % [message, cleanup_message] if not message.is_empty() else cleanup_message
		)
	elif timed_out:
		status = "timeout"
		message = "Test timed out after %.3f seconds" % timeout_seconds
	var diagnostics := {"failures": failures}
	if _current_windowed and status in ["failed", "timeout", "error"]:
		var screenshot_result := await _capture_failure_screenshot(test_context, test_name)
		if not bool(screenshot_result.get("ok", false)):
			status = "error"
			# Keep the real cause visible: a missing screenshot must not erase
			# the assertion or cleanup failure that actually failed the test.
			var detail := str(screenshot_result.get("message", "unknown screenshot error"))
			message = (
				"%s (screenshot capture failed: %s)" % [message, detail]
				if not message.is_empty()
				else "Screenshot capture failed: %s" % detail
			)
			diagnostics["screenshot_error"] = screenshot_result
		elif not str(screenshot_result.get("path", "")).is_empty():
			diagnostics["screenshot"] = screenshot_result["path"]
	var duration := float(Time.get_ticks_msec() - started_ticks) / 1000.0
	var finished_at := _timestamp()
	_cancel_timeout()
	await _teardown_integration(test_context)
	test_context.queue_free()
	await process_frame
	return {
		"status": status,
		"duration_seconds": duration,
		"message": message,
		"diagnostics": diagnostics,
		"started_at": started_at,
		"finished_at": finished_at,
	}


func _prepare_integration(test_context: GdToolsTest, integration_value: Variant) -> Dictionary:
	var integration: Dictionary = {}
	if typeof(integration_value) == TYPE_DICTIONARY:
		integration = integration_value
	var resource_result := _load_integration_resources(integration.get("resources", {}))
	if not bool(resource_result.get("ok", false)):
		return resource_result
	var scene_result := _load_integration_scene(integration.get("scene", null))
	if not bool(scene_result.get("ok", false)):
		return scene_result
	var resources: Dictionary = resource_result.get("resources", {})
	var scene_root := scene_result.get("root") as Node
	var context = TEST_CONTEXT_SCRIPT.new()
	context.initialize(test_context, integration, scene_root, resources)
	test_context._gd_tools_set_test_context(context)
	if scene_root != null:
		test_context.add_child(scene_root)
	return {"ok": true}


func _load_integration_resources(resource_value: Variant) -> Dictionary:
	if typeof(resource_value) != TYPE_DICTIONARY:
		return _integration_error("Integration resources must be a logical-name to path dictionary")
	var resources: Dictionary = {}
	for logical_name_value in resource_value:
		var logical_name := str(logical_name_value)
		var resource_path := str(resource_value[logical_name_value])
		if not ResourceLoader.exists(resource_path):
			return _integration_error(
				"Unable to load integration resource '%s' at '%s'" % [logical_name, resource_path]
			)
		var resource := ResourceLoader.load(resource_path) as Resource
		if resource == null:
			return _integration_error(
				(
					"Integration resource '%s' did not load as Resource: %s"
					% [logical_name, resource_path]
				)
			)
		# ResourceLoader caches instances, so a per-attempt duplicate is what
		# keeps a retained, mutated resource from leaking into a retry.
		resources[logical_name] = resource.duplicate(true)
	return {"ok": true, "resources": resources}


func _load_integration_scene(scene_value: Variant) -> Dictionary:
	if scene_value == null:
		return {"ok": true, "root": null}
	var scene_path := str(scene_value)
	if not ResourceLoader.exists(scene_path):
		return _integration_error("Unable to load integration scene: %s" % scene_path)
	var packed_scene := ResourceLoader.load(scene_path) as PackedScene
	if packed_scene == null:
		return _integration_error("Integration scene did not load as PackedScene: %s" % scene_path)
	var scene_root := packed_scene.instantiate()
	if scene_root == null:
		return _integration_error("Integration scene could not be instantiated: %s" % scene_path)
	return {"ok": true, "root": scene_root}


func _integration_error(message: String) -> Dictionary:
	return {"ok": false, "message": message}


func _capture_failure_screenshot(test_context: GdToolsTest, test_name: String) -> Dictionary:
	if _screenshot_path.is_empty():
		return {
			"ok": false,
			"path": "",
			"message": "Windowed failure screenshot path was not provided",
		}
	# One capture per failing test, so a later failure cannot overwrite the
	# evidence for an earlier one in the same suite.
	var path := "%s.%s.failure.png" % [_screenshot_path, test_name]
	await RenderingServer.frame_post_draw
	var context = test_context.get_test_context()
	if context == null:
		return {
			"ok": false,
			"path": path,
			"message": "Integration context is unavailable for screenshot capture",
		}
	return context.capture_screenshot(path)


func _teardown_integration(test_context: GdToolsTest) -> void:
	var context = test_context.get_test_context()
	if context != null:
		var scene_root = context.get_scene_root() as Node
		if scene_root != null and is_instance_valid(scene_root):
			var parent := scene_root.get_parent()
			if parent != null:
				parent.remove_child(scene_root)
			scene_root.queue_free()
	test_context._gd_tools_clear_test_context()
	await process_frame


func _new_test_context(script: GDScript, suite_context: GdToolsTest):
	var test_context = script.new()
	if not (test_context is GdToolsTest):
		return null
	test_context.clear_failures()
	test_context._gd_tools_set_suite_state(suite_context._gd_tools_get_suite_state())
	_copy_script_properties(suite_context, test_context)
	return test_context


func _copy_script_properties(source: GdToolsTest, target: GdToolsTest) -> void:
	for property in source.get_property_list():
		var property_name := str(property.get("name", ""))
		var usage := int(property.get("usage", 0))
		if property_name.begins_with("_"):
			continue
		if (usage & PROPERTY_USAGE_SCRIPT_VARIABLE) == 0:
			continue
		target.set(property_name, source.get(property_name))


func _run_optional_call(
	context: GdToolsTest, method_name: String, timeout_seconds: float
) -> Dictionary:
	_begin_test_timeout(timeout_seconds)
	_test_completed = false
	_invoke_test(context, method_name, _active_test_token)
	await test_call_completed
	return {"timed_out": _test_timeout_reached}


func _run_cleanup(context: GdToolsTest, method_name: String, timeout_seconds: float) -> void:
	# A cleanup hook differs from a suite hook only in intent, not in
	# mechanism: both arm a fresh timer and await it. The await is load
	# bearing - without it this stops being a coroutine, and the caller's
	# await would return at once instead of waiting out the cleanup.
	await _run_optional_call(context, method_name, timeout_seconds)


func _activate_coverage(coverage_data: Dictionary) -> bool:
	if not bool(coverage_data.get("enabled", false)):
		return true
	var plan_path := str(coverage_data.get("plan_path", ""))
	var output_path := str(coverage_data.get("output_path", ""))
	if plan_path.is_empty() or output_path.is_empty():
		_finish_with_error("Native coverage requires both plan_path and output_path")
		return false
	if not GdToolsNativeCoverage.activate(plan_path, output_path):
		_finish_with_error("Unable to activate native coverage")
		return false
	# No test has run yet, so every engine error in the log so far was printed
	# by the collector's own load/instrument attempts. Snapshot them for the
	# demotion in _finish_with_status.
	_snapshot_activation_errors()
	_coverage_enabled = true
	return true


func _invalidate_timeout() -> void:
	# The only place _active_test_token is mutated. Every timer is bound
	# to whatever token was current when it was armed, so advancing the
	# token here makes all of them inert in _on_test_timeout and
	# _invoke_test. That is what stops a timer left over from an earlier
	# attempt from resolving a later attempt's test_call_completed.
	_active_test_token += 1


func _cancel_timeout() -> void:
	# Every exit from a test attempt must call this, including the early
	# returns. A timer that outlives its attempt does not break the test
	# it belonged to; it fires into whatever runs next.
	_invalidate_timeout()


func _begin_test_timeout(timeout_seconds: float) -> void:
	# Arming also invalidates, which is what makes the new timer the only
	# live one. This is not a cancel and must not be described as one.
	_invalidate_timeout()
	_test_timeout_reached = false
	_test_completed = false
	var timer := create_timer(timeout_seconds)
	timer.timeout.connect(_on_test_timeout.bind(_active_test_token), CONNECT_ONE_SHOT)


func _on_test_timeout(token: int) -> void:
	if token != _active_test_token or _test_completed:
		return
	_test_timeout_reached = true
	test_call_completed.emit()


func _await_test_call(context: GdToolsTest, method_name: String, arguments: Array = []) -> void:
	# Awaits the timer already armed for this attempt. Deliberately does
	# NOT arm one: re-arming here would hand every hook a fresh budget and
	# change what a declared timeout_seconds means, since a test attempt
	# gets one budget for before_each, the body and after_each together.
	# Arming happens once per attempt, in _begin_test_timeout.
	_test_completed = false
	_invoke_test(context, method_name, _active_test_token, arguments)
	await test_call_completed


func _invoke_test(
	context: GdToolsTest, method_name: String, token: int, arguments: Array = []
) -> void:
	await process_frame
	if token != _active_test_token:
		return
	if arguments.is_empty():
		await context.call(method_name)
	else:
		await context.callv(method_name, arguments)
	if token != _active_test_token or _test_timeout_reached:
		return
	_test_completed = true
	test_call_completed.emit()


func _record_suite_error(suite_name: String, message: String) -> void:
	_run_status = "error"
	_record_test_result(suite_name, "<suite>", "error", 0.0, message, {})


func _record_hook_result(
	suite_name: String,
	hook_name: String,
	failures: Array[Dictionary],
	timed_out: bool,
	timeout_seconds: float
) -> void:
	if timed_out:
		_record_test_result(
			suite_name,
			hook_name,
			"timeout",
			0.0,
			"Hook timed out after %.3f seconds" % timeout_seconds,
			{"failures": failures}
		)
	elif not failures.is_empty():
		_record_test_result(
			suite_name, hook_name, "failed", 0.0, _failure_message(failures), {"failures": failures}
		)


func _failures_since(context: GdToolsTest, start_index: int) -> Array[Dictionary]:
	var failures := context.get_failures()
	if start_index >= failures.size():
		return []
	return failures.slice(start_index)


func _record_test_result(
	suite_name: String,
	test_name: String,
	status: String,
	duration: float,
	message: String,
	diagnostics: Dictionary,
	attempts: int = 1,
	started_at: String = "",
	finished_at: String = ""
) -> void:
	if status == "failed" or status == "timeout":
		_run_status = "failed"
	elif status == "error" and _run_status != "failed":
		_run_status = "error"
	(
		_test_results
		. append(
			{
				"suite": suite_name,
				"name": test_name,
				"status": status,
				"duration_seconds": duration,
				"attempts": attempts,
				"message": message,
				"diagnostics": diagnostics,
				"started_at": started_at,
				"finished_at": finished_at,
			}
		)
	)


func _failure_message(failures: Array[Dictionary]) -> String:
	var message := ""
	for failure in failures:
		if not message.is_empty():
			message += "; "
		var failure_message := str(failure.get("message", ""))
		if failure_message.is_empty():
			failure_message = str(failure.get("assertion", "assertion failed"))
		message += failure_message
	return message


func _capture_engine_diagnostics() -> void:
	if _log_path.is_empty():
		return
	var file := FileAccess.open(_log_path, FileAccess.READ)
	if file == null:
		return
	_scan_engine_lines(file.get_as_text(), _engine_errors, _engine_warnings)
	file.close()


func _snapshot_activation_errors() -> void:
	if _log_path.is_empty():
		return
	var file := FileAccess.open(_log_path, FileAccess.READ)
	if file == null:
		return
	var activation_errors: Array[String] = []
	var ignored_warnings: Array[String] = []
	_scan_engine_lines(file.get_as_text(), activation_errors, ignored_warnings)
	file.close()
	_activation_engine_errors = activation_errors


func _scan_engine_lines(text: String, errors: Array[String], warnings: Array[String]) -> void:
	for line in text.split("\n"):
		var normalized := str(line).strip_edges()
		# `SCRIPT ERROR:` is how GDScript reports a parse error, an invalid call,
		# and a wrong-typed builtin argument. It is an engine error the run cannot
		# honestly call clean, and without matching it here such a failure reached
		# the log, left `engine_errors` empty, and exited 0 -- reporting a broken
		# test as a clean pass. Matched before `ERROR:` so the prefix trims in the
		# right order: `SCRIPT ERROR:` does not begin with `ERROR:`, but the trimmed
		# remainder of a nested `ERROR:` line does.
		if normalized.begins_with("SCRIPT ERROR:"):
			errors.append(normalized.trim_prefix("SCRIPT ERROR:").strip_edges())
		elif normalized.begins_with("ERROR:"):
			errors.append(normalized.trim_prefix("ERROR:").strip_edges())
		elif normalized.begins_with("WARNING:"):
			warnings.append(normalized.trim_prefix("WARNING:").strip_edges())


func _timestamp() -> String:
	return Time.get_datetime_string_from_system(true)


func _finish_with_error(message: String) -> void:
	_capture_engine_diagnostics()
	_run_status = "error"
	_record_test_result("<runner>", "<runner>", "error", 0.0, message, {})
	_run_finished_at = _timestamp()
	_emit_event({"event": "run_finished", "status": _run_status})
	_write_result()
	quit(2)


func _finish_with_status() -> void:
	if _coverage_enabled and not GdToolsNativeCoverage.write():
		_run_status = "error"
		_record_test_result(
			"<runner>",
			"<coverage>",
			"error",
			0.0,
			"Unable to write native coverage output",
			{},
		)
	_capture_engine_diagnostics()
	# Demote the activation-window engine errors (R1): Godot printed them
	# while the collector attempted instrumentation, so they are evidence of
	# a coverage omission rather than a run failure. Count-aware: one
	# occurrence per activation error is demoted, so an identical message
	# raised later by a test still escalates below.
	for activation_error in _activation_engine_errors:
		var index := _engine_errors.find(activation_error)
		if index != -1:
			_engine_errors.remove_at(index)
			_engine_warnings.append(activation_error)
	if _coverage_enabled:
		# R5: surface the collector's omissions through the existing warning
		# channel. Warnings never escalate the status (only _engine_errors
		# do, below), so a per-target omission cannot turn the run into an
		# error while the structured entries land in the result diagnostics.
		for omission in GdToolsNativeCoverage.get_omitted():
			_coverage_omissions.append(omission)
			_engine_warnings.append(
				(
					"Coverage target omitted: %s. %s Fix: %s"
					% [omission["path"], omission["reason"], omission["fix"]]
				)
			)
	if not _engine_errors.is_empty():
		_run_status = "error"
		_record_test_result(
			"<runner>",
			"<engine>",
			"error",
			0.0,
			"Godot engine errors were reported",
			{
				"engine_errors": _engine_errors,
				"engine_warnings": _engine_warnings,
			},
		)
	_run_finished_at = _timestamp()
	_emit_event({"event": "run_finished", "status": _run_status})
	_write_result()
	if _run_status == "error":
		quit(2)
	else:
		quit(0 if _run_status == "passed" else 1)


func _emit_event(event: Dictionary) -> void:
	var events_path := OS.get_environment("GD_TOOLS_NATIVE_EVENTS")
	if events_path.is_empty():
		return

	var directory := events_path.get_base_dir()
	if not directory.is_empty() and not DirAccess.dir_exists_absolute(directory):
		DirAccess.make_dir_recursive_absolute(directory)
	var file := FileAccess.open(events_path, FileAccess.READ_WRITE)
	if file == null:
		file = FileAccess.open(events_path, FileAccess.WRITE)
	if file == null:
		push_error("Unable to write native event stream: %s" % events_path)
		return
	file.seek_end()
	file.store_line(JSON.stringify(event))
	file.close()


func _write_result() -> void:
	var result := {
		"protocol_version": PROTOCOL_VERSION,
		"run_id": OS.get_environment("GD_TOOLS_NATIVE_RUN_ID"),
		"status": _run_status,
		"started_at": _run_started_at,
		"finished_at": _run_finished_at,
		"engine_errors": _engine_errors,
		"engine_warnings": _engine_warnings,
		"tests": _test_results,
	}
	if not _coverage_omissions.is_empty():
		result["diagnostics"] = {"coverage_omissions": _coverage_omissions}
	var result_path := OS.get_environment("GD_TOOLS_NATIVE_RESULT")
	if result_path.is_empty():
		print(JSON.stringify(result, "\t"))
		return

	var directory := result_path.get_base_dir()
	if not directory.is_empty() and not DirAccess.dir_exists_absolute(directory):
		DirAccess.make_dir_recursive_absolute(directory)

	var temporary_path := result_path + ".tmp"
	var file := FileAccess.open(temporary_path, FileAccess.WRITE)
	if file == null:
		push_error("Unable to write native result: %s" % temporary_path)
		return
	file.store_string(JSON.stringify(result, "\t") + "\n")
	file.close()
	var rename_error := DirAccess.rename_absolute(temporary_path, result_path)
	if rename_error != OK:
		push_error("Unable to finalize native result: %s" % result_path)
