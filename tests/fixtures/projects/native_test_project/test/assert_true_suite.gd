extends GdToolsTest
class_name AssertTrueSuite


func test_assert_holds() -> void:
	AssertCoverageSubject.new().check(1)
