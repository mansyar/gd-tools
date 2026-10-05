extends GdToolsTest
class_name AndShortSuite


func test_left_operand_short_circuits() -> void:
	assert_eq(BoolopCoverageSubject.new().both(false, true), false)
