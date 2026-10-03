extends GdToolsTest
class_name TernaryFalseSuite


func test_false_arm_only() -> void:
	assert_eq(TernaryCoverageSubject.new().pick(false), 20)
