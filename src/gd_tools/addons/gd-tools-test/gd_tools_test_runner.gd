extends SceneTree

## Headless entrypoint for the gd-tools native test runtime.
##
## The Python orchestrator writes a manifest and result path into the
## environment before launching Godot with this script. The runner executes
## one manifest and exits with 0 for passing tests, 1 for test failures, and
## 2 for protocol/runtime errors.

const PROTOCOL_VERSION := 1

var _test_results: Array[Dictionary] = []
var _run_status := "passed"


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var manifest := _load_manifest()
	if manifest.is_empty():
		return

	if int(manifest.get("protocol_version", -1)) != PROTOCOL_VERSION:
		_finish_with_error(
			"Unsupported native protocol version: %s" % manifest.get("protocol_version", "")
		)
		return

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
	var script := load(suite_path) as GDScript
	if script == null:
		_record_suite_error(suite_name, "Unable to load suite: %s" % suite_path)
		return

	var before_context = script.new()
	if not (before_context is GdToolsTest):
		_record_suite_error(suite_name, "Suite does not extend GdToolsTest")
		return
	get_root().add_child(before_context)
	if before_context.has_method("before_all"):
		await before_context.call("before_all")
	before_context.queue_free()
	await process_frame

	for test_data in suite_data.get("tests", []):
		await _run_test(script, suite_name, test_data)

	var after_context = script.new()
	if not (after_context is GdToolsTest):
		_record_suite_error(suite_name, "Suite does not extend GdToolsTest")
		return
	get_root().add_child(after_context)
	if after_context.has_method("after_all"):
		await after_context.call("after_all")
	after_context.queue_free()
	await process_frame


func _run_test(script: GDScript, suite_name: String, test_data: Dictionary) -> void:
	var test_name := str(test_data.get("name", ""))
	var test_context = script.new()
	if not (test_context is GdToolsTest):
		_record_test_result(
			suite_name,
			test_name,
			"error",
			0.0,
			"Suite does not extend GdToolsTest",
			{},
		)
		return

	get_root().add_child(test_context)
	var started_at := Time.get_ticks_msec()
	if test_context.has_method("before_each"):
		await test_context.call("before_each")

	if test_context.has_method(test_name):
		await test_context.call(test_name)
	else:
		_record_suite_error(suite_name, "Test method not found: %s" % test_name)

	if test_context.has_method("after_each"):
		await test_context.call("after_each")

	var failures: Array[Dictionary] = test_context.get_failures()
	var status := "failed" if not failures.is_empty() else "passed"
	var message := _failure_message(failures)
	_record_test_result(
		suite_name,
		test_name,
		status,
		float(Time.get_ticks_msec() - started_at) / 1000.0,
		message,
		{"failures": failures},
	)
	test_context.queue_free()
	await process_frame


func _record_suite_error(suite_name: String, message: String) -> void:
	_run_status = "error"
	_record_test_result(suite_name, "<suite>", "error", 0.0, message, {})


func _record_test_result(
		suite_name: String,
		test_name: String,
		status: String,
		duration: float,
		message: String,
		diagnostics: Dictionary
) -> void:
	if status == "failed":
		_run_status = "failed"
	elif status == "error" and _run_status != "failed":
		_run_status = "error"
	_test_results.append({
		"suite": suite_name,
		"name": test_name,
		"status": status,
		"duration_seconds": duration,
		"attempts": 1,
		"message": message,
		"diagnostics": diagnostics,
	})


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


func _finish_with_error(message: String) -> void:
	_run_status = "error"
	_record_test_result("<runner>", "<runner>", "error", 0.0, message, {})
	_write_result()
	quit(2)


func _finish_with_status() -> void:
	_write_result()
	quit(0 if _run_status == "passed" else 1)


func _write_result() -> void:
	var result := {
		"protocol_version": PROTOCOL_VERSION,
		"run_id": OS.get_environment("GD_TOOLS_NATIVE_RUN_ID"),
		"status": _run_status,
		"tests": _test_results,
	}
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
