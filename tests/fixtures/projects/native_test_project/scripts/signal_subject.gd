extends RefCounted
class_name NativeSignalSubject

## Simple signal source used as a doubling target by the signal assertion
## suite. Doubles inherit the declared signal, so a double of this script can
## be watched with watch_signals() like any other Object.

signal ping(value)


func emit_ping(value) -> void:
	ping.emit(value)
