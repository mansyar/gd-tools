extends GdToolsTest
class_name OrRightSuite


func test_right_operand_evaluated() -> void:
	assert_eq(BoolopCoverageSubject.new().either(false, true), true)
