extends RefCounted

## Collaborator exercised by the bridge mocking suite: doubles, stubs, and
## the call-assertion family run through the GUT compatibility bridge.


func greet(name: String) -> String:
	return "Hello, %s!" % name


func add(left: int, right: int) -> int:
	return left + right
