extends GdToolsTest
class_name NativeCoverageSuite

func test_statement_and_branch_coverage() -> void:
	var subject := NativeCoverageSubject.new()
	assert_eq(subject.choose(true), 1)
	assert_eq(subject.choose(false), 0)
