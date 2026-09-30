@tool
extends Panel

## gd-tools dock panel.
##
## Provides Run Tests / Run Coverage buttons, an async non-blocking
## run state, and a results area (summary + failures) parsed from the
## machine-readable artifacts the gd-tools CLI writes under
## ``.gd-tools/``.

const CLI_NAME := "gd-tools"
const MISSING_CLI_MESSAGE := (
	"gd-tools CLI not found.\n"
	+ "Install it with:\n"
	+ "    pip install gd-tools-cli\n"
	+ "and make sure the script is on your PATH,\n"
	+ "then restart the Godot editor."
)
const COVERAGE_DIR := "res://.gd-tools/coverage"
const ARTIFACTS_DIR := "res://.gd-tools/artifacts"

var _run_button: Button = null
var _coverage_button: Button = null
var _status_label: Label = null
var _results_label: RichTextLabel = null
var _process_id: int = -1
var _pending_coverage := false


func _ready() -> void:
	custom_minimum_size = Vector2(320.0, 220.0)
	_build_ui()


func _process(_delta: float) -> void:
	if _process_id > 0 and not OS.is_process_running(_process_id):
		var exit_code := OS.get_process_exit_code(_process_id)
		_process_id = -1
		_on_run_finished(exit_code)


## Spawn a gd-tools CLI invocation as a detached, non-blocking process.
##
## Uses the argument-list form (no shell) so arguments are passed
## verbatim. Returns ``true`` when the process was spawned.
func _start_cli(arguments: Array) -> bool:
	_status_label.text = "Running gd-tools %s ..." % " ".join(arguments)
	_results_label.text = ""
	_set_buttons_disabled(true)
	var project_path := ProjectSettings.globalize_path("res://")
	var full_arguments := ["--project", project_path]
	full_arguments.append_array(arguments)
	var pid := OS.create_process(CLI_NAME, full_arguments)
	if pid <= 0:
		_set_buttons_disabled(false)
		_status_label.text = "gd-tools not found"
		_results_label.text = MISSING_CLI_MESSAGE
		return false
	_process_id = pid
	return true


func _on_run_finished(exit_code: int) -> void:
	_set_buttons_disabled(false)
	if exit_code == 127 or exit_code < 0:
		_status_label.text = "gd-tools not found"
		_results_label.text = MISSING_CLI_MESSAGE
		return
	var coverage_results: Dictionary = {}
	if _pending_coverage:
		coverage_results = _read_coverage_summary()
	_pending_coverage = false
	var summary := _read_test_summary()
	_render_results(summary, coverage_results, exit_code)


func _read_test_summary() -> Dictionary:
	var index_path := _latest_artifact_index()
	if index_path.is_empty():
		return {}
	var file := FileAccess.open(index_path, FileAccess.READ)
	if file == null:
		return {}
	var parsed: Variant = JSON.parse_string(file.get_as_text())
	if typeof(parsed) != TYPE_DICTIONARY:
		return {}
	var totals := {"passed": 0, "failed": 0, "skipped": 0}
	var total_duration := 0.0
	var failures: Array = []
	for suite_entry: Dictionary in parsed.get("suites", []):
		var result_path: String = suite_entry.get("result", "")
		if result_path.is_empty():
			continue
		var suite_result := _load_json(result_path)
		if suite_result.is_empty():
			continue
		for test: Dictionary in suite_result.get("tests", []):
			var status: String = test.get("status", "")
			match status:
				"passed":
					totals["passed"] += 1
				"failed", "error", "timeout", "crashed":
					totals["failed"] += 1
					failures.append(
						{
							"name": "%s.%s" % [
								test.get("suite", "?"),
								test.get("name", "?"),
							],
							"message": test.get("message", ""),
						}
					)
				"skipped", "pending":
					totals["skipped"] += 1
			total_duration += float(test.get("duration_seconds", 0.0))
	return {
		"passed": totals["passed"],
		"failed": totals["failed"],
		"skipped": totals["skipped"],
		"duration": total_duration,
		"failures": failures,
		"artifact_path": index_path.get_base_dir(),
	}


func _read_coverage_summary() -> Dictionary:
	var plan := _load_json(COVERAGE_DIR + "/plan.json")
	var data := _load_json(COVERAGE_DIR + "/coverage.json")
	if plan.is_empty() or data.is_empty():
		return {}
	var hits_by_id := {}
	for entry: Dictionary in data.get("files", []):
		hits_by_id[entry.get("file_id")] = entry.get("hits", {})
	var covered_lines := 0
	var total_lines := 0
	var covered_branches := 0
	var total_branches := 0
	for file_plan: Dictionary in plan.get("files", []):
		var hits: Dictionary = hits_by_id.get(
			file_plan.get("file_id"), {}
		)
		for line_plan: Dictionary in file_plan.get("lines", []):
			total_lines += 1
			var hit := int(hits.get(line_plan.get("id", ""), 0)) > 0
			if hit:
				covered_lines += 1
			if str(line_plan.get("branch_type", "")) != "":
				total_branches += 1
				if hit:
					covered_branches += 1
	if total_lines == 0:
		return {}
	return {
		"line_rate": float(covered_lines) / float(total_lines),
		"branch_rate": (
			float(covered_branches) / float(total_branches)
			if total_branches > 0
			else -1.0
		),
	}


func _render_results(
	summary: Dictionary,
	coverage_results: Dictionary,
	exit_code: int,
) -> void:
	if summary.is_empty():
		_status_label.text = "Run finished (exit %d)" % exit_code
		_results_label.text = (
			"No test artifacts found. Did the run complete?\n"
			+ "Artifacts are written to .gd-tools/artifacts/."
		)
		return
	var failed: int = summary["failed"]
	_status_label.text = (
		"Finished: %d passed, %d failed, %d skipped in %.1fs"
		% [
			summary["passed"],
			failed,
			summary["skipped"],
			summary["duration"],
		]
	)
	var lines: Array[String] = []
	if failed == 0:
		lines.append("[color=#4caf50]All tests passed.[/color]")
	else:
		lines.append("[color=#f44336]%d failed test(s):[/color]" % failed)
		for failure: Dictionary in summary["failures"]:
			lines.append(
				"[color=#f44336]FAIL[/color] %s" % failure["name"]
			)
			var message: String = failure["message"]
			if not message.is_empty():
				lines.append("  " + message.replace("\n", "\n  "))
	lines.append("")
	if not coverage_results.is_empty():
		var branch_text := "n/a"
		var branch_rate: float = coverage_results["branch_rate"]
		if branch_rate >= 0.0:
			branch_text = "%.1f%%" % (branch_rate * 100.0)
		lines.append(
			"Coverage: lines %.1f%%, branches %s"
			% [coverage_results["line_rate"] * 100.0, branch_text]
		)
	lines.append("Artifacts: %s" % summary["artifact_path"])
	_results_label.text = "\n".join(lines)


func _latest_artifact_index() -> String:
	var artifacts_dir := DirAccess.open(ARTIFACTS_DIR)
	if artifacts_dir == null:
		return ""
	var best_path := ""
	var best_time := -1
	artifacts_dir.list_dir_begin()
	var run_id := artifacts_dir.get_next()
	while not run_id.is_empty():
		if artifacts_dir.current_is_dir():
			var candidate := "%s/%s/artifacts.json" % [
				ARTIFACTS_DIR,
				run_id,
			]
			if FileAccess.file_exists(candidate):
				var modified := FileAccess.get_modified_time(candidate)
				if modified > best_time:
					best_time = modified
					best_path = candidate
		run_id = artifacts_dir.get_next()
	artifacts_dir.list_dir_end()
	return best_path


func _load_json(path: String) -> Dictionary:
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		return {}
	var parsed: Variant = JSON.parse_string(file.get_as_text())
	if typeof(parsed) != TYPE_DICTIONARY:
		return {}
	return parsed


func _set_buttons_disabled(disabled: bool) -> void:
	_run_button.disabled = disabled
	_coverage_button.disabled = disabled


func _on_run_tests_pressed() -> void:
	if _process_id > 0:
		return
	_pending_coverage = false
	_start_cli(["test"])


func _on_run_coverage_pressed() -> void:
	if _process_id > 0:
		return
	_pending_coverage = true
	_start_cli(["test", "--coverage"])


func _build_ui() -> void:
	var layout := VBoxContainer.new()
	layout.name = "Layout"
	add_child(layout)

	var buttons := HBoxContainer.new()
	buttons.name = "Buttons"
	layout.add_child(buttons)

	_run_button = Button.new()
	_run_button.name = "RunTestsButton"
	_run_button.text = "Run Tests"
	_run_button.pressed.connect(_on_run_tests_pressed)
	buttons.add_child(_run_button)

	_coverage_button = Button.new()
	_coverage_button.name = "RunCoverageButton"
	_coverage_button.text = "Run Coverage"
	_coverage_button.pressed.connect(_on_run_coverage_pressed)
	buttons.add_child(_coverage_button)

	_status_label = Label.new()
	_status_label.name = "StatusLabel"
	_status_label.text = "Idle"
	_status_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	layout.add_child(_status_label)

	_results_label = RichTextLabel.new()
	_results_label.name = "ResultsLabel"
	_results_label.bbcode_enabled = true
	_results_label.size_flags_vertical = Control.SIZE_EXPAND_FILL
	layout.add_child(_results_label)
