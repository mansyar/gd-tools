extends GdToolsTest
class_name NativeBeforeAllFailureSuite

func before_all() -> void:
    assert_true(false, "before_all failed intentionally")

func test_never_reports_green() -> void:
    assert_true(true)
