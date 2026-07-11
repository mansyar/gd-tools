extends GutTest


func before_each():
	_GDTCoverage.set_active(true)
	_GDTCoverage.reset()


func test_hit_records_correctly_when_active():
	_GDTCoverage.hit(0, 5)
	var hits = _GDTCoverage.get_hits()
	assert_true(hits.has(0), "hits should contain file_id 0")
	assert_true(hits[0].has(5), "hits[0] should contain line_id 5")
	assert_eq(hits[0][5], 1, "hit count should be 1")


func test_multiple_hits_increment_counter():
	_GDTCoverage.hit(0, 5)
	_GDTCoverage.hit(0, 5)
	_GDTCoverage.hit(0, 5)
	var hits = _GDTCoverage.get_hits()
	assert_eq(hits[0][5], 3, "hit count should be 3 after 3 hits")


func test_reset_clears_all_data():
	_GDTCoverage.hit(0, 5)
	_GDTCoverage.reset()
	var hits = _GDTCoverage.get_hits()
	assert_eq(hits.size(), 0, "hits should be empty after reset")


func test_hit_noop_when_inactive():
	_GDTCoverage.set_active(false)
	_GDTCoverage.hit(0, 5)
	var hits = _GDTCoverage.get_hits()
	assert_eq(hits.size(), 0, "hits should be empty when inactive")


func test_set_active_is_active_toggle():
	_GDTCoverage.set_active(false)
	assert_false(_GDTCoverage.is_active(), "should be inactive after set_active(false)")
	_GDTCoverage.set_active(true)
	assert_true(_GDTCoverage.is_active(), "should be active after set_active(true)")


func test_get_hits_returns_nested_dictionary():
	_GDTCoverage.hit(1, 10)
	_GDTCoverage.hit(1, 20)
	_GDTCoverage.hit(2, 30)
	var hits = _GDTCoverage.get_hits()
	assert_true(hits.has(1), "hits should contain file_id 1")
	assert_true(hits.has(2), "hits should contain file_id 2")
	assert_eq(hits[1][10], 1, "hits[1][10] should be 1")
	assert_eq(hits[1][20], 1, "hits[1][20] should be 1")
	assert_eq(hits[2][30], 1, "hits[2][30] should be 1")
