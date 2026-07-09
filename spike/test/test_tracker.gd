extends GutTest

var _tracker: Object

func before_each():
    _tracker = get_node("/root/_GDTCoverage")
    _tracker.reset()

func after_each():
    _tracker.reset()

func test_hit_records_count():
    _tracker.hit(0, 1)
    _tracker.hit(0, 1)
    var hits = _tracker.get_hits()
    assert_eq(hits["0:1"], 2, "hit(0, 1) called twice should record count 2")

func test_reset_clears_hits():
    _tracker.hit(0, 1)
    _tracker.reset()
    var hits = _tracker.get_hits()
    assert_true(hits.is_empty(), "get_hits() should be empty after reset()")

func test_get_hits_returns_copy():
    _tracker.hit(0, 1)
    var hits = _tracker.get_hits()
    hits["999:999"] = 999
    var hits_again = _tracker.get_hits()
    assert_false(hits_again.has("999:999"), "modifying returned dict should not affect tracker's internal dict")
