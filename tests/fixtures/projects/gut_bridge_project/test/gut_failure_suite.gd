extends GutTest
class_name BridgeFailureSuite

func test_intentional_failure() -> void:
	assert_eq(1, 2, "intentional bridge failure")
