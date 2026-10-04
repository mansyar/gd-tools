extends GdToolsTest

class_name NativeSnapshotSerializerSuite

# Serialization contract for the snapshot subsystem (tier 1: values).
# The passing tests pin the exact canonical text the snapshot store writes,
# so dictionary key ordering and indentation stay stable across platforms.
# Tier 2 (objects) and tier 3 (node trees) are covered by later suites.


const SERIALIZER := preload(
	"res://addons/gd-tools-test/gd_tools_snapshot_serializer.gd"
)

const SUBJECT := preload("res://scripts/snapshot_subject.gd")
const NODE_SUBJECT := preload("res://scripts/snapshot_node_subject.gd")


func test_renders_primitives() -> void:
	assert_eq(SERIALIZER.render(null), "null")
	assert_eq(SERIALIZER.render(true), "true")
	assert_eq(SERIALIZER.render(false), "false")
	assert_eq(SERIALIZER.render(42), "42")
	assert_eq(SERIALIZER.render(-7), "-7")
	assert_eq(SERIALIZER.render(3.5), "3.5")
	assert_eq(SERIALIZER.render("text"), "\"text\"")


func test_renders_arrays_multiline() -> void:
	assert_eq(SERIALIZER.render([1, 2]), "[\n  1,\n  2\n]")


func test_renders_empty_containers_compact() -> void:
	assert_eq(SERIALIZER.render([]), "[]")
	assert_eq(SERIALIZER.render({}), "{}")


func test_sorts_dictionary_keys() -> void:
	assert_eq(
		SERIALIZER.render({"b": 2, "a": 1}),
		"{\n  \"a\": 1,\n  \"b\": 2\n}"
	)


func test_renders_nested_containers_indented() -> void:
	assert_eq(
		SERIALIZER.render({"outer": [1, {"inner": 2}]}),
		"""{
  "outer": [
    1,
    {
      "inner": 2
    }
  ]
}"""
	)


func test_render_is_deterministic_across_calls() -> void:
	var value := {"list": [3, 1], "name": "player", "meta": {"z": 1, "a": 2}}
	var first := SERIALIZER.render(value)
	var second := SERIALIZER.render(value)
	assert_eq(first, second)
	assert_eq(
		first,
		"""{
  "list": [
    3,
    1
  ],
  "meta": {
    "a": 2,
    "z": 1
  },
  "name": "player"
}"""
	)


func test_renders_script_object_properties() -> void:
	assert_eq(
		SERIALIZER.render(SUBJECT.new()),
		"""Object:res://scripts/snapshot_subject.gd
  hp: 100
  stats: {
    "mp": 5
  }
  tags: [
    "a",
    "b"
  ]"""
	)


func test_renders_object_without_script() -> void:
	assert_eq(SERIALIZER.render(RefCounted.new()), "Object:RefCounted")


func test_renders_node_tree_structure() -> void:
	var root := Node.new()
	var child: Node2D = NODE_SUBJECT.new()
	var grand := Node.new()
	child.name = "Child"
	grand.name = "Grand"
	root.add_child(child)
	child.add_child(grand)
	assert_eq(
		SERIALIZER.render(root),
		"""Node:/ (Node)
  Node:/Child (Node2D)
    label: "hud"
    speed: 5.0
    Node:/Child/Grand (Node)"""
	)
	root.free()


func test_renders_node_without_script() -> void:
	assert_eq(SERIALIZER.render(Node.new()), "Node:/ (Node)")
