extends GutTest
class_name BridgeMockingSuite

# Mocking constructs are native runtime features the bridge inherits from
# GdToolsTest; the preflight scan must not reject suites that use them.

const SUBJECT := preload("res://scripts/bridge_mock_subject.gd")


func test_bridge_double_and_stub_work() -> void:
	var d = double(SUBJECT)
	# Unstubbed typed method answers the type's zero value (GUT semantics).
	assert_eq(d.add(2, 3), 0)
	stub(d, "add").to_return(99)
	assert_eq(d.add(2, 3), 99)


func test_bridge_partial_double_runs_real() -> void:
	var p = partial_double(SUBJECT)
	assert_eq(p.add(2, 3), 5)
	assert_eq(p.greet("bridge"), "Hello, bridge!")


func test_bridge_call_assertions_work() -> void:
	var d = double(SUBJECT)
	d.greet("world")
	assert_called(d, "greet")
	assert_call_count(d, "greet", 1)
	assert_call_arguments(d, "greet", ["world"])
	assert_not_called(d, "add")
