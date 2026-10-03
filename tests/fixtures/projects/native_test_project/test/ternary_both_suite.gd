extends GdToolsTest
class_name TernaryBothSuite


func test_both_arms() -> void:
	assert_eq(TernaryCoverageSubject.new().pick(true), 10)
	assert_eq(TernaryCoverageSubject.new().pick(false), 20)
