extends Node


class Inner:
	# Dropped: no anchor node encloses a class-body initialiser.
	var dropped = 1 if true else 2


func anchors(a: int) -> void:
	var multi = (
		1
		if a > 0
		else 2
	)
	if (1 if a > 0 else 2) > 0:
		print(a)
	for i in range(1 if a > 0 else 2):
		print(i)
	while (a if a > 0 else 0) > 1:
		break
	print(multi)


func orphaned(a: int, x = 1 if a > 0 else 2) -> void:
	print(x)