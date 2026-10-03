extends GdToolsTest
class_name TernaryTrueSuite


func test_true_arm_only() -> void:
	assert_eq(TernaryCoverageSubject.new().pick(true), 10)
