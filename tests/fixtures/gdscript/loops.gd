extends Node

func count_down(start: int) -> void:
	var i = start
	while i > 0:
		print(i)
		i -= 1
	return

func iterate_range() -> void:
	for j in range(5):
		print(j)
	return

func iterate_typed() -> void:
	for k: int in range(3):
		print(k)
	return
