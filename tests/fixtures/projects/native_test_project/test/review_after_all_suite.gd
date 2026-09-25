extends GdToolsTest
class_name NativeAfterAllFailureSuite

func after_all() -> void:
    assert_true(false, "after_all failed intentionally")

func test_pass() -> void:
    assert_true(true)
