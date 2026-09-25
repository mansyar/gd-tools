extends GdToolsTest
class_name NativeReviewTimeoutCleanupSuite

func _log(event: String) -> void:
    var log_file := FileAccess.open("res://review-timeout.log", FileAccess.READ_WRITE)
    if log_file == null:
        log_file = FileAccess.open("res://review-timeout.log", FileAccess.WRITE)
    log_file.seek_end()
    log_file.store_line(event)
    log_file.close()

func before_each() -> void:
    await wait_seconds(1.0)

func after_each() -> void:
    _log("after_each")

func test_pass() -> void:
    assert_true(true)
