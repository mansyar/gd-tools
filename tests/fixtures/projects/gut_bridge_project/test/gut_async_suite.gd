extends GutTest
class_name BridgeAsyncSuite

signal async_fired

func test_wait_seconds() -> void:
	# Ordering assertion instead of wall-clock: both timers share the engine
	# clock, so this holds even when headless frame deltas diverge from wall
	# time under load. A no-op wait would resume before the flag timer fired.
	var state := {"flag": false}
	get_tree().create_timer(0.05).timeout.connect(func() -> void:
		state["flag"] = true)
	await wait_seconds(0.1)
	assert_true(state["flag"], "wait_seconds resumed after the 0.05s flag timer")

func test_frame_waits() -> void:
	await wait_frames(2)
	await wait_physics_frames(1)
	await wait_idle_frames(1)
	await wait_process_frames(1)
	assert_true(true)

func test_wait_for_signal() -> void:
	await wait_frames(1)
	get_tree().create_timer(0.05).timeout.connect(func() -> void:
		async_fired.emit())
	var received: bool = await wait_for_signal(async_fired, 1.0)
	assert_true(received)

func test_wait_until() -> void:
	var state := {"ready": false}
	var flag_setter := func() -> void:
		state["ready"] = true
	await wait_until(func() -> bool:
		flag_setter.call()
		return state["ready"], 1.0)
	assert_true(state["ready"])

func test_wait_while() -> void:
	var state := {"done": true}
	await wait_while(func() -> bool: return not state["done"], 1.0)
	assert_true(state["done"])

func test_yield_aliases() -> void:
	await yield_frames(1)
	await yield_for(0.05)
	assert_true(true)
