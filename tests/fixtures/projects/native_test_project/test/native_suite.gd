extends GdToolsTest
class_name NativeFixtureSuite

const TAGS = ["native", "smoke"]

var before_each_calls := 0

func before_each() -> void:
	before_each_calls += 1

func test_pass() -> void:
	assert_true(true)

func test_async() -> void:
	await get_tree().process_frame
	assert_true(true)
