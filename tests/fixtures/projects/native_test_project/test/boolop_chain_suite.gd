extends GdToolsTest
class_name ChainSuite


func test_chain_short_circuits_at_second_operator() -> void:
	# a and b and c with a=true, b=false: the first right operand (b)
	# evaluates, the second (c) never does.
	assert_eq(BoolopCoverageSubject.new().chain(true, false, true), false)
