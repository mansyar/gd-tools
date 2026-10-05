extends RefCounted
class_name BoolopCoverageSubject


func both(a: bool, b: bool) -> bool:
	return a and b


func either(a: bool, b: bool) -> bool:
	return a or b


func chain(a: bool, b: bool, c: bool) -> bool:
	return a and b and c
