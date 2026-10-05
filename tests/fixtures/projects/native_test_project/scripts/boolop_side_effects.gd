extends RefCounted
class_name BoolopSideEffects

var right_calls := 0
var cond_calls := 0


func cond(value: bool) -> bool:
	cond_calls += 1
	return value


func right(value: bool) -> bool:
	right_calls += 1
	return value


func and_pick(a: bool, b: bool) -> bool:
	return cond(a) and right(b)


func or_pick(a: bool, b: bool) -> bool:
	return cond(a) or right(b)
