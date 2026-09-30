extends Node

## Coverage tracker autoload for gd-tools.
## Instruments GDScript source files with coverage tracking calls
## in _ready() using reload(true) (keep_state) so existing autoload
## instances pick up the instrumented code. Records line hit counts
## during GUT test execution. Tracker activation happens via
## pre_run_hook.gd's set_active(true) call after all autoloads have
## initialized.
##
## Playtest mode: when GD_TOOLS_COVERAGE_PLAYTEST=1 is set, the tracker
## activates itself (no test runtime or hook involved) and writes the
## coverage output periodically (GD_TOOLS_COVERAGE_PLAYTEST_INTERVAL,
## default 5s) and once more when the game exits, so a plain game run
## collects coverage while a human plays. The JSON output matches the
## post-run hook contract exactly.

const TRACKER_NAME = "_GDTCoverage"

const PLAYTEST_ENV = "GD_TOOLS_COVERAGE_PLAYTEST"

const PLAYTEST_INTERVAL_ENV = "GD_TOOLS_COVERAGE_PLAYTEST_INTERVAL"

const DEFAULT_PLAYTEST_INTERVAL: float = 5.0

var _hits: Dictionary = {}

var _active: bool = false

var _plan: Dictionary = {}

var _omitted: Array = []

var _playtest_active: bool = false

var _playtest_output_path: String = ""

var _playtest_timer: Timer = null


func _ready() -> void:
	# Instrument files when GD_TOOLS_COVERAGE_PLAN is set.
	# Uses reload(true) (keep_state) so scripts with existing instances
	# (e.g. other autoloads) are reloaded without discarding them.
	var plan_path: String = OS.get_environment("GD_TOOLS_COVERAGE_PLAN")
	if plan_path.is_empty():
		return

	_plan = _load_plan(plan_path)
	if _plan.is_empty():
		return

	if not _validate_plan(_plan):
		_plan = {}
		return

	var files: Array = _plan.get("files", [])
	if files.is_empty():
		print("[gd-tools] [Warning] Coverage plan has no files to instrument.")
		return

	_instrument_files()

	if OS.get_environment(PLAYTEST_ENV) == "1":
		_start_playtest_mode()
		return

	# _active remains false — the pre-run hook will activate the tracker
	# via set_active(true) after all autoloads have initialized.


func hit(file_id: int, line_id: int) -> void:
	# Single bool check for minimal overhead when inactive.
	if not _active:
		return
	if not _hits.has(file_id):
		_hits[file_id] = {}
	if not _hits[file_id].has(line_id):
		_hits[file_id][line_id] = 0
	_hits[file_id][line_id] += 1


func get_hits() -> Dictionary:
	return _hits


func get_omitted() -> Array:
	## Targets that could not be instrumented, as {file_id, path, reason, fix}.
	return _omitted


func reset() -> void:
	_hits.clear()
	_omitted.clear()


func set_active(active: bool) -> void:
	_active = active


func is_active() -> bool:
	return _active


# === Playtest mode ===


func _notification(what: int) -> void:
	# The windowed game closing is the primary exit path during play.
	if what == NOTIFICATION_WM_CLOSE_REQUEST:
		_stop_playtest(true)


func _exit_tree() -> void:
	# Covers SceneTree.quit() and editor/engine shutdown, where the
	# window-close notification is not delivered.
	_stop_playtest(true)


func _start_playtest_mode() -> void:
	# Self-activate: there is no test runtime to call set_active(true),
	# and the pre-run hook is never involved in a plain game run.
	_playtest_active = true
	set_active(true)
	_playtest_output_path = OS.get_environment("GD_TOOLS_COVERAGE_OUTPUT")
	if _playtest_output_path.is_empty():
		_log_warning(
			"Playtest coverage cannot write output.",
			"GD_TOOLS_COVERAGE_OUTPUT environment variable is not set.",
			"Set GD_TOOLS_COVERAGE_OUTPUT to a writable file path."
		)
		return

	var timer := Timer.new()
	timer.wait_time = _resolve_playtest_interval()
	timer.timeout.connect(_write_playtest_snapshot)
	add_child(timer)
	timer.start()
	_playtest_timer = timer


func _resolve_playtest_interval() -> float:
	var raw: String = OS.get_environment(PLAYTEST_INTERVAL_ENV)
	if raw.is_empty():
		return DEFAULT_PLAYTEST_INTERVAL
	var value: float = raw.to_float()
	if value <= 0.0:
		_log_warning(
			"Invalid playtest flush interval.",
			"GD_TOOLS_COVERAGE_PLAYTEST_INTERVAL is not a positive number: " + raw,
			"Set a positive number of seconds, or unset the variable to use "
			+ "the %.1fs default." % DEFAULT_PLAYTEST_INTERVAL
		)
		return DEFAULT_PLAYTEST_INTERVAL
	return value


func _stop_playtest(flush: bool) -> void:
	# One-shot: both the window-close notification and tree exit funnel
	# here, so the final write happens exactly once.
	if not _playtest_active:
		return
	_playtest_active = false
	if _playtest_timer != null:
		_playtest_timer.stop()
		_playtest_timer.queue_free()
		_playtest_timer = null
	if flush:
		_write_playtest_snapshot(true)


func _write_playtest_snapshot(final: bool = false) -> void:
	var data: Dictionary = _build_coverage_json(_hits, _omitted)
	if not _write_json(_playtest_output_path, data):
		return
	if final:
		_log_summary(_hits, _playtest_output_path)


func _build_coverage_json(hits: Dictionary, omitted: Array = []) -> Dictionary:
	# Matches the post-run hook output contract exactly so every
	# reporter consumes playtest sessions unchanged.
	var files: Array = []
	for file_id in hits:
		var file_hits: Dictionary = hits[file_id]
		var hits_dict: Dictionary = {}
		for line_id in file_hits:
			hits_dict[str(line_id)] = file_hits[line_id]
		files.append({"file_id": int(file_id), "hits": hits_dict})
	var data := {
		"version": 1,
		"generated_at": Time.get_datetime_string_from_system(true, false) + "Z",
		"files": files
	}
	if not omitted.is_empty():
		data["omitted"] = omitted
	return data


func _write_json(path: String, data: Dictionary) -> bool:
	var dir_path: String = path.get_base_dir()
	if not dir_path.is_empty() and not DirAccess.dir_exists_absolute(dir_path):
		var err: int = DirAccess.make_dir_recursive_absolute(dir_path)
		if err != OK:
			_log_error(
				"Cannot create output directory.",
				"Failed to create directory: " + dir_path,
				"Check permissions and path validity."
			)
			return false

	var file = FileAccess.open(path, FileAccess.WRITE)
	if file == null:
		_log_error(
			"Cannot write coverage output.",
			"Cannot open file for writing: " + path,
			"Check file permissions and path validity."
		)
		return false

	file.store_string(JSON.stringify(data, "  "))
	file = null
	return true


func _log_summary(hits: Dictionary, output_path: String) -> String:
	var total_files: int = hits.size()
	var total_lines: int = 0
	for file_id in hits:
		total_lines += hits[file_id].size()
	var summary := (
		"[gd-tools] Coverage summary: %d files, %d lines tracked, output: %s"
		% [total_files, total_lines, output_path]
	)
	print(summary)
	return summary


# === Instrumentation logic (moved from pre_run_hook.gd) ===


func _instrument_files() -> int:
	var files: Array = _plan.get("files", [])
	var count: int = 0
	for file_entry in files:
		if _instrument_file(file_entry):
			count += 1
	return count


func _instrument_file(file_entry: Dictionary) -> bool:
	var path: String = file_entry.get("path", "")
	var file_id: int = int(file_entry.get("file_id", -1))
	var lines: Array = file_entry.get("lines", [])

	if lines.is_empty():
		return false

	# R4: a path that does not exist and a file that will not load are the
	# same control flow but different problems. One means the plan is stale;
	# the other means the script is a real defect. FileAccess.file_exists is
	# what separates them -- load() returns null for both.
	if not FileAccess.file_exists(path):
		_record_omission(
			file_id,
			path,
			"Skipped uninstrumentable script.",
			"The coverage plan references a file that no longer exists: " + path,
			"The plan is stale. Re-run with --no-cache to regenerate it."
		)
		return false

	var script = load(path) as GDScript
	if script == null:
		_record_omission(
			file_id,
			path,
			"Skipped uninstrumentable script.",
			"The file exists but does not load as GDScript: " + path,
			"Fix the script, or exclude it from the plan."
		)
		return false

	var original_source: String = script.source_code
	var instrumented: String = _inject_trackers(original_source, file_id, lines)
	script.source_code = instrumented
	var err: int = script.reload(true)
	if err != OK:
		_record_omission(
			file_id,
			path,
			"Skipped uninstrumentable script.",
			"Trackers could not be injected, so the script did not reload: " + path,
			"Fix the script's own syntax, or exclude it from the plan."
		)
		script.source_code = original_source
		script.reload(true)
		return false

	# R3: seed an empty entry so files[] is the instrumented set rather than
	# the hit set. Without it an instrumented-but-unexecuted file is absent
	# from the output and cannot be told apart from one that failed to
	# instrument at all. Phase 1 verified an empty hits object scores
	# identically to an absent entry in every renderer, so this reports no
	# change to any percentage.
	if not _hits.has(file_id):
		_hits[file_id] = {}
	return true


static func _extract_indent(line: String) -> String:
	var indent: String = ""
	for c in line:
		if c == " " or c == "\t":
			indent += c
		else:
			break
	return indent


static func _detect_body_indent(source_lines: PackedStringArray, pattern_index: int) -> String:
	# Scan lines after the pattern line to find the next non-empty line
	# and use its indentation as the body indent.
	var i: int = pattern_index + 1
	while i < source_lines.size():
		var line: String = source_lines[i]
		if not line.strip_edges().is_empty():
			return _extract_indent(line)
		i += 1
	# Fallback: if no non-empty line found, use the pattern indent plus one tab.
	return _extract_indent(source_lines[pattern_index]) + "\t"


static func _inject_trackers(source: String, file_id: int, lines: Array) -> String:
	var source_lines: PackedStringArray = source.split("\n")
	var sorted_lines: Array = lines.duplicate(true)
	sorted_lines.sort_custom(func(a, b): return int(a["line"]) > int(b["line"]))
	for entry in sorted_lines:
		var target_line_num: int = int(entry["line"])
		var line_id: int = int(entry["id"])
		var target_index: int = target_line_num - 1
		if target_index < 0 or target_index >= source_lines.size():
			continue
		var target_line: String = source_lines[target_index]
		var branch_type = entry.get("branch_type", "")
		if branch_type == null:
			branch_type = ""
		var insert_index: int
		var indent: String
		if branch_type in ["match_case", "if_false", "elif_true"]:
			# Inject AFTER the branch line (inside the body).
			# match_case patterns, else: and elif: lines must have trackers
			# placed inside their body — injecting before these lines would
			# insert a statement between the if/elif/else keywords, breaking
			# the GDScript block structure (orphaned else/elif = syntax error).
			insert_index = target_index + 1
			indent = _detect_body_indent(source_lines, target_index)
		else:
			# Inject BEFORE the tracked line (existing behavior)
			insert_index = target_index
			indent = _extract_indent(target_line)
		var tracker_call: String = "%s%s.hit(%d, %d)" % [indent, TRACKER_NAME, file_id, line_id]
		source_lines.insert(insert_index, tracker_call)
	return "\n".join(source_lines)


func _load_plan(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		_log_error(
			"Failed to load coverage plan.",
			"File not found: " + path,
			"Ensure GD_TOOLS_COVERAGE_PLAN points to a valid plan JSON file."
		)
		return {}

	var f = FileAccess.open(path, FileAccess.READ)
	if f == null:
		_log_error(
			"Failed to load coverage plan.",
			"Cannot open file: " + path,
			"Check file permissions and try again."
		)
		return {}

	var content: String = f.get_as_text()
	f = null

	var parsed = JSON.parse_string(content)
	if not (parsed is Dictionary):
		_log_error(
			"Failed to parse coverage plan JSON.",
			"Invalid JSON in file: " + path,
			"Validate the JSON syntax and try again."
		)
		return {}

	return parsed


func _validate_plan(plan: Dictionary) -> bool:
	if not plan.has("version"):
		_log_error(
			"Invalid coverage plan structure.",
			"Missing 'version' key.",
			"Ensure the plan JSON has a 'version' field."
		)
		return false

	if not plan.has("files") or not (plan["files"] is Array):
		_log_error(
			"Invalid coverage plan structure.",
			"Missing or invalid 'files' key.",
			"Ensure the plan JSON has a 'files' array."
		)
		return false

	for file_entry in plan["files"]:
		if not _validate_file_entry(file_entry):
			return false

	return true


func _validate_file_entry(file_entry: Variant) -> bool:
	if not (file_entry is Dictionary):
		_log_error(
			"Invalid coverage plan structure.",
			"File entry is not an object.",
			"Ensure each file in 'files' is a JSON object."
		)
		return false

	if not file_entry.has("file_id"):
		_log_error(
			"Invalid coverage plan structure.",
			"File entry missing 'file_id'.",
			"Ensure each file has a 'file_id' field."
		)
		return false

	if not file_entry.has("path"):
		_log_error(
			"Invalid coverage plan structure.",
			"File entry missing 'path'.",
			"Ensure each file has a 'path' field."
		)
		return false

	if not file_entry.has("lines") or not (file_entry["lines"] is Array):
		_log_error(
			"Invalid coverage plan structure.",
			"Missing or invalid 'lines' key.",
			"Ensure each file has a 'lines' array."
		)
		return false

	for line_entry in file_entry["lines"]:
		if not (line_entry is Dictionary) or not line_entry.has("line") or not line_entry.has("id"):
			_log_error(
				"Invalid coverage plan structure.",
				"Line entry missing 'line' or 'id' key.",
				"Ensure each line entry has 'line' and 'id' fields."
			)
			return false

	return true


func _log_error(what: String, cause: String, fix: String) -> void:
	push_error(
		"[gd-tools] [Error] " + what + "\n\n" + "  Cause: " + cause + "\n" + "  Fix:   " + fix
	)


func _log_warning(what: String, cause: String, fix: String) -> void:
	# R1: report an uninstrumentable target as a warning, never an error.
	# push_error escalates Godot to a non-zero exit, and test_runner.py turns
	# any returncode above 1 into a hard failure -- so one unrelated broken
	# script failed every test in the project. _log_error is deliberately left
	# intact for the plan-level failures above, which really are fatal.
	push_warning(
		"[gd-tools] [Warning] " + what + "\n\n" + "  Cause: " + cause + "\n" + "  Fix:   " + fix
	)


func _record_omission(
		file_id: int, path: String, what: String, cause: String, fix: String
) -> void:
	# R5: record the omission structurally so the additive `omitted` key in
	# the coverage JSON carries the reason the collector derived, while the
	# console keeps the same warning it has always printed.
	_omitted.append({"file_id": file_id, "path": path, "reason": cause, "fix": fix})
	_log_warning(what, cause, fix)
