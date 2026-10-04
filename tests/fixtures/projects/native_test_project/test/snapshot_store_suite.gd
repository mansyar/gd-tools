extends GdToolsTest

class_name NativeSnapshotStoreSuite

const STORE := preload("res://addons/gd-tools-test/gd_tools_snapshot_store.gd")

const BASE_DIR := "res://.gd-tools/snapshots"


func test_write_creates_versioned_snapshot_file() -> void:
	var result := STORE.write(
		BASE_DIR,
		"snapshot_store_suite",
		"test_write_creates_versioned_snapshot_file",
		"default",
		'"stored value"'
	)
	assert_true(result.get("ok", false))
	var path := STORE.snapshot_path(
		BASE_DIR,
		"snapshot_store_suite",
		"test_write_creates_versioned_snapshot_file",
		"default"
	)
	assert_true(FileAccess.file_exists(path))
	var text := FileAccess.get_file_as_string(path)
	assert_true(text.begins_with("# gd-tools snapshot v1\n"))
	assert_true(text.contains("# suite: snapshot_store_suite\n"))
	assert_true(text.contains("# test: test_write_creates_versioned_snapshot_file\n"))
	assert_true(text.contains("# name: default\n"))
	assert_true(text.ends_with('"stored value"\n'))
	assert_true(not text.contains("\r"))


func test_read_round_trips_stored_value() -> void:
	var write_result := STORE.write(
		BASE_DIR,
		"snapshot_store_suite",
		"test_read_round_trips_stored_value",
		"default",
		"[\n  1,\n  2\n]"
	)
	assert_true(write_result.get("ok", false))
	var read_result := STORE.read(
		BASE_DIR,
		"snapshot_store_suite",
		"test_read_round_trips_stored_value",
		"default"
	)
	assert_true(read_result.get("ok", false))
	assert_eq(read_result.get("value"), "[\n  1,\n  2\n]")


func test_read_missing_snapshot_reports_not_found() -> void:
	var result := STORE.read(
		BASE_DIR,
		"snapshot_store_suite",
		"test_read_missing_snapshot_reports_not_found",
		"default"
	)
	assert_true(not result.get("ok", true))
	assert_eq(result.get("error"), "not_found")


func test_read_malformed_snapshot_reports_error() -> void:
	var path := STORE.snapshot_path(
		BASE_DIR,
		"snapshot_store_suite",
		"test_read_malformed_snapshot_reports_error",
		"default"
	)
	DirAccess.make_dir_recursive_absolute(path.get_base_dir())
	var file := FileAccess.open(path, FileAccess.WRITE)
	assert_true(file != null)
	file.store_string("not a snapshot\n")
	file.close()
	var result := STORE.read(
		BASE_DIR,
		"snapshot_store_suite",
		"test_read_malformed_snapshot_reports_error",
		"default"
	)
	assert_true(not result.get("ok", true))
	assert_eq(result.get("error"), "malformed")
	assert_true(str(result.get("message", "")).length() > 0)
