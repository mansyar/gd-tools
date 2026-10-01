extends GdToolsTest

class_name NativeSignalHookScopeSuite

signal probe_signal

# Hook-scope semantics for watch_signals: a watch opened in before_each runs
# on the same test instance, so hook-time emissions must be captured and the
# watch must stay live for the whole test body.

var emitted_in_hook := false


func before_each() -> void:
	watch_signals(self)
	probe_signal.emit()
	emitted_in_hook = true


func test_hook_watched_signal_emission_is_captured() -> void:
	assert_true(emitted_in_hook)
	assert_signal_emit_count(self, "probe_signal", 1)


func test_hook_watch_covers_whole_test_body() -> void:
	probe_signal.emit()
	assert_signal_emit_count(self, "probe_signal", 2)


func test_hook_watch_isolated_between_tests() -> void:
	# A fresh instance per test means the hook watch/emission starts clean.
	assert_signal_emit_count(self, "probe_signal", 1)
