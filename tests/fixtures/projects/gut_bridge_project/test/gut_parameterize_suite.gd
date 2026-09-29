extends GutTest
class_name BridgeParameterizeSuite

# Bridge suites parameterize exactly like native ones: the same preflight
# validation, case expansion, naming and result contract apply, because the
# bridge shim inherits the native `GdToolsTest` machinery.

func before_all() -> void:
	parameterize(["value", "label"], [[1, "admin"], [2, "user"]])

func test_ranked(value: int, label: String) -> void:
	assert_eq(value, 1)
	assert_eq(label, "admin")

func test_plain() -> void:
	assert_true(true)

func test_item() -> void:
	var item = use_parameters(["alpha", "beta"])
	assert_eq(item, "alpha")
