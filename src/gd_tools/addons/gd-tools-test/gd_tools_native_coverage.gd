class_name GdToolsNativeCoverage
extends RefCounted

## Transient native coverage collector for the gd-tools test runner.
##
## The Python side supplies the existing instrumentation plan. This
## class instruments scripts in memory, tracks hits through a static class
## callable, and writes the same JSON shape consumed by the Python reporter.

## Every branch_type this collector knows how to measure. A plan that
## carries anything else was produced by a newer plan generator than
## this collector implements; instrumenting it would silently
## mis-measure the unknown arms, so activation is refused instead.
const KNOWN_BRANCH_TYPES: Array[String] = [
	"if_true",
	"elif_true",
	"if_false",
	"loop_body",
	"match_case",
	"ternary_true",
	"ternary_false",
	"and_site",
	"and_right",
	"and_short",
	"or_site",
	"or_right",
	"or_short",
	"assert_true",
	"assert_false",
]

static var _hits: Dictionary = {}
static var _active := false
static var _output_path := ""
static var _omitted: Array = []
static var _derived: Dictionary = {}


static func activate(plan_path: String, output_path: String) -> bool:
	## Instrument all files in a plan and enable hit collection.
	_hits.clear()
	_active = false
	_output_path = output_path
	_omitted.clear()
	_derived.clear()

	if plan_path.is_empty() or not FileAccess.file_exists(plan_path):
		push_error("[gd-tools] Native coverage plan not found: %s" % plan_path)
		return false

	var plan_file := FileAccess.open(plan_path, FileAccess.READ)
	if plan_file == null:
		push_error("[gd-tools] Unable to read native coverage plan: %s" % plan_path)
		return false
	var parsed: Variant = JSON.parse_string(plan_file.get_as_text())
	# Accept any schema version >= 1: the plan gained fields over time
	# (excluded_lines in v2) but the instrumentation contract is stable.
	if typeof(parsed) != TYPE_DICTIONARY or int(parsed.get("version", -1)) < 1:
		push_error("[gd-tools] Unsupported native coverage plan format")
		return false

	# Loud-failure handshake: refuse to activate on branch types this
	# collector does not implement. Instrumenting them would silently
	# mis-measure (unknown span entries wrap as ternary arms, unknown
	# spanless entries fire as line trackers), so the whole run must
	# fail instead of reporting numbers that look trustworthy but are
	# not.
	for file_data in parsed.get("files", []):
		for line_entry in file_data.get("lines", []):
			var branch_type: Variant = line_entry.get("branch_type")
			if branch_type == null:
				continue
			var type_name := str(branch_type)
			if type_name.is_empty() or type_name in KNOWN_BRANCH_TYPES:
				continue
			push_error(
				(
					"[gd-tools] Coverage plan uses unsupported branch type "
					+ "'%s' (point id %s in %s). The installed collector is "
					+ "older than the plan that produced it; update the "
					+ "gd-tools addons so instrumentation matches the plan."
				)
				% [
					type_name,
					str(line_entry.get("id", "?")),
					str(file_data.get("path", "?")),
				]
			)
			return false

	# R2: a target that cannot be instrumented is reported and skipped, not
	# fatal. This loop used to return on the first failure, which discarded
	# every file already instrumented and left _active false so nothing was
	# written at all -- one broken script cost the project its whole coverage.
	for file_data in parsed.get("files", []):
		_instrument_file(file_data)

	_active = true
	return true


static func hit(file_id: int, line_id: int) -> void:
	## Record one instrumented hit when coverage is active.
	if not _active:
		return
	if not _hits.has(file_id):
		_hits[file_id] = {}
	if not _hits[file_id].has(line_id):
		_hits[file_id][line_id] = 0
	_hits[file_id][line_id] += 1


static func hit_ret(file_id: int, line_id: int, value: Variant) -> Variant:
	## Record one instrumented hit and pass the tracked value through.
	##
	## Injected around ternary operands and boolean-operator sites/right
	## operands so each arm is measured exactly when it evaluates, without
	## re-evaluating the condition.
	hit(file_id, line_id)
	return value


static func hit_bool(file_id: int, true_id: int, false_id: int, value: Variant) -> Variant:
	## Record exactly one boolean-arm hit and pass the value through.
	##
	## Injected around assert conditions: the condition's truth decides
	## which of the two arms is recorded, and the value continues into
	## the assert itself. One wrapper call therefore records exactly one
	## of assert_true / assert_false per evaluation.
	hit(file_id, true_id if value else false_id)
	return value


static func write() -> bool:
	## Write collected hits using the existing coverage JSON schema.
	if not _active or _output_path.is_empty():
		return false

	var files: Array = []
	_derive_short_hits()
	for file_id in _hits:
		var file_hits: Dictionary = {}
		for line_id in _hits[file_id]:
			file_hits[str(line_id)] = _hits[file_id][line_id]
		files.append({"file_id": int(file_id), "hits": file_hits})

	var data := {
		"version": 1,
		"generated_at": Time.get_datetime_string_from_system(true, false) + "Z",
		"files": files,
	}
	if not _omitted.is_empty():
		data["omitted"] = _omitted
	var directory := _output_path.get_base_dir()
	if not directory.is_empty() and not DirAccess.dir_exists_absolute(directory):
		if DirAccess.make_dir_recursive_absolute(directory) != OK:
			return false

	var temporary_path := _output_path + ".tmp"
	var file := FileAccess.open(temporary_path, FileAccess.WRITE)
	if file == null:
		return false
	file.store_string(JSON.stringify(data, "  ") + "\n")
	file.close()
	return DirAccess.rename_absolute(temporary_path, _output_path) == OK


static func _derive_short_hits() -> void:
	## Fold derived short-circuit arm hits into the recorded hit counts.
	##
	## ``short = site - right`` clamped at zero: a negative result would
	## mean the wrap double-fired, which is a defect, not a measurement.
	for file_id in _derived:
		if not _hits.has(file_id):
			continue
		var pairs: Dictionary = _derived[file_id]
		for short_id in pairs:
			var site_hits := int(_hits[file_id].get(pairs[short_id][0], 0))
			var right_hits := int(_hits[file_id].get(pairs[short_id][1], 0))
			var short_hits := maxi(0, site_hits - right_hits)
			if short_hits > 0:
				_hits[file_id][short_id] = short_hits


static func _instrument_file(file_data: Dictionary) -> bool:
	var path := str(file_data.get("path", ""))
	var file_id := int(file_data.get("file_id", -1))
	var lines: Array = file_data.get("lines", [])
	if path.is_empty() or file_id < 0 or lines.is_empty():
		return false

	if not FileAccess.file_exists(path):
		_record_omission(
			file_id,
			path,
			"Skipped uninstrumentable coverage target.",
			"The coverage plan references a file that no longer exists: " + path,
			"The plan is stale. Re-run with --no-cache to regenerate it."
		)
		return false

	var script := load(path) as GDScript
	if script == null:
		_record_omission(
			file_id,
			path,
			"Skipped uninstrumentable coverage target.",
			"The file exists but does not load as GDScript: " + path,
			"Fix the script, or exclude it from the plan."
		)
		return false

	var original_source := script.source_code
	script.source_code = _inject_trackers(
			original_source,
			file_id,
			lines
	)
	var reload_error: int = script.reload(true)
	if reload_error != OK:
		script.source_code = original_source
		script.reload(true)
		_record_omission(
			file_id,
			path,
			"Skipped uninstrumentable coverage target.",
			"Trackers could not be injected, so the script did not reload: " + path,
			"Fix the script's own syntax, or exclude it from the plan."
		)
		return false

	# R3: seed an empty entry so files[] is the instrumented set rather than
	# the hit set. Without it an instrumented-but-unexecuted file is absent
	# from the output and cannot be told apart from one that failed to
	# instrument at all. Phase 1 verified an empty hits object scores
	# identically to an absent entry in every renderer, so this reports no
	# change to any percentage.
	if not _hits.has(file_id):
		_hits[file_id] = {}
	_derive_short_arms(file_id, lines)
	return true


static func _derive_short_arms(file_id: int, lines: Array) -> void:
	## Pair each ``<op>_short`` point with its operator's site and right
	## point ids so :meth:`write` can derive short-circuit hits.
	##
	## Short-circuit arms have no span of their own: the collector records
	## the site whenever the whole expression evaluates and the right arm
	## whenever the right operand evaluates, so ``short = site - right``
	## counts the evaluations the operator skipped. The plan emits each
	## right operand immediately followed by its short arm, so pairing by
	## most recent same-operator right is exact, including for chains.
	var site_by_operator: Dictionary = {}
	var last_right: Dictionary = {}
	var pairs: Dictionary = {}
	for entry in lines:
		var branch_type := str(entry.get("branch_type", ""))
		if branch_type.ends_with("_site"):
			site_by_operator[branch_type.trim_suffix("_site")] = int(entry["id"])
		elif branch_type.ends_with("_right"):
			last_right[branch_type.trim_suffix("_right")] = int(entry["id"])
		elif branch_type.ends_with("_short"):
			var operator := branch_type.trim_suffix("_short")
			if site_by_operator.has(operator) and last_right.has(operator):
				pairs[int(entry["id"])] = [
					site_by_operator[operator],
					last_right[operator],
				]
	if not pairs.is_empty():
		_derived[file_id] = pairs


static func get_omitted() -> Array:
	## Targets that could not be instrumented, as {file_id, path, reason, fix}.
	return _omitted


static func _record_omission(
		file_id: int, path: String, what: String, cause: String, fix: String
) -> void:
	# R1: report an uninstrumentable target as a warning, never an error.
	# push_error escalates Godot to a non-zero exit, and test_runner.py turns
	# any returncode above 1 into a hard failure -- so one unrelated broken
	# script failed every test in the project. The plan-level checks in
	# activate() stay push_error: a missing, unreadable, or wrong-version plan
	# is not a per-target problem and genuinely is fatal.
	# R5: the structured entry rides the additive `omitted` key in the
	# coverage JSON and the runner's diagnostics, so the reason the collector
	# derived outlives the process that derived it.
	_omitted.append({"file_id": file_id, "path": path, "reason": cause, "fix": fix})
	push_warning(
		"[gd-tools] [Warning] " + what + "\n\n"
		+ "  Cause: " + cause + "\n"
		+ "  Fix:   " + fix
	)


static func _inject_trackers(
		source: String,
		file_id: int,
		lines: Array
) -> String:
	var wrapped := _wrap_expression_operands(source, file_id, lines)
	var source_lines: PackedStringArray = wrapped.split("\n")
	var entries: Array = lines.duplicate(true)
	entries.sort_custom(func(a, b): return int(a["line"]) > int(b["line"]))
	for entry in entries:
		# Ternary and boolean-operator arms are instrumented by wrapping
		# their operand text (see _wrap_expression_operands); a
		# line-inserted hit() on the shared anchor line fires both arms
		# in lockstep and can never report an uncovered arm.
		if entry.get("operand_span") != null:
			continue
		# Short-circuit arms are derived at write() as site - right; a
		# line-inserted hit() would fire whenever the statement runs
		# rather than when the operator skipped its right operand.
		if str(entry.get("branch_type", "")).ends_with("_short"):
			continue
		var target_index := int(entry["line"]) - 1
		if target_index < 0 or target_index >= source_lines.size():
			continue
		var branch_type = str(entry.get("branch_type", ""))
		var insert_index := target_index
		if branch_type in ["match_case", "if_false", "elif_true"]:
			insert_index = target_index + 1
		var indent := _extract_indent(source_lines[insert_index])
		if indent.is_empty():
			indent = _extract_indent(source_lines[target_index])
		var tracker := "%sGdToolsNativeCoverage.hit(%d, %d)" % [
			indent,
			file_id,
			int(entry["id"]),
		]
		source_lines.insert(insert_index, tracker)
	return "\n".join(source_lines)


static func _offset_of(source: String, line: int, col: int) -> int:
	## Absolute character offset of a 1-based line/column position, or -1.
	var source_lines := source.split("\n")
	if line < 1 or line > source_lines.size() or col < 1:
		return -1
	var offset := 0
	for i in range(line - 1):
		offset += source_lines[i].length() + 1
	var target := offset + (col - 1)
	if target > source.length():
		return -1
	return target


static func _wrap_expression_operands(
		source: String,
		file_id: int,
		lines: Array
) -> String:
	## Replace each tracked operand with a value-preserving tracker call.
	##
	## The plan records the source span of every ternary arm operand and
	## boolean-operator site/right operand. Wrapping the operand records
	## the arm's hit exactly when that operand evaluates, keeping values,
	## evaluation order, and single evaluation intact. Line numbers are
	## unchanged: a wrapper never adds or removes a newline, so the
	## line-based insertion that follows stays valid.
	##
	## Assert conditions carry two arm ids (assert_true/assert_false)
	## over one shared span: the pair becomes a single value-aware
	## hit_bool wrap that records exactly one arm per evaluation.
	var spans: Array = []
	var assert_pairs: Dictionary = {}
	for entry in lines:
		var branch_type := str(entry.get("branch_type", ""))
		var span: Variant = entry.get("operand_span")
		if span == null:
			continue
		if branch_type == "assert_true" or branch_type == "assert_false":
			var key := str(span)
			if not assert_pairs.has(key):
				assert_pairs[key] = {
					"span": span,
					"assert_true": -1,
					"assert_false": -1,
				}
			assert_pairs[key][branch_type] = int(entry["id"])
			continue
		var start := _offset_of(source, int(span[0]), int(span[1]))
		var end := _offset_of(source, int(span[2]), int(span[3]))
		if start < 0 or end < 0 or start >= end or end > source.length():
			# Fail open: an unusable span leaves the arm uninstrumented
			# rather than corrupting the source.
			continue
		spans.append({"start": start, "end": end, "kind": "ret", "id": int(entry["id"])})
	for key in assert_pairs:
		var pair: Dictionary = assert_pairs[key]
		if int(pair["assert_true"]) < 0 or int(pair["assert_false"]) < 0:
			# Fail open: an incomplete pair leaves the assert uninstrumented.
			continue
		var span: Array = pair["span"]
		var start := _offset_of(source, int(span[0]), int(span[1]))
		var end := _offset_of(source, int(span[2]), int(span[3]))
		if start < 0 or end < 0 or start >= end or end > source.length():
			continue
		spans.append({
			"start": start,
			"end": end,
			"kind": "bool",
			"true_id": int(pair["assert_true"]),
			"false_id": int(pair["assert_false"]),
		})
	if spans.is_empty():
		return source
	spans.sort_custom(func(a, b):
		if int(a["start"]) != int(b["start"]):
			return int(a["start"]) < int(b["start"])
		return int(a["end"]) > int(b["end"])
	)
	return _wrap_spans(source, file_id, spans, 0, 0, source.length())


static func _wrap_spans(
		source: String,
		file_id: int,
		spans: Array,
		index: int,
		from: int,
		to: int
) -> String:
	## Emit source[from:to] with spans[index..] wrapped in place.
	##
	## Spans are sorted ascending by start (outer span before inner on a
	## tie), so a span's children are the following entries fully contained
	## in it; they are wrapped recursively inside the operand text.
	var result := ""
	var cursor := from
	var i := index
	while i < spans.size():
		var span: Dictionary = spans[i]
		var start := int(span["start"])
		var end := int(span["end"])
		if start >= to or end > to:
			break
		if start < cursor:
			i += 1
			continue
		var children: Array = []
		var j := i + 1
		while j < spans.size() and int(spans[j]["end"]) <= end:
			children.append(spans[j])
			j += 1
		result += source.substr(cursor, start - cursor)
		var operand := _wrap_spans(source, file_id, children, 0, start, end)
		if str(span.get("kind", "ret")) == "bool":
			result += "GdToolsNativeCoverage.hit_bool(%d, %d, %d, %s)" % [
				file_id,
				int(span["true_id"]),
				int(span["false_id"]),
				operand,
			]
		else:
			result += "GdToolsNativeCoverage.hit_ret(%d, %d, %s)" % [
				file_id,
				int(span["id"]),
				operand,
			]
		cursor = end
		i = j
	result += source.substr(cursor, to - cursor)
	return result


static func _extract_indent(line: String) -> String:
	var indent := ""
	for character in line:
		if character == " " or character == "\t":
			indent += character
		else:
			break
	return indent
