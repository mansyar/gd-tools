extends GdToolsTest
class_name NativeLifecycleSuite

func _log(event: String) -> void:
	var log_file = FileAccess.open("res://lifecycle.log", FileAccess.READ_WRITE)
	if log_file == null:
		log_file = FileAccess.open("res://lifecycle.log", FileAccess.WRITE)
	log_file.seek_end()
	log_file.store_line(event)
	log_file.close()

func before_all() -> void:
	_log("before_all")

func before_each() -> void:
	_log("before_each")

func after_each() -> void:
	_log("after_each")

func after_all() -> void:
	_log("after_all")

func test_pass() -> void:
	_log("test_pass")
	assert_true(true)

func test_fail() -> void:
	_log("test_fail")
	assert_true(false, "intentional lifecycle failure")
