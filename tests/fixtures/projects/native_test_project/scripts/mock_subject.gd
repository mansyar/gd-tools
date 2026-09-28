extends RefCounted
class_name NativeMockSubject

## Simple collaborator used as a doubling target by mocking suites.
##
## `events` records every real method entry so a test can prove whether the
## real implementation ran (partial_double) or not (double) without needing
## any stubbing machinery.

var events: Array[String] = []


func greet(name: String) -> String:
	events.append("greet")
	return "Hello, %s!" % name


func add(left: int, right: int) -> int:
	events.append("add")
	return left + right


func note(event: String) -> void:
	events.append(event)
