extends GdToolsTest

class_name NativeSnapshotAssertSuite

const STORE := preload("res://addons/gd-tools-test/gd_tools_snapshot_store.gd")

const BASE_DIR := "res://.gd-tools/snapshots"
const SUITE := "NativeSnapshotAssertSuite"


func test_first_run_writes_and_passes() -> void:
	assert_snapshot({"a": 1})
	var path := STORE.snapshot_path(
		BASE_DIR,
		SUITE,
		"test_first_run_writes_and_passes",
		"test_first_run_writes_and_passes_1"
	)
	assert_true(FileAccess.file_exists(path))


func test_multiple_auto_named_snapshots() -> void:
	assert_snapshot("first")
	assert_snapshot([1, 2])
	assert_true(
		FileAccess.file_exists(
			STORE.snapshot_path(
				BASE_DIR,
				SUITE,
				"test_multiple_auto_named_snapshots",
				"test_multiple_auto_named_snapshots_1"
			)
		)
	)
	assert_true(
		FileAccess.file_exists(
			STORE.snapshot_path(
				BASE_DIR,
				SUITE,
				"test_multiple_auto_named_snapshots",
				"test_multiple_auto_named_snapshots_2"
			)
		)
	)


func test_explicit_snapshot_name() -> void:
	assert_snapshot(42, "custom")
	assert_true(
		FileAccess.file_exists(
			STORE.snapshot_path(BASE_DIR, SUITE, "test_explicit_snapshot_name", "custom")
		)
	)


func test_mismatch_fails_and_reports_diff() -> void:
	STORE.write(
		BASE_DIR,
		SUITE,
		"test_mismatch_fails_and_reports_diff",
		"test_mismatch_fails_and_reports_diff_1",
		'"stored"'
	)
	assert_snapshot("actual")
	assert_eq(get_failures().size(), 1)
	var failure := get_failures()[0]
	assert_eq(failure.get("assertion"), "assert_snapshot")
	var message := str(failure.get("message", ""))
	assert_true(message.contains("Snapshot mismatch"), message)
	assert_true(message.contains('- "stored"'), message)
	assert_true(message.contains('+ "actual"'), message)
	assert_eq(failure.get("expected"), '"stored"')
	assert_eq(failure.get("actual"), '"actual"')
	clear_failures()


func test_io_error_fails_closed() -> void:
	OS.set_environment("GD_TOOLS_SNAPSHOT_BASE", "res://project.godot")
	assert_snapshot(1)
	OS.set_environment("GD_TOOLS_SNAPSHOT_BASE", "")
	assert_eq(get_failures().size(), 1)
	var failure := get_failures()[0]
	assert_eq(failure.get("assertion"), "assert_snapshot")
	assert_true(str(failure.get("message", "")).length() > 0)
	clear_failures()


func test_parameterized_case_snapshots() -> void:
	var value = use_parameters(["alpha", "beta"])
	assert_snapshot(value)
	var case_name := _gd_tools_snapshot_test_name
	assert_true(
		FileAccess.file_exists(
			STORE.snapshot_path(BASE_DIR, SUITE, case_name, case_name + "_1")
		),
		case_name
	)
