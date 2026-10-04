extends RefCounted
class_name NativeMockSubject

## Simple collaborator used as a doubling target by mocking suites.
##
## `events` records every real method entry so a test can prove whether the
## real implementation ran (partial_double) or not (double) without needing
## any stubbing machinery.

var events: Array[String] = []
var count: int = 0


func greet(name: String) -> String:
	events.append("greet")
	return "Hello, %s!" % name


func add(left: int, right: int) -> int:
	events.append("add")
	return left + right


func note(event: String) -> void:
	events.append(event)


func pick(option):
	# Deliberately untyped: doubles of Variant-returning methods can answer
	# with null (GUT semantics), unlike typed primitive returns.
	events.append("pick")
	return option
