extends SceneTree

const PROTOCOL_VERSION := 2
const SUITE_FIELDS := ["scene", "resources", "mode", "tests"]
const PER_TEST_FIELDS := ["scene", "resources"]
const ERROR_KEY := "__gdtools_preflight_error__"


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var result_path := OS.get_environment("GD_TOOLS_NATIVE_PREFLIGHT_RESULT")
	if result_path.is_empty():
		push_error("GD_TOOLS_NATIVE_PREFLIGHT_RESULT is not set")
		quit(2)
		return

	var manifest_path := OS.get_environment("GD_TOOLS_NATIVE_PREFLIGHT_MANIFEST")
	if manifest_path.is_empty():
		_finish_error(result_path, "GD_TOOLS_NATIVE_PREFLIGHT_MANIFEST is not set")
		return

	var result := _build_preflight_result(manifest_path)
	if not _write_result(result_path, result):
		quit(2)
		return
	quit(0 if result["status"] == "ok" else 2)


func _build_preflight_result(manifest_path: String) -> Dictionary:
	var manifest_result := _read_json(manifest_path)
	if manifest_result.has(ERROR_KEY):
		return _error_result(str(manifest_result[ERROR_KEY]))
	var manifest_value: Variant = manifest_result["value"]
	if typeof(manifest_value) != TYPE_DICTIONARY:
		return _error_result("Discovery manifest must be a JSON object")
	var manifest: Dictionary = manifest_value

	var protocol_version: Variant = manifest.get("protocol_version")
	var protocol_type := typeof(protocol_version)
	if (
		(protocol_type != TYPE_INT and protocol_type != TYPE_FLOAT)
		or int(protocol_version) != PROTOCOL_VERSION
	):
		return _error_result(
			"Discovery manifest requires protocol_version 2; received %s" % [str(protocol_version)]
		)
	return _build_suites_result(manifest.get("suites", []))


func _build_suites_result(raw_suites: Variant) -> Dictionary:
	if typeof(raw_suites) != TYPE_ARRAY:
		return _error_result("Discovery manifest suites must be an array")
	var suites: Array = []
	for raw_suite: Variant in raw_suites:
		var resolved := _resolve_suite(raw_suite)
		if resolved.has(ERROR_KEY):
			return _error_result(str(resolved[ERROR_KEY]))
		suites.append(resolved)
	return {
		"protocol_version": PROTOCOL_VERSION,
		"status": "ok",
		"suites": suites,
		"error": null,
	}


func _error_result(message: String) -> Dictionary:
	return {
		"protocol_version": PROTOCOL_VERSION,
		"status": "error",
		"suites": [],
		"error": message,
	}


func _resolve_suite(raw_suite: Variant) -> Dictionary:
	if typeof(raw_suite) != TYPE_DICTIONARY:
		return _error("Each discovery manifest suite must be an object")
	var suite: Dictionary = (raw_suite as Dictionary).duplicate(true)
	var path_result := _suite_path(suite)
	if path_result.has(ERROR_KEY):
		return path_result
	var suite_path: String = path_result["value"]
	var script_result := _load_suite_script(suite_path)
	if script_result.has(ERROR_KEY):
		return script_result
	var script: Script = script_result["value"]
	var method_names := _test_method_names(script)
	var tests_result := _validate_manifest_tests(suite_path, suite.get("tests", []), method_names)
	if tests_result.has(ERROR_KEY):
		return tests_result

	var constants: Dictionary = script.get_script_constant_map()
	var raw_integration: Variant = constants.get("INTEGRATION", {})
	var integration_result := _resolve_integration(suite_path, raw_integration, method_names)
	if integration_result.has(ERROR_KEY):
		return integration_result
	var defaults: Dictionary = integration_result["defaults"]
	var overrides: Dictionary = integration_result["overrides"]
	_resolve_suite_tests(suite, defaults, overrides)
	suite["integration"] = defaults
	return suite


func _suite_path(suite: Dictionary) -> Dictionary:
	var suite_path_value: Variant = suite.get("path")
	if typeof(suite_path_value) != TYPE_STRING:
		return _error("Suite path must be a string")
	var suite_path: String = suite_path_value
	if not suite_path.begins_with("res://"):
		return _error("Suite path '%s' must start with 'res://'" % suite_path)
	return {"value": suite_path}


func _load_suite_script(suite_path: String) -> Dictionary:
	if not ResourceLoader.exists(suite_path):
		return _error("Unable to load suite script '%s': file does not exist" % suite_path)
	var script := ResourceLoader.load(suite_path) as Script
	if script == null:
		return _error("Unable to load suite script '%s'" % suite_path)
	return {"value": script}


func _validate_manifest_tests(
	suite_path: String, raw_tests: Variant, method_names: Dictionary
) -> Dictionary:
	if typeof(raw_tests) != TYPE_ARRAY:
		return _error("Suite '%s' tests must be an array" % suite_path)
	for raw_test: Variant in raw_tests:
		if typeof(raw_test) != TYPE_DICTIONARY:
			return _error("Suite '%s' test entries must be objects" % suite_path)
		var test_name: Variant = (raw_test as Dictionary).get("name")
		if typeof(test_name) != TYPE_STRING:
			return _error("Suite '%s' test names must be strings" % suite_path)
		if not method_names.has(test_name):
			return _error("Suite '%s' references unknown test '%s'" % [suite_path, test_name])
	return {}


func _resolve_suite_tests(suite: Dictionary, defaults: Dictionary, overrides: Dictionary) -> void:
	var resolved_tests: Array = []
	for raw_test: Variant in suite.get("tests", []):
		var test: Dictionary = (raw_test as Dictionary).duplicate(true)
		var test_name: String = test["name"]
		var override: Dictionary = overrides.get(test_name, {})
		test["integration"] = _merge_test_integration(defaults, override)
		resolved_tests.append(test)
	suite["tests"] = resolved_tests


func _test_method_names(script: Script) -> Dictionary:
	var names: Dictionary = {}
	for method_value: Variant in script.get_script_method_list():
		if typeof(method_value) != TYPE_DICTIONARY:
			continue
		var method: Dictionary = method_value
		var method_name_value: Variant = method.get("name")
		if typeof(method_name_value) != TYPE_STRING:
			continue
		var method_name: String = method_name_value
		if not method_name.begins_with("test_"):
			continue
		var arguments: Variant = method.get("args", [])
		if typeof(arguments) != TYPE_ARRAY:
			continue
		# Discovery only selects no-argument test methods, so a parameterized
		# method is not a runnable test here either. Treating it as known would
		# let an override validate for a test that is never executed.
		if (arguments as Array).is_empty():
			names[method_name] = true
	return names


func _resolve_integration(
	suite_path: String, raw_integration: Variant, method_names: Dictionary
) -> Dictionary:
	if typeof(raw_integration) != TYPE_DICTIONARY:
		return _error("INTEGRATION in '%s' must be a dictionary" % suite_path)
	var raw: Dictionary = raw_integration
	var fields_result := _validate_integration_fields(suite_path, raw)
	if fields_result.has(ERROR_KEY):
		return fields_result
	var defaults_result := _resolve_default_integration(suite_path, raw)
	if defaults_result.has(ERROR_KEY):
		return defaults_result
	var overrides_result := _resolve_test_overrides(suite_path, raw, method_names)
	if overrides_result.has(ERROR_KEY):
		return overrides_result
	return {
		"defaults": defaults_result["value"],
		"overrides": overrides_result["value"],
	}


func _validate_integration_fields(suite_path: String, raw: Dictionary) -> Dictionary:
	for field: Variant in raw.keys():
		if not SUITE_FIELDS.has(field):
			return _error("INTEGRATION in '%s' has unknown field '%s'" % [suite_path, field])
	return {}


func _resolve_default_integration(suite_path: String, raw: Dictionary) -> Dictionary:
	var scene: Variant = null
	if raw.has("scene"):
		var scene_result := _validate_path(
			raw["scene"], "INTEGRATION scene in '%s'" % suite_path, true
		)
		if scene_result.has(ERROR_KEY):
			return scene_result
		scene = scene_result["value"]

	var resources: Dictionary = {}
	if raw.has("resources"):
		var resources_result := _resolve_resource_map(
			raw["resources"], "INTEGRATION resources in '%s'" % suite_path, false
		)
		if resources_result.has(ERROR_KEY):
			return resources_result
		resources = resources_result["value"]

	var mode: String = "headless"
	if raw.has("mode"):
		var mode_value: Variant = raw["mode"]
		if (
			typeof(mode_value) != TYPE_STRING
			or mode_value != "headless" and mode_value != "windowed"
		):
			return _error(
				"INTEGRATION mode in '%s' must be 'headless' or 'windowed'" % [suite_path]
			)
		mode = mode_value
	return {
		"value":
		{
			"scene": scene,
			"resources": resources.duplicate(true),
			"mode": mode,
		}
	}


func _resolve_test_overrides(
	suite_path: String, raw: Dictionary, method_names: Dictionary
) -> Dictionary:
	var overrides: Dictionary = {}
	if not raw.has("tests"):
		return {"value": overrides}
	var raw_overrides: Variant = raw["tests"]
	if typeof(raw_overrides) != TYPE_DICTIONARY:
		return _error("INTEGRATION tests in '%s' must be a dictionary" % suite_path)
	for test_name: Variant in raw_overrides:
		if typeof(test_name) != TYPE_STRING:
			return _error("INTEGRATION test names in '%s' must be strings" % suite_path)
		if not method_names.has(test_name):
			return _error(
				"INTEGRATION in '%s' references unknown test '%s'" % [suite_path, test_name]
			)
		var override_result := _resolve_test_override(
			suite_path, test_name, raw_overrides[test_name]
		)
		if override_result.has(ERROR_KEY):
			return override_result
		overrides[test_name] = override_result["value"]
	return {"value": overrides}


func _resolve_test_override(
	suite_path: String, test_name: String, raw_override: Variant
) -> Dictionary:
	if typeof(raw_override) != TYPE_DICTIONARY:
		return _error(
			(
				"INTEGRATION declaration for test '%s' in '%s' must be an object"
				% [test_name, suite_path]
			)
		)
	var raw: Dictionary = raw_override
	for field: Variant in raw.keys():
		if not PER_TEST_FIELDS.has(field):
			return _error(
				(
					"per-test declarations do not support field '%s' for '%s' in '%s'"
					% [field, test_name, suite_path]
				)
			)

	var override: Dictionary = {}
	if raw.has("scene"):
		var scene_result := _validate_path(
			raw["scene"], "Scene for test '%s' in '%s'" % [test_name, suite_path], true
		)
		if scene_result.has(ERROR_KEY):
			return scene_result
		override["scene"] = scene_result["value"]
	if raw.has("resources"):
		var resources_result := _resolve_resource_map(
			raw["resources"], "Resources for test '%s' in '%s'" % [test_name, suite_path], true
		)
		if resources_result.has(ERROR_KEY):
			return resources_result
		override["resources"] = resources_result["value"]
	return {"value": override}


func _resolve_resource_map(raw_resources: Variant, label: String, allow_null: bool) -> Dictionary:
	if typeof(raw_resources) != TYPE_DICTIONARY:
		return _error("%s; resources must be a dictionary" % label)
	var resources: Dictionary = {}
	for logical_value: Variant in raw_resources:
		if typeof(logical_value) != TYPE_STRING:
			return _error("%s logical names must be strings" % label)
		var logical_name: String = logical_value
		if logical_name.strip_edges().is_empty():
			return _error("%s logical names must not be empty" % label)
		var resource_value: Variant = raw_resources[logical_value]
		if resource_value == null:
			if not allow_null:
				return _error("%s resource '%s' must be a res:// path" % [label, logical_name])
			resources[logical_name] = null
			continue
		var path_result := _validate_path(
			resource_value, "Resource '%s' in %s" % [logical_name, label], false
		)
		if path_result.has(ERROR_KEY):
			return path_result
		resources[logical_name] = path_result["value"]
	return {"value": resources}


func _validate_path(value: Variant, label: String, allow_null: bool) -> Dictionary:
	if value == null and allow_null:
		return {"value": null}
	if typeof(value) != TYPE_STRING:
		return _error("%s must be a res:// path or null" % label)
	var path: String = value
	if not path.begins_with("res://"):
		return _error("%s must start with 'res://'" % label)
	if not ResourceLoader.exists(path):
		return _error("%s does not exist: '%s'" % [label, path])
	return {"value": path}


func _merge_test_integration(defaults: Dictionary, override: Dictionary) -> Dictionary:
	var scene: Variant = defaults["scene"]
	if override.has("scene"):
		scene = override["scene"]
	var resources: Dictionary = (defaults["resources"] as Dictionary).duplicate(true)
	if override.has("resources"):
		for logical_name: Variant in override["resources"]:
			var resource_value: Variant = override["resources"][logical_name]
			if resource_value == null:
				resources.erase(logical_name)
			else:
				resources[logical_name] = resource_value
	return {
		"scene": scene,
		"resources": resources,
	}


func _read_json(path: String) -> Dictionary:
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		return _error("Unable to read discovery manifest '%s'" % path)
	var content := file.get_as_text()
	file.close()
	var parsed: Variant = JSON.parse_string(content)
	if parsed == null and content.strip_edges() != "null":
		return _error("Discovery manifest '%s' is not valid JSON" % path)
	return {"value": parsed}


func _finish_error(result_path: String, message: String) -> void:
	if not _write_result(
		result_path,
		{
			"protocol_version": PROTOCOL_VERSION,
			"status": "error",
			"suites": [],
			"error": message,
		}
	):
		quit(2)
		return
	quit(2)


func _write_result(result_path: String, result: Dictionary) -> bool:
	var directory := result_path.get_base_dir()
	if not directory.is_empty() and not DirAccess.dir_exists_absolute(directory):
		var directory_error := DirAccess.make_dir_recursive_absolute(directory)
		if directory_error != OK:
			push_error("Unable to create native preflight result directory: %s" % [directory])
			return false

	var temporary_path := result_path + ".tmp"
	var file := FileAccess.open(temporary_path, FileAccess.WRITE)
	if file == null:
		push_error("Unable to write native preflight result: %s" % temporary_path)
		return false
	file.store_string(JSON.stringify(result, "\t") + "\n")
	file.close()

	var rename_error := DirAccess.rename_absolute(temporary_path, result_path)
	if rename_error != OK and FileAccess.file_exists(result_path):
		var remove_error := DirAccess.remove_absolute(result_path)
		if remove_error == OK:
			rename_error = DirAccess.rename_absolute(temporary_path, result_path)
	if rename_error != OK:
		push_error("Unable to finalize native preflight result: %s" % result_path)
		return false
	return true


func _error(message: String) -> Dictionary:
	return {ERROR_KEY: message}
