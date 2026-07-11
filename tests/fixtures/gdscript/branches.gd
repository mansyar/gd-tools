extends Node

func check_value(x: int) -> void:
	if x > 10:
		print("big")
	elif x > 5:
		print("medium")
	else:
		print("small")
	return

func nested_check(x: int, y: int) -> int:
	if x > 0:
		if y > 0:
			return 1
		else:
			return 2
	else:
		if y > 0:
			return 3
		else:
			return 4
	return 0
