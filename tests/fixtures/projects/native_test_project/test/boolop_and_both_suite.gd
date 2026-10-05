extends GdToolsTest
class_name AndBothSuite


func test_both_operands_evaluated() -> void:
	assert_eq(BoolopCoverageSubject.new().both(true, true), true)
