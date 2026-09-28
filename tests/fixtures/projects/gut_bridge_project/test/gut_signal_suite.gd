extends GutTest
class_name BridgeSignalSuite

signal bridge_fired(value: int)

var _emitter: Node


func before_all() -> void:
	_emitter = Node.new()


func after_all() -> void:
	_emitter.free()


func test_signal_emitted_family() -> void:
	watch_signals(self)
	bridge_fired.emit(7)
	assert_signal_emitted(self, "bridge_fired")
	assert_signal_emit_count(self, "bridge_fired", 1)
	assert_signal_emitted_with_parameters(self, "bridge_fired", [7])
	assert_has_signal(self, "bridge_fired")

func test_signal_not_emitted() -> void:
	watch_signals(self)
	assert_signal_not_emitted(self, "bridge_fired")

func test_connected_assertions() -> void:
	var receiver := Node.new()
	assert_not_connected(self, "bridge_fired", receiver, "_on_fired")
	self.bridge_fired.connect(receiver._on_fired)
	assert_connected(self, "bridge_fired", receiver, "_on_fired")
	receiver.free()
