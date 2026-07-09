extends RefCounted

## A simple calculator for spike testing.
##
## This file will be instrumented at runtime by the coverage spike.

func divide(a: float, b: float) -> Dictionary:
	if b == 0.0:
		return {"error": "division by zero"}
	else:
		return {"result": a / b}
