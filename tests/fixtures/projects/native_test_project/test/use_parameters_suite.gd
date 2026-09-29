extends GdToolsTest
class_name NativeUseParametersSuite

func test_item() -> void:
	var item = use_parameters(["alpha", "beta"])
	assert_eq(item, "alpha")


func test_flag() -> void:
	var flag = use_parameters({"on": true, "off": false})
	assert_true(flag is bool)

