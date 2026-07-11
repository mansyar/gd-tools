extends Node

signal value_changed(new_value: int)
enum Status { RED, GREEN, BLUE }

func empty_function() -> void:
	pass

func loop_with_break(arr: Array) -> void:
	for item in arr:
		if item == null:
			break
		print(item)
	return

func loop_with_continue(arr: Array) -> void:
	for item in arr:
		if item == null:
			continue
		print(item)
	return

func ternary_example(x: int) -> int:
	var result = 42 if x > 5 else 0
	return result

func while_with_break() -> void:
	var i = 0
	while true:
		if i >= 10:
			break
		i += 1
	return
