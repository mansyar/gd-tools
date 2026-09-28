extends GutTest
class_name BridgeCoverageSuite

func test_subject_branches() -> void:
	var subject: RefCounted = preload("res://scripts/bridge_subject.gd").new()
	assert_eq(subject.double(3), 6)
	assert_eq(subject.gate(20), "high")
	assert_eq(subject.gate(1), "low")
