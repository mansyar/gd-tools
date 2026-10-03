class_name TernarySideEffects
extends RefCounted


var true_calls: int = 0
var false_calls: int = 0
var cond_calls: int = 0


func truthy() -> int:
	true_calls += 1
	return 10


func falsy() -> int:
	false_calls += 1
	return 20


func pick(cond: bool) -> int:
	cond_calls += 1
	return truthy() if cond else falsy()
