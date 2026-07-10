extends GutTest


func test_always_fails():
	assert_eq(1, 2, "This test always fails")
