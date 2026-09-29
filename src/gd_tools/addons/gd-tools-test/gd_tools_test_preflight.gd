extends SceneTree

const PROTOCOL_VERSION := 2
const SUITE_FIELDS := ["scene", "resources", "mode", "tests"]
const PER_TEST_FIELDS := ["scene", "resources"]
const ERROR_KEY := "__gdtools_preflight_error__"
const PARAMETER_NAMING = preload("res://addons/gd-tools-test/gd_tools_parameter_naming.gd")


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
	var arities := _test_method_arities(script)
	var parameterization_result := _resolve_parameterization(suite_path, script, arities, suite)
	var tests_result := _validate_manifest_tests(suite_path, suite.get("tests", []), method_names)
	var use_parameters_result := _resolve_use_parameters(suite_path, script, arities, suite)
	var selectors_result := _apply_case_selectors(suite_path, arities, suite)
	var failure: Dictionary = _first_error(
		[parameterization_result, tests_result, use_parameters_result, selectors_result]
	)
	if failure.has(ERROR_KEY):
		return failure

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
	# Godot 4.7+ loads parse-error scripts as non-null resources, so only
	# `can_instantiate()` reveals the broken state; validating tests against
	# such a script would produce a confusing "unknown test" error instead
	# of pointing at the unloadable suite.
	if script == null or not script.can_instantiate():
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
		# A ``method[case]`` selector addresses one expanded case; validate
		# the owning method here and let case filtering report selectors
		# that match no declared case.
		var base_name: String = _parse_case_selector(test_name)["method"]
		if not method_names.has(base_name):
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
		names[method_name] = true
	return names


func _test_method_arities(script: Script) -> Dictionary:
	## Parameter counts for every ``test_*`` method, including defaults.
	var arities: Dictionary = {}
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
		arities[method_name] = (arguments as Array).size()
	return arities


func _resolve_parameterization(
	suite_path: String, script: Script, arities: Dictionary, suite: Dictionary
) -> Dictionary:
	## Validate the suite's ``parameterize`` declaration and attach case
	## metadata to every manifest test it covers.
	var declaration_result := _extract_parameterize_declaration(suite_path, script)
	if declaration_result.has(ERROR_KEY):
		return declaration_result
	var declaration: Variant = declaration_result["value"]

	var parameterized: Array = []
	for method_name: Variant in arities:
		if int(arities[method_name]) > 0:
			parameterized.append(String(method_name))
	parameterized.sort()

	if declaration == null:
		if parameterized.is_empty():
			return {}
		var first: String = parameterized[0]
		return _error(
			(
				(
					"Suite '%s' test method '%s' takes %d parameters but no"
					+ " parameterize declaration was found in before_all"
				)
				% [suite_path, first, int(arities[first])]
			)
		)

	var names: Array = declaration["names"]
	var values: Array = declaration["values"]
	var expected := names.size()
	var matched := 0
	for method_name: Variant in parameterized:
		var arity := int(arities[method_name])
		if arity != expected:
			return _error(
				(
					(
						"Suite '%s' test method '%s' takes %d parameters but the"
						+ " parameterize declaration provides %d"
					)
					% [suite_path, method_name, arity, expected]
				)
			)
		matched += 1
	if matched == 0:
		return _error(
			(
				(
					"parameterize declaration in '%s' does not match any test"
					+ " method (expected a test taking %d parameter(s))"
				)
				% [suite_path, expected]
			)
		)
	for raw_test: Variant in suite.get("tests", []):
		var test := raw_test as Dictionary
		var base: String = _parse_case_selector(str(test.get("name", "")))["method"]
		if int(arities.get(base, -1)) == expected:
			test["parameters"] = {
				"names": names.duplicate(true),
				"values": values.duplicate(true),
			}
	return {}


func _apply_case_selectors(
	suite_path: String, arities: Dictionary, suite: Dictionary
) -> Dictionary:
	## Trim parameterized declarations to ``method[case]`` selections and
	## rewrite each selected entry to its owning method so the runner sees
	## exactly one case per selector.
	for raw_test: Variant in suite.get("tests", []):
		var test := raw_test as Dictionary
		var name := str(test.get("name", ""))
		var selector := _parse_case_selector(name)
		if str(selector["case"]) == "":
			continue
		var base := str(selector["method"])
		if not arities.has(base):
			# Unknown tests are reported by manifest validation.
			continue
		if typeof(test.get("parameters")) != TYPE_DICTIONARY:
			return _error("Suite '%s' test method '%s' is not parameterized" % [suite_path, base])
		var values: Array = test["parameters"]["values"]
		var selected: Array = []
		for case_index in values.size():
			var suffix := PARAMETER_NAMING.case_suffix(values[case_index], case_index)
			if suffix == "[%s]" % selector["case"]:
				selected.append(values[case_index])
		if selected.is_empty():
			return _error(
				"Suite '%s' test '%s' has no case '[%s]'" % [suite_path, base, selector["case"]]
			)
		test["parameters"]["values"] = selected
		test["name"] = base
	return {}


func _extract_parameterize_declaration(suite_path: String, script: Script) -> Dictionary:
	## Statically extract the single ``parameterize`` call from before_all.
	var source := script.get_source_code()
	var body := _method_body(source, "before_all")
	var call_result := _extract_call_arguments(body, "parameterize")
	if call_result.has(ERROR_KEY):
		return call_result
	return _resolve_parameterize_declaration(suite_path, call_result["value"])


func _resolve_parameterize_declaration(suite_path: String, calls: Array) -> Dictionary:
	if calls.is_empty():
		return {"value": null}
	if calls.size() > 1:
		return _error(
			(
				(
					"Suite '%s' has %d parameterize calls in before_all;"
					+ " exactly one parameterize declaration is supported"
				)
				% [suite_path, calls.size()]
			)
		)
	var arguments: Array = calls[0]
	if arguments.size() != 2:
		return _error(
			(
				(
					"parameterize declaration in '%s' takes two arguments"
					+ " (names, values); received %d"
				)
				% [suite_path, arguments.size()]
			)
		)
	var names_result := _evaluate_expression(suite_path, "names", arguments[0])
	var values_result := _evaluate_expression(suite_path, "values", arguments[1])
	var expression_error := _first_error([names_result, values_result])
	if expression_error.has(ERROR_KEY):
		return expression_error
	var names: Variant = names_result["value"]
	var values: Variant = values_result["value"]
	return _checked_metadata(suite_path, "parameterize names", names, values)


func _first_error(results: Array) -> Dictionary:
	for result: Variant in results:
		if (result as Dictionary).has(ERROR_KEY):
			return result
	return {}


func _resolve_use_parameters(
	suite_path: String, script: Script, arities: Dictionary, suite: Dictionary
) -> Dictionary:
	## Statically resolve ``use_parameters`` declarations inside test bodies.
	for raw_test: Variant in suite.get("tests", []):
		var result := _resolve_test_use_parameters(
			suite_path, script, arities, raw_test as Dictionary
		)
		if result.has(ERROR_KEY):
			return result
	return {}


func _resolve_test_use_parameters(
	suite_path: String, script: Script, arities: Dictionary, test: Dictionary
) -> Dictionary:
	var method_name := str(test.get("name", ""))
	var body := _method_body(script.get_source_code(), method_name)
	var call_result := _extract_call_arguments(body, "use_parameters")
	if call_result.has(ERROR_KEY):
		return call_result
	var calls: Array = call_result["value"]
	if calls.is_empty():
		return {}
	var metadata_result := _use_parameters_metadata(
		suite_path, method_name, int(arities.get(method_name, 0)), calls
	)
	if metadata_result.has(ERROR_KEY):
		return metadata_result
	test["parameters"] = metadata_result["value"]
	return {}


func _use_parameters_metadata(
	suite_path: String, method_name: String, arity: int, calls: Array
) -> Dictionary:
	if calls.size() > 1:
		return _error(
			(
				(
					"Suite '%s' test method '%s' has %d use_parameters calls;"
					+ " exactly one use_parameters call is supported"
				)
				% [suite_path, method_name, calls.size()]
			)
		)
	if arity > 0:
		return _error(
			(
				(
					"Suite '%s' test method '%s' cannot combine signature"
					+ " parameters with use_parameters"
				)
				% [suite_path, method_name]
			)
		)
	var arguments: Array = calls[0]
	if arguments.size() != 1:
		return _error(
			(
				("use_parameters declaration in '%s' takes one argument" + " (values); received %d")
				% [suite_path, arguments.size()]
			)
		)
	var values_result := _evaluate_expression(suite_path, "values", arguments[0])
	if values_result.has(ERROR_KEY):
		return values_result
	return _use_parameters_metadata_shape(suite_path, values_result["value"])


func _use_parameters_metadata_shape(suite_path: String, declared: Variant) -> Dictionary:
	if typeof(declared) == TYPE_DICTIONARY:
		# The GUT legacy convention: each dictionary entry is one case and the
		# test body receives the entry's value through use_parameters. The keys
		# become the case identifiers, so the metadata values carry the keys
		# for naming only -- runtime injection reads the test's own dictionary.
		var dictionary: Dictionary = declared
		var values: Array = []
		for key: Variant in dictionary:
			values.append([key])
		return _checked_metadata(suite_path, "use_parameters keys", ["value"], values)
	if typeof(declared) != TYPE_ARRAY:
		return _error(
			(
				(
					"Suite '%s' use_parameters declaration must be an array of"
					+ " values or a dictionary of named values"
				)
				% suite_path
			)
		)
	var values: Array = []
	for value: Variant in declared:
		values.append([value])
	return _checked_metadata(suite_path, "use_parameters values", ["value"], values)


func _checked_metadata(
	suite_path: String, label: String, names: Variant, values: Variant
) -> Dictionary:
	var shape_error := _first_error(
		[
			_validate_parameter_names(suite_path, names, label),
			_validate_parameter_values(suite_path, values, names),
			_validate_json_safe(suite_path, values, "parameter values"),
		]
	)
	if shape_error.has(ERROR_KEY):
		return shape_error
	var normalized_values: Array = []
	for value_set: Variant in values:
		normalized_values.append(PARAMETER_NAMING.normalize_value_set(value_set))
	return {
		"value":
		{
			"names": (names as Array).duplicate(true),
			"values": normalized_values,
		},
	}


func _parse_case_selector(name: String) -> Dictionary:
	var selector := RegEx.create_from_string("^(test_\\w+)\\[(.+)\\]$")
	var matched := selector.search(name)
	if matched == null:
		return {"method": name, "case": ""}
	return {"method": matched.get_string(1), "case": matched.get_string(2)}


func _method_body(source: String, method_name: String) -> String:
	var lines := source.split("\n")
	var start := -1
	var declaration := RegEx.create_from_string("^func\\s+%s\\s*\\(" % method_name)
	for index in lines.size():
		if declaration.search(String(lines[index])) != null:
			start = index
			break
	if start == -1:
		return ""
	var body: Array[String] = []
	for index in range(start + 1, lines.size()):
		var line := String(lines[index])
		if line.begins_with("func "):
			break
		# Comment-only lines are dropped so a commented-out declaration is
		# never mistaken for a live one; inline comments are still handled
		# by the call-argument scanner.
		if not line.strip_edges().begins_with("#"):
			body.append(line)
	return "\n".join(body)


func _extract_call_arguments(body: String, call_name: String) -> Dictionary:
	var regex := RegEx.create_from_string("(?<![\\w.])" + call_name + "\\s*\\(")
	var strings := _string_spans(body)
	var calls: Array = []
	for match: Variant in regex.search_all(body):
		if _offset_in_spans(strings, (match as RegExMatch).get_start()):
			# The match only mentions the API inside a string literal or a
			# trailing comment, not a live call; skip it.
			continue
		var content := _balanced_paren_content(body, (match as RegExMatch).get_end())
		if content.has(ERROR_KEY):
			return content
		calls.append(_split_top_level_arguments(String(content["value"])))
	return {"value": calls}


func _string_spans(source: String) -> Array:
	# Character ranges covered by string literals and comments, so call
	# scanning can skip matches that merely mention an API name there.
	var spans: Array = []
	var index := 0
	while index < source.length():
		var character := source[index]
		if character == "#":
			var comment_end := source.find("\n", index)
			if comment_end == -1:
				comment_end = source.length()
			spans.append([index, comment_end])
			index = comment_end
			continue
		if character == '"' or character == "'":
			var end := _skip_string(source, index)
			spans.append([index, end])
			index = end
			continue
		index += 1
	return spans


func _offset_in_spans(spans: Array, offset: int) -> bool:
	for span: Variant in spans:
		if offset >= span[0] and offset < span[1]:
			return true
	return false


func _balanced_paren_content(source: String, start: int) -> Dictionary:
	var depth := 1
	var index := start
	while index < source.length():
		var character := source[index]
		if character == "#":
			while index < source.length() and source[index] != "\n":
				index += 1
			continue
		if character == '"' or character == "'":
			index = _skip_string(source, index)
			continue
		if character == "(":
			depth += 1
		elif character == ")":
			depth -= 1
			if depth == 0:
				return {"value": source.substr(start, index - start)}
		index += 1
	return _error("parameterize call is missing its closing parenthesis")


func _skip_string(source: String, start: int) -> int:
	var quote := source[start]
	var index := start + 1
	while index < source.length():
		var character := source[index]
		if character == "\\":
			index += 2
			continue
		if character == quote:
			return index + 1
		index += 1
	return index


func _split_top_level_arguments(source: String) -> Array:
	var arguments: Array = []
	var depth := 0
	var start := 0
	var index := 0
	while index < source.length():
		var character := source[index]
		if character == '"' or character == "'":
			index = _skip_string(source, index)
			continue
		if character == "(" or character == "[" or character == "{":
			depth += 1
		elif character == ")" or character == "]" or character == "}":
			depth -= 1
		elif character == "," and depth == 0:
			arguments.append(source.substr(start, index - start).strip_edges())
			start = index + 1
		index += 1
	arguments.append(source.substr(start).strip_edges())
	return arguments


func _evaluate_expression(suite_path: String, label: String, source: String) -> Dictionary:
	var expression := Expression.new()
	if expression.parse(source) != Error.OK:
		return _error(
			(
				"parameterize %s in '%s' must be a literal expression (%s)"
				% [label, suite_path, expression.get_error_text()]
			)
		)
	var value: Variant = expression.execute([], null, false)
	if expression.has_execute_failed():
		return _error(
			(
				(
					"parameterize %s in '%s' must be literal values that preflight"
					+ " can evaluate without running the suite (%s)"
				)
				% [label, suite_path, expression.get_error_text()]
			)
		)
	return {"value": value}


func _validate_parameter_names(
	suite_path: String, names: Variant, label: String = "parameterize names"
) -> Dictionary:
	if typeof(names) != TYPE_ARRAY:
		return _error("Suite '%s' %s must be an array of strings" % [suite_path, label])
	var seen: Dictionary = {}
	for name_value: Variant in names:
		if typeof(name_value) != TYPE_STRING or (name_value as String).strip_edges().is_empty():
			return _error("Suite '%s' %s must be non-empty strings" % [suite_path, label])
		if seen.has(name_value):
			return _error("Suite '%s' duplicate parameter name '%s'" % [suite_path, name_value])
		seen[name_value] = true
	if (names as Array).is_empty():
		return _error("Suite '%s' %s must not be empty" % [suite_path, label])
	return {}


func _validate_parameter_values(suite_path: String, values: Variant, names: Variant) -> Dictionary:
	if typeof(names) != TYPE_ARRAY:
		# The names check already reports the malformed declaration; skip the
		# row-shape comparison rather than comparing against a non-array.
		return {}
	if typeof(values) != TYPE_ARRAY:
		return _error("Suite '%s' parameterize values must be an array of value sets" % suite_path)
	for index in values.size():
		var value_set: Variant = values[index]
		if typeof(value_set) != TYPE_ARRAY:
			return _error("Suite '%s' parameter set %d must be an array" % [suite_path, index])
		if (value_set as Array).size() != names.size():
			return _error(
				(
					"Suite '%s' parameter set %d has %d value(s); expected %d"
					% [suite_path, index, (value_set as Array).size(), names.size()]
				)
			)
	return {}


func _validate_json_safe(suite_path: String, value: Variant, label: String) -> Dictionary:
	match typeof(value):
		TYPE_NIL, TYPE_BOOL, TYPE_INT, TYPE_FLOAT, TYPE_STRING:
			return {}
		TYPE_ARRAY:
			for element: Variant in value:
				var result := _validate_json_safe(suite_path, element, label)
				if result.has(ERROR_KEY):
					return result
			return {}
		TYPE_DICTIONARY:
			return _validate_json_safe_dictionary(suite_path, value, label)
		_:
			return _error("Suite '%s' %s must be JSON-serializable literals" % [suite_path, label])


func _validate_json_safe_dictionary(
	suite_path: String, dictionary: Dictionary, label: String
) -> Dictionary:
	# Dictionaries are JSON-serializable when their keys are strings; JSON
	# coerces other key types, which would silently change the values the
	# runner injects.
	for key: Variant in dictionary:
		if typeof(key) != TYPE_STRING:
			return _error("Suite '%s' %s dictionary keys must be strings" % [suite_path, label])
		var result := _validate_json_safe(suite_path, dictionary[key], label)
		if result.has(ERROR_KEY):
			return result
	return {}


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
