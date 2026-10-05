extends RefCounted
class_name AssertCoverageSubject


func check(value: int) -> void:
	assert(value == 1, "value must be 1")
