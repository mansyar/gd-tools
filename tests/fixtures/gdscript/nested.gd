extends Node

func deep_nest(items: Array) -> void:
	for i in range(items.size()):
		if items[i] != null:
			if i > 0:
				match items[i]:
					1:
						continue
					_:
						print("found")
		else:
			print("empty")
	return
