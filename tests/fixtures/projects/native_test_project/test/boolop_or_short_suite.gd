extends GdToolsTest
class_name OrShortSuite


func test_left_operand_short_circuits() -> void:
	assert_eq(BoolopCoverageSubject.new().either(true, false), true)
