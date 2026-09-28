extends GutTest
class_name BridgeLifecycleSuite

func _log(event: String) -> void:
	var log_file := FileAccess.open("res://hook_order.log", FileAccess.READ_WRITE)
	if log_file == null:
		log_file = FileAccess.open("res://hook_order.log", FileAccess.WRITE)
	log_file.seek_end()
	log_file.store_line(event)
	log_file.close()

func prerun_setup() -> void:
	_log("prerun_setup")

func before_all() -> void:
	_log("before_all")

func before_each() -> void:
	_log("before_each")

func after_each() -> void:
	_log("after_each")

func after_all() -> void:
	_log("after_all")

func postrun_teardown() -> void:
	_log("postrun_teardown")

func test_hook_order() -> void:
	_log("test_hook_order")
	assert_true(true)
