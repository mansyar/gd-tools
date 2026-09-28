extends GutTest
class_name BridgeSkipSuite

func test_explicit_skip() -> void:
	skip_test("not relevant on the bridge")
	assert_true(false, "a skip discards later assertions")

func test_version_skip_lt() -> void:
	skip_if_godot_version_lt("4.5")
	assert_true(true)

func test_version_skip_ne() -> void:
	skip_if_godot_version_ne(Engine.get_version_info()["string"])
	assert_true(true)
