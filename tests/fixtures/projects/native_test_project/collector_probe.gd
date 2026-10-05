extends SceneTree
## Drives GdToolsNativeCoverage.hit_bool directly to verify that one
## wrapper call records exactly one boolean arm.
##
## A firing assert halts headless debug runs, so the false arm cannot be
## observed through a real assert; this probe exercises the same code
## path the assert instrumentation emits, for both truth values. The
## collector is loaded by path so the probe does not depend on the
## editor's global class cache, and it is activated through the public
## activate() entry point with a minimal plan.


const PROBE_PLAN := """{
  "version": 7,
  "generated_by": "collector-probe",
  "files": [
    {
      "file_id": 1,
      "path": "res://collector_probe_target.gd",
      "source_hash": "probe",
      "lines": [
        {"line": 1, "id": 10, "type": "branch", "branch_type": "assert_true", "operand_span": [1, 1, 1, 2]},
        {"line": 1, "id": 11, "type": "branch", "branch_type": "assert_false", "operand_span": [1, 1, 1, 2]}
      ],
      "excluded_lines": []
    }
  ]
}"""


func _init() -> void:
	var plan := FileAccess.open("res://collector_probe_plan.json", FileAccess.WRITE)
	plan.store_string(PROBE_PLAN)
	plan.close()
	var collector: GDScript = load(
		"res://addons/gd-tools-test/gd_tools_native_coverage.gd"
	)
	var activated: bool = collector.activate(
		"res://collector_probe_plan.json", "res://collector_probe_out.json"
	)
	var kept: bool = collector.hit_bool(1, 10, 11, true)
	var dropped: bool = collector.hit_bool(1, 10, 11, false)
	var written: bool = collector.write()
	var f := FileAccess.open("res://collector_probe_values.txt", FileAccess.WRITE)
	f.store_line(
		"activated=%s kept=%s dropped=%s written=%s"
		% [activated, kept, dropped, written]
	)
	f.close()
	quit(0)
