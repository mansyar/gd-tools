class_name NativeSnapshotUpdateSuite
extends GdToolsTest

const STORE := preload("res://addons/gd-tools-test/gd_tools_snapshot_store.gd")
const BASE_DIR := "res://.gd-tools/snapshots"
const SUITE := "NativeSnapshotUpdateSuite"


func test_update_mode_rewrites_mismatch() -> void:
	var snapshot_name := "rewritten"
	var path := STORE.snapshot_path(BASE_DIR, SUITE, _gd_tools_snapshot_test_name, snapshot_name)
	var write_result := STORE.write(BASE_DIR, SUITE, _gd_tools_snapshot_test_name, snapshot_name, "\"stale\"")
	assert_true(bool(write_result.get("ok", false)))
	assert_snapshot("fresh", snapshot_name)
	var read_result := STORE.read(BASE_DIR, SUITE, _gd_tools_snapshot_test_name, snapshot_name)
	assert_true(bool(read_result.get("ok", false)))
	assert_eq(str(read_result.get("value", "")), "\"fresh\"")
