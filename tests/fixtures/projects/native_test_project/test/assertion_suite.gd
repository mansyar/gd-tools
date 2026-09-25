extends GdToolsTest
class_name NativeAssertionSuite

func test_structured_failure() -> void:
	assert_eq(1, 2, "values differ")
