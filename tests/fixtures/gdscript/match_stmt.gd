extends Node

func handle_state(state: int) -> void:
	match state:
		0:
			print("idle")
		1:
			print("running")
		2:
			print("paused")
		_:
			print("unknown")
	return
