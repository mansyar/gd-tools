extends GutTest

var _HookScript: GDScript

func before_each():
	_HookScript = load("res://addons/gd-tools-coverage/pre_run_hook.gd")

func after_each():
	_HookScript = null

func test_inject_single_line():
	var source = "func foo():\n\tprint('hello')"
	var lines = [{"line": 2, "id": 0}]
	var result = _HookScript._inject_trackers(source, 0, lines)
	var expected = "func foo():\n\t_GDTCoverage.hit(0, 0)\n\tprint('hello')"
	assert_eq(result, expected)

func test_inject_multiple_lines_preserves_order():
	var source = "func foo():\n\tif true:\n\t\tprint('yes')\n\telse:\n\t\tprint('no')"
	var lines = [
		{"line": 2, "id": 0},
		{"line": 3, "id": 1},
		{"line": 5, "id": 2}
	]
	var result = _HookScript._inject_trackers(source, 0, lines)
	var expected = "func foo():\n\t_GDTCoverage.hit(0, 0)\n\tif true:\n\t\t_GDTCoverage.hit(0, 1)\n\t\tprint('yes')\n\telse:\n\t\t_GDTCoverage.hit(0, 2)\n\t\tprint('no')"
	assert_eq(result, expected)

func test_inject_bottom_to_top():
	# Pass lines in DESCENDING order - output should match ascending order.
	# This verifies the function sorts internally (bottom-to-top insertion).
	var source = "func foo():\n\tif true:\n\t\tprint('yes')\n\telse:\n\t\tprint('no')"
	var lines = [
		{"line": 5, "id": 2},
		{"line": 3, "id": 1},
		{"line": 2, "id": 0}
	]
	var result = _HookScript._inject_trackers(source, 0, lines)
	var expected = "func foo():\n\t_GDTCoverage.hit(0, 0)\n\tif true:\n\t\t_GDTCoverage.hit(0, 1)\n\t\tprint('yes')\n\telse:\n\t\t_GDTCoverage.hit(0, 2)\n\t\tprint('no')"
	assert_eq(result, expected)

func test_inject_preserves_indentation():
	# Test tab indentation
	var source_tabs = "func foo():\n\tprint('hello')"
	var result_tabs = _HookScript._inject_trackers(source_tabs, 0, [{"line": 2, "id": 0}])
	assert_eq(result_tabs, "func foo():\n\t_GDTCoverage.hit(0, 0)\n\tprint('hello')")
	# Test space indentation
	var source_spaces = "func bar():\n    print('world')"
	var result_spaces = _HookScript._inject_trackers(source_spaces, 1, [{"line": 2, "id": 0}])
	assert_eq(result_spaces, "func bar():\n    _GDTCoverage.hit(1, 0)\n    print('world')")
