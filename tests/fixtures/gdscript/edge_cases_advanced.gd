extends Node

# Pattern 5: @onready / @export annotations (should produce NO coverage points)
@onready var node: Node
@export var speed: float = 1.0

# Pattern 3: setter/getter blocks
var health: int = 100:
	set(value):
		health = value
	get:
		return health

func _ready() -> void:
	# Pattern 8: super() call
	super._ready()
	# Pattern 1: ternary expression (gap: both branches should be tracked)
	var x: int = 10
	var r = 42 if x > 5 else 0
	# Pattern 6: builtin function call
	var n = absi(-5)
	# Pattern 7: await expression
	await get_tree().process_frame
	# Pattern 2: lambda function
	var cb = func():
		return 42
	var result = cb.call()

func handle_match(value: int) -> void:
	# Pattern 4: match with bind pattern (correct syntax: var y:)
	match value:
		1:
			print("one")
		var y:
			print(y)
		_:
			print("default")
