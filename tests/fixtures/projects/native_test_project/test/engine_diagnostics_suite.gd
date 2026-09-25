extends GdToolsTest
class_name NativeEngineDiagnosticsSuite

func test_engine_diagnostics() -> void:
    push_error("native engine error")
    push_warning("native engine warning")
    assert_true(true)
