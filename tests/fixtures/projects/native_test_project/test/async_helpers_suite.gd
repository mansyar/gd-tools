extends GdToolsTest
class_name NativeAsyncHelpersSuite

signal probe_signal

func test_process_frame() -> void:
	await wait_process_frame()
	assert_true(true)

func test_physics_frames() -> void:
	await wait_physics_frames(2)
	assert_true(true)

func test_timer() -> void:
	await wait_seconds(0.01)
	assert_true(true)

func test_signal() -> void:
	await wait_for_signal(get_tree().process_frame)
	assert_true(true)


func _emit_after(delay: float) -> void:
	get_tree().create_timer(delay).timeout.connect(
		probe_signal.emit, CONNECT_ONE_SHOT
	)

func test_wait_for_signal_true_when_emitted() -> void:
	_emit_after(0.05)
	assert_true(await wait_for_signal(probe_signal, 5.0))

func test_wait_for_signal_false_when_never_emitted() -> void:
	assert_false(await wait_for_signal(probe_signal, 0.1))

func test_wait_for_signal_default_budget_when_emitted() -> void:
	_emit_after(0.05)
	assert_true(await wait_for_signal(probe_signal))

func test_wait_for_signal_records_no_own_failure() -> void:
	var before := get_failures().size()
	await wait_for_signal(probe_signal, 0.1)
	assert_eq(get_failures().size(), before)

func test_wait_for_signal_resolves_before_budget() -> void:
	_emit_after(0.05)
	assert_true(await wait_for_signal(probe_signal, 15.0))
