extends RefCounted

## A simple calculator for integration testing.


func add(a: float, b: float) -> float:
	return a + b


func subtract(a: float, b: float) -> float:
	return a - b


func multiply(a: float, b: float) -> float:
	return a * b


func divide(a: float, b: float) -> Dictionary:
	if b == 0.0:
		return {"error": "division by zero"}
	return {"result": a / b}
