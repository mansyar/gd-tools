extends GdToolsTest
class_name NativeReviewStateSuite

var suite_value := 0

func before_all() -> void:
    suite_value = 42

func test_uses_suite_state() -> void:
    assert_eq(suite_value, 42)
