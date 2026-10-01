extends GdToolsTest

class_name NativeSignalAssertionSuite

signal probe_signal

# Emission-capture coverage for watch_signals and the signal assertions.
# The passing half pins the capture contract; the failing half is inspected
# by the e2e layer for capture detail and unwatched-target guidance.
# An inner-class emitter covers watching an arbitrary RefCounted, while the
# suite itself (a Node) covers node targets.


class Emitter:
	signal ping(value)


func _emitter() -> Emitter:
	return Emitter.new()


func test_watch_node_target_and_assert_emitted() -> void:
	watch_signals(self)
	probe_signal.emit()
	assert_signal_emitted(self, "probe_signal")


func test_watch_refcounted_target_and_assert_emitted() -> void:
	var emitter := _emitter()
	watch_signals(emitter)
	emitter.ping.emit(7)
	assert_signal_emitted(emitter, "ping")


func test_not_emitted_passes_without_emission() -> void:
	watch_signals(self)
	assert_signal_not_emitted(self, "probe_signal")


func test_emitted_fails_without_emission() -> void:
	watch_signals(self)
	assert_signal_emitted(self, "probe_signal", "nothing fired")


func test_not_emitted_fails_when_emitted() -> void:
	watch_signals(self)
	probe_signal.emit()
	assert_signal_not_emitted(self, "probe_signal")


func test_unwatched_target_fails_with_guidance() -> void:
	assert_signal_emitted(_emitter(), "ping")


func test_unwatched_not_emitted_fails_with_guidance() -> void:
	assert_signal_not_emitted(_emitter(), "ping")


func test_capture_resets_between_tests() -> void:
	# Runs after an emitting test in the same manifest; leaked recordings
	# from that test would make this assertion fail.
	watch_signals(self)
	assert_signal_not_emitted(self, "probe_signal")


func test_emit_count_passes_on_exact_count() -> void:
	watch_signals(self)
	probe_signal.emit()
	probe_signal.emit()
	assert_signal_emit_count(self, "probe_signal", 2)


func test_emit_count_fails_on_wrong_count() -> void:
	watch_signals(self)
	probe_signal.emit()
	assert_signal_emit_count(self, "probe_signal", 2)


func test_with_args_passes_on_any_matching_emission() -> void:
	var emitter := _emitter()
	watch_signals(emitter)
	emitter.ping.emit(1)
	emitter.ping.emit(2)
	assert_signal_emitted_with_args(emitter, "ping", [2])


func test_with_args_any_wildcard_matches() -> void:
	var emitter := _emitter()
	watch_signals(emitter)
	emitter.ping.emit("alpha")
	assert_signal_emitted_with_args(emitter, "ping", ["any"])


func test_with_args_fails_when_no_emission_matches() -> void:
	var emitter := _emitter()
	watch_signals(emitter)
	emitter.ping.emit(1)
	emitter.ping.emit(3)
	assert_signal_emitted_with_args(emitter, "ping", [2])


func test_emit_wait_passes_after_emission() -> void:
	_emit_probe_after(2)
	await assert_signal_emitted_after(probe_signal, 5.0)


func test_emit_wait_fails_on_timeout() -> void:
	await assert_signal_emitted_after(probe_signal, 0.05)


func _emit_probe_after(frames: int) -> void:
	for index in frames:
		await get_tree().process_frame
	probe_signal.emit()
