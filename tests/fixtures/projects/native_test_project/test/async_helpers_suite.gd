extends GdToolsTest
class_name NativeAsyncHelpersSuite

func test_process_frame() -> void:
	await wait_process_frame()
	assert_true(true)

func test_physics_frames() -> void:
	await wait_physics_frames(2)
	assert_true(true)

func test_timer() -> void:
	await wait_seconds(0.01)
	assert_true(true)

func test_signal() -> void:
	await wait_for_signal(get_tree().process_frame)
	assert_true(true)
