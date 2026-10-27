extends Node

func classify_input(action: String, fast: bool, slow: bool) -> String:
	if action == "idle":
		return "idle"
	elif (
		action == "run"
		or fast
		or slow
	):
		return "moving"
	else:
		return "other"


func describe_pair(pair: Array) -> String:
	match pair:
		[1,
			2]:
			return "low"
		_:
			return "other"
