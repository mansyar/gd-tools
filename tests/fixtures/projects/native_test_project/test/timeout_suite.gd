extends GdToolsTest
class_name NativeTimeoutSuite

func test_hangs() -> void:
	await wait_seconds(1.0)
