extends GdToolsTest
class_name NativeParameterizeSuite

var marker := ""


func before_all() -> void:
	parameterize(["value", "label"], [[1, "admin"], [2, "user"]])


func before_each() -> void:
	marker = "setup"


func after_each() -> void:
	pass


func test_ranked(value: int, label: String) -> void:
	assert_eq(marker, "setup")
	assert_eq(value, 1)
	assert_eq(label, "admin")


func test_plain() -> void:
	assert_eq(marker, "setup")


func test_async_value(value: int, label: String) -> void:
	await wait_process_frame()
	assert_true(value > 0)
	assert_true(label != "")


func test_payload() -> void:
	var payload = use_parameters([{"a": 1}, {"b": 2}])
	assert_not_null(payload)
