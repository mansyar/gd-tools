extends GutTest

var _calc: Object

func before_each():
	_calc = load("res://scripts/calculator.gd").new()

func after_each():
	_calc = null

func test_divide_normal():
	var result = _calc.divide(10.0, 2.0)
	assert_eq(result["result"], 5.0)

func test_divide_by_zero():
	var result = _calc.divide(10.0, 0.0)
	assert_eq(result["error"], "division by zero")
