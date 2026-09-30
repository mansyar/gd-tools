"""E2E checks for native Godot integration metadata preflight."""

import json
import os
import shutil
import subprocess
from pathlib import Path
from textwrap import dedent

import pytest

from conftest import import_godot_project

pytestmark = pytest.mark.e2e

NATIVE_FIXTURE = (
    Path(__file__).parent.parent
    / "fixtures"
    / "projects"
    / "native_test_project"
)
NATIVE_ADDON = (
    Path(__file__).parent.parent.parent
    / "src"
    / "gd_tools"
    / "addons"
    / "gd-tools-test"
)
PREFLIGHT_SCRIPT = "res://addons/gd-tools-test/gd_tools_test_preflight.gd"


def _suite_source(
    integration: object | None = None,
    *,
    body: str = "",
) -> str:
    """Create a native suite script with optional integration metadata."""
    lines = ['extends "res://addons/gd-tools-test/gd_tools_test.gd"']
    if integration is not None:
        lines.append(
            "const INTEGRATION := "
            + json.dumps(integration, separators=(",", ":"))
        )
    if body:
        lines.append(body.rstrip())
    lines.extend(
        [
            "func test_pass() -> void:",
            "\tpass",
            "func test_other() -> void:",
            "\tpass",
            "func test_replace_scene() -> void:",
            "\tpass",
            "func test_add_resource() -> void:",
            "\tpass",
            "func test_remove() -> void:",
            "\tpass",
            "func test_unselected() -> void:",
            "\tpass",
        ]
    )
    return "\n".join(lines) + "\n"


def _prepare_project(
    tmp_path: Path,
    godot_bin: str,
    files: dict[str, str],
) -> Path:
    """Create and import an isolated project containing preflight fixtures."""
    project = tmp_path / "native_preflight_project"
    shutil.copytree(NATIVE_FIXTURE, project)
    for relative_path, content in files.items():
        destination = project / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(dedent(content).lstrip(), encoding="utf-8")
    shutil.copytree(NATIVE_ADDON, project / "addons" / "gd-tools-test")

    import_godot_project(godot_bin, project)
    return project


def _manifest(
    project: Path,
    *,
    suite_path: str = "res://test/integration_suite.gd",
    tests: list[str] | None = None,
    protocol_version: int = 3,
) -> dict:
    """Build a discovery manifest for direct preflight execution."""
    return {
        "protocol_version": protocol_version,
        "project_root": str(project),
        "runtime": "native",
        "suites": [
            {
                "name": "NativePreflightSuite",
                "path": suite_path,
                "tags": ["native"],
                "tests": [
                    {"name": name, "timeout_seconds": 5.0}
                    for name in (tests or ["test_pass"])
                ],
            }
        ],
        "coverage": {"enabled": False},
    }


def _run_preflight(
    project: Path,
    godot_bin: str,
    manifest: dict,
    result_path: Path,
):
    """Run the bundled Godot metadata preflight directly."""
    manifest_path = result_path.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    env = os.environ.copy()
    env["GD_TOOLS_NATIVE_PREFLIGHT_MANIFEST"] = str(manifest_path)
    env["GD_TOOLS_NATIVE_PREFLIGHT_RESULT"] = str(result_path)
    return subprocess.run(
        [
            godot_bin,
            "--headless",
            "--path",
            str(project),
            "--script",
            PREFLIGHT_SCRIPT,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=30,
    )


def test_preflight_defaults_without_integration_constant(
    godot_bin,
    tmp_path,
):
    """A legacy native suite receives explicit empty headless metadata."""
    project = _prepare_project(
        tmp_path,
        godot_bin,
        {"test/integration_suite.gd": _suite_source()},
    )
    result_path = tmp_path / "preflight-defaults.json"

    process = _run_preflight(
        project,
        godot_bin,
        _manifest(project),
        result_path,
    )

    assert process.returncode == 0, process.stdout + process.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["protocol_version"] == 3
    assert payload["status"] == "ok"
    assert payload["error"] is None
    suite = payload["suites"][0]
    assert suite["integration"] == {
        "scene": None,
        "resources": {},
        "mode": "headless",
    }
    assert suite["tests"][0]["integration"] == {
        "scene": None,
        "resources": {},
    }


def test_preflight_merges_integration_field_by_field(godot_bin, tmp_path):
    """Suite defaults and selected-test overrides merge without mutation."""
    integration = {
        "scene": "res://scenes/main.tscn",
        "resources": {
            "config": "res://resources/config.tres",
            "stats": "res://resources/stats.tres",
        },
        "mode": "windowed",
        "tests": {
            "test_replace_scene": {
                "scene": "res://scenes/alternate.tscn",
            },
            "test_add_resource": {
                "resources": {"extra": "res://resources/extra.tres"},
            },
            "test_remove": {
                "scene": None,
                "resources": {"stats": None},
            },
            "test_unselected": {
                "resources": {"future": "res://resources/extra.tres"},
            },
        },
    }
    files = {
        "test/integration_suite.gd": _suite_source(integration),
        "scenes/main.tscn": (
            '[gd_scene format=3]\n\n[node name="Main" type="Node"]\n'
        ),
        "scenes/alternate.tscn": (
            '[gd_scene format=3]\n\n[node name="Alternate" type="Node"]\n'
        ),
        "resources/config.tres": (
            '[gd_resource type="Resource" format=3]\n\n[resource]\n'
        ),
        "resources/stats.tres": (
            '[gd_resource type="Resource" format=3]\n\n[resource]\n'
        ),
        "resources/extra.tres": (
            '[gd_resource type="Resource" format=3]\n\n[resource]\n'
        ),
    }
    project = _prepare_project(tmp_path, godot_bin, files)
    result_path = tmp_path / "preflight-merge.json"

    process = _run_preflight(
        project,
        godot_bin,
        _manifest(
            project,
            tests=[
                "test_pass",
                "test_replace_scene",
                "test_add_resource",
                "test_remove",
            ],
        ),
        result_path,
    )

    assert process.returncode == 0, process.stdout + process.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    suite = payload["suites"][0]
    assert suite["integration"] == {
        "scene": "res://scenes/main.tscn",
        "resources": {
            "config": "res://resources/config.tres",
            "stats": "res://resources/stats.tres",
        },
        "mode": "windowed",
    }
    tests = {test["name"]: test["integration"] for test in suite["tests"]}
    assert tests["test_pass"] == {
        "scene": "res://scenes/main.tscn",
        "resources": {
            "config": "res://resources/config.tres",
            "stats": "res://resources/stats.tres",
        },
    }
    assert tests["test_replace_scene"] == {
        "scene": "res://scenes/alternate.tscn",
        "resources": {
            "config": "res://resources/config.tres",
            "stats": "res://resources/stats.tres",
        },
    }
    assert tests["test_add_resource"]["resources"] == {
        "config": "res://resources/config.tres",
        "stats": "res://resources/stats.tres",
        "extra": "res://resources/extra.tres",
    }
    assert tests["test_remove"] == {
        "scene": None,
        "resources": {"config": "res://resources/config.tres"},
    }
    assert "test_unselected" not in tests


@pytest.mark.parametrize(
    ("integration", "expected_error"),
    [
        ({"unknown": True}, "unknown field 'unknown'"),
        ({"mode": "borderless"}, "headless"),
        ({"scene": "scenes/main.tscn"}, "res://"),
        ({"scene": "res://scenes/missing.tscn"}, "does not exist"),
        ({"resources": []}, "resources must be a dictionary"),
        (
            {"resources": {"bad": "relative.tres"}},
            "res://",
        ),
        ({"tests": {"missing": {}}}, "unknown test 'missing'"),
        (
            {"tests": {"test_pass": {"mode": "windowed"}}},
            "per-test declarations do not support field 'mode'",
        ),
    ],
    ids=[
        "unknown-root-field",
        "invalid-mode",
        "relative-scene",
        "missing-scene",
        "malformed-resources",
        "relative-resource",
        "unknown-test",
        "per-test-mode",
    ],
)
def test_preflight_rejects_malformed_declarations(
    godot_bin,
    tmp_path,
    integration,
    expected_error,
):
    """Malformed metadata produces structured exit-code-2 diagnostics."""
    project = _prepare_project(
        tmp_path,
        godot_bin,
        {"test/integration_suite.gd": _suite_source(integration)},
    )
    result_path = tmp_path / "preflight-invalid.json"

    process = _run_preflight(
        project,
        godot_bin,
        _manifest(project),
        result_path,
    )

    assert process.returncode == 2, process.stdout + process.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["protocol_version"] == 3
    assert payload["status"] == "error"
    assert payload["suites"] == []
    assert "res://test/integration_suite.gd" in payload["error"]
    assert expected_error in payload["error"]


def test_preflight_resolves_overrides_for_parameterized_tests(
    godot_bin, tmp_path
):
    """A parameterized method is a known test once its declaration matches.

    Python discovery includes parameterized ``test_*`` methods, so an
    override targeting one must merge like any other test when a
    ``before_all`` declaration provides matching parameters.
    """
    integration = {
        "tests": {
            "test_ranked": {
                "scene": "res://scenes/main.tscn",
            }
        }
    }
    body = (
        "func before_all() -> void:\n"
        '\tparameterize(["value"], [[1], [2]])\n'
        "\n"
        "func test_ranked(value: int) -> void:\n"
        "\tpass"
    )
    project = _prepare_project(
        tmp_path,
        godot_bin,
        {
            "test/integration_suite.gd": _suite_source(integration, body=body),
            "scenes/main.tscn": (
                '[gd_scene format=3]\n\n[node name="Main" type="Node"]\n'
            ),
        },
    )
    result_path = tmp_path / "preflight-parameterized.json"

    process = _run_preflight(
        project,
        godot_bin,
        _manifest(project, tests=["test_ranked"]),
        result_path,
    )

    assert process.returncode == 0, process.stdout + process.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    tests = {test["name"]: test for test in payload["suites"][0]["tests"]}
    assert tests["test_ranked"]["integration"] == {
        "scene": "res://scenes/main.tscn",
        "resources": {},
    }
    assert tests["test_ranked"]["parameters"] == {
        "names": ["value"],
        "values": [[1], [2]],
    }


def test_preflight_resolves_parameterize_declaration_metadata(
    godot_bin, tmp_path
):
    """A matching declaration records per-case metadata on its method."""
    body = (
        "func before_all() -> void:\n"
        '\tparameterize(["value", "label"], [[1, "admin"], [2, "user"]])\n'
        "\n"
        "func test_ranked(value: int, label: String) -> void:\n"
        "\tpass\n"
        "func test_plain() -> void:\n"
        "\tpass"
    )
    project = _prepare_project(
        tmp_path,
        godot_bin,
        {"test/integration_suite.gd": _suite_source(body=body)},
    )
    result_path = tmp_path / "preflight-parameters.json"

    process = _run_preflight(
        project,
        godot_bin,
        _manifest(project, tests=["test_ranked", "test_plain"]),
        result_path,
    )

    assert process.returncode == 0, process.stdout + process.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    tests = {test["name"]: test for test in payload["suites"][0]["tests"]}
    assert tests["test_ranked"]["parameters"] == {
        "names": ["value", "label"],
        "values": [[1, "admin"], [2, "user"]],
    }
    assert "parameters" not in tests["test_plain"]


def test_preflight_accepts_empty_parameter_values(godot_bin, tmp_path):
    """An empty values list is a valid declaration resolved as skipped."""
    body = (
        "func before_all() -> void:\n"
        '\tparameterize(["value"], [])\n'
        "\n"
        "func test_ranked(value: int) -> void:\n"
        "\tpass"
    )
    project = _prepare_project(
        tmp_path,
        godot_bin,
        {"test/integration_suite.gd": _suite_source(body=body)},
    )
    result_path = tmp_path / "preflight-empty-parameters.json"

    process = _run_preflight(
        project,
        godot_bin,
        _manifest(project, tests=["test_ranked"]),
        result_path,
    )

    assert process.returncode == 0, process.stdout + process.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    tests = {test["name"]: test for test in payload["suites"][0]["tests"]}
    assert tests["test_ranked"]["parameters"] == {
        "names": ["value"],
        "values": [],
    }


@pytest.mark.parametrize(
    ("body", "expected_error"),
    [
        (
            (
                "func before_all() -> void:\n"
                '\tparameterize(["value", "label"], [[1, "admin"], [2]])\n'
                "\n"
                "func test_ranked(value: int, label: String) -> void:\n"
                "\tpass"
            ),
            "parameter set 1 has 1 value(s); expected 2",
        ),
        (
            (
                "func before_all() -> void:\n"
                '\tparameterize("value", [[1]])\n'
                "\n"
                "func test_ranked(value: int) -> void:\n"
                "\tpass"
            ),
            "parameterize names must be an array of strings",
        ),
        (
            (
                "func before_all() -> void:\n"
                "\tparameterize([1], [[1]])\n"
                "\n"
                "func test_ranked(value: int) -> void:\n"
                "\tpass"
            ),
            "parameterize names must be non-empty strings",
        ),
        (
            (
                "func before_all() -> void:\n"
                '\tparameterize(["value", "value"], [[1, 2]])\n'
                "\n"
                "func test_ranked(value: int, label: int) -> void:\n"
                "\tpass"
            ),
            "duplicate parameter name 'value'",
        ),
        (
            (
                "func before_all() -> void:\n"
                '\tparameterize(["value", " "], [[1, 2]])\n'
                "\n"
                "func test_ranked(value: int, label: int) -> void:\n"
                "\tpass"
            ),
            "parameterize names must be non-empty strings",
        ),
        (
            (
                "func before_all() -> void:\n"
                "\tparameterize([], [])\n"
                "\n"
                "func test_ranked(value: int) -> void:\n"
                "\tpass"
            ),
            "parameterize names must not be empty",
        ),
        (
            (
                "func before_all() -> void:\n"
                '\tparameterize(["value"], [1, 2])\n'
                "\n"
                "func test_ranked(value: int) -> void:\n"
                "\tpass"
            ),
            "parameter set 0 must be an array",
        ),
        (
            (
                "const LIMIT := 3\n"
                "func before_all() -> void:\n"
                '\tparameterize(["value"], [[LIMIT]])\n'
                "\n"
                "func test_ranked(value: int) -> void:\n"
                "\tpass"
            ),
            "must be literal values",
        ),
        (
            "func test_ranked(value: int) -> void:\n\tpass",
            "no parameterize declaration was found in before_all",
        ),
        (
            (
                "func before_all() -> void:\n"
                '\tparameterize(["value"], [[1]])\n'
                "\n"
                "func test_ranked(value: int, extra: int) -> void:\n"
                "\tpass"
            ),
            "takes 2 parameters but the parameterize declaration provides 1",
        ),
        (
            (
                "func before_all() -> void:\n"
                '\tparameterize(["value"], [[1]])\n'
                "\n"
                "func test_plain() -> void:\n"
                "\tpass"
            ),
            "does not match any test method",
        ),
        (
            (
                "func before_all() -> void:\n"
                '\tparameterize(["value"], [[1]])\n'
                '\tparameterize(["label"], [["a"]])\n'
                "\n"
                "func test_ranked(value: int) -> void:\n"
                "\tpass"
            ),
            "exactly one parameterize declaration",
        ),
    ],
    ids=[
        "mismatched-lengths",
        "names-not-array",
        "name-not-string",
        "duplicate-names",
        "blank-name",
        "empty-names",
        "value-sets-not-arrays",
        "unresolvable-expression",
        "missing-declaration",
        "arity-mismatch",
        "declaration-without-test",
        "multiple-declarations",
    ],
)
def test_preflight_rejects_parameterize_declarations(
    godot_bin,
    tmp_path,
    body,
    expected_error,
):
    """Malformed parameterize declarations produce exit-code-2 diagnostics."""
    project = _prepare_project(
        tmp_path,
        godot_bin,
        {"test/integration_suite.gd": _suite_source(body=body)},
    )
    result_path = tmp_path / "preflight-parameterize-invalid.json"

    process = _run_preflight(
        project,
        godot_bin,
        _manifest(project, tests=["test_ranked"]),
        result_path,
    )

    assert process.returncode == 2, process.stdout + process.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["protocol_version"] == 3
    assert payload["status"] == "error"
    assert payload["suites"] == []
    assert "res://test/integration_suite.gd" in payload["error"]
    assert expected_error in payload["error"]


def test_preflight_rejects_protocol_v1(godot_bin, tmp_path):
    """A version-mismatched discovery manifest returns a structured error."""
    project = _prepare_project(
        tmp_path,
        godot_bin,
        {"test/integration_suite.gd": _suite_source()},
    )
    result_path = tmp_path / "preflight-protocol.json"

    process = _run_preflight(
        project,
        godot_bin,
        _manifest(project, protocol_version=1),
        result_path,
    )

    assert process.returncode == 2, process.stdout + process.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["status"] == "error"
    assert "protocol_version 3" in payload["error"]


def test_preflight_reports_script_load_failure(godot_bin, tmp_path):
    """A missing suite script is an actionable infrastructure error."""
    project = _prepare_project(
        tmp_path,
        godot_bin,
        {"test/integration_suite.gd": _suite_source()},
    )
    result_path = tmp_path / "preflight-load-failure.json"

    process = _run_preflight(
        project,
        godot_bin,
        _manifest(project, suite_path="res://test/missing_suite.gd"),
        result_path,
    )

    assert process.returncode == 2, process.stdout + process.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["status"] == "error"
    assert "res://test/missing_suite.gd" in payload["error"]
    assert "load" in payload["error"].lower()


def test_preflight_does_not_instantiate_or_execute_suite(godot_bin, tmp_path):
    """Loading metadata has no suite construction or lifecycle side effects."""
    body = dedent("""
        func _init() -> void:
        \tvar file := FileAccess.open("res://preflight-side-effect.txt", FileAccess.WRITE)
        \tif file != null:
        \t\tfile.store_line("constructed")
        \t\tfile.close()

        func before_all() -> void:
        \tvar file := FileAccess.open("res://preflight-side-effect.txt", FileAccess.WRITE)
        \tif file != null:
        \t\tfile.store_line("before_all")
        \t\tfile.close()
        """).strip()
    project = _prepare_project(
        tmp_path,
        godot_bin,
        {"test/integration_suite.gd": _suite_source(body=body)},
    )
    result_path = tmp_path / "preflight-no-side-effects.json"

    process = _run_preflight(
        project,
        godot_bin,
        _manifest(project),
        result_path,
    )

    assert process.returncode == 0, process.stdout + process.stderr
    assert not (project / "preflight-side-effect.txt").exists()


def test_preflight_resolves_use_parameters_declarations(godot_bin, tmp_path):
    """A use_parameters literal inside a test body records case metadata.

    The array form yields one unnamed value per case; the dictionary form
    uses the dictionary keys as parameter names and its values as the case
    values, matching the GUT legacy convention.
    """
    body = dedent("""
        func test_item() -> void:
        \tvar item = use_parameters(["alpha", "beta"])
        \tassert_eq(item, "alpha")

        func test_flag() -> void:
        \tvar flag = use_parameters({"on": true, "off": false})
        \tassert_true(flag is bool)
        """).strip()
    project = _prepare_project(
        tmp_path,
        godot_bin,
        {"test/integration_suite.gd": _suite_source(body=body)},
    )
    result_path = tmp_path / "preflight-use-parameters.json"

    process = _run_preflight(
        project,
        godot_bin,
        _manifest(project, tests=["test_item", "test_flag"]),
        result_path,
    )

    assert process.returncode == 0, process.stdout + process.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    tests = {test["name"]: test for test in payload["suites"][0]["tests"]}
    assert tests["test_item"]["parameters"] == {
        "names": ["value"],
        "values": [["alpha"], ["beta"]],
    }
    assert tests["test_flag"]["parameters"] == {
        "names": ["value"],
        "values": [["on"], ["off"]],
    }


@pytest.mark.parametrize(
    ("body", "expected_error"),
    [
        (
            dedent("""
                func test_item() -> void:
                \tvar first = use_parameters(["alpha"])
                \tvar second = use_parameters(["beta"])
                """).strip(),
            "exactly one use_parameters call",
        ),
        (
            dedent("""
                func before_all() -> void:
                \tparameterize(["value"], [[1]])

                func test_item(value: int) -> void:
                \tvar item = use_parameters(["alpha"])
                """).strip(),
            "cannot combine signature parameters with use_parameters",
        ),
        (
            dedent("""
                const LIMIT := 3

                func test_item() -> void:
                \tvar item = use_parameters([LIMIT])
                """).strip(),
            "must be literal values",
        ),
    ],
    ids=[
        "multiple-calls",
        "combine-signature",
        "unresolvable-expression",
    ],
)
def test_preflight_rejects_use_parameters_declarations(
    godot_bin, tmp_path, body, expected_error
):
    """Malformed use_parameters declarations produce exit-code-2 diagnostics."""
    project = _prepare_project(
        tmp_path,
        godot_bin,
        {"test/integration_suite.gd": _suite_source(body=body)},
    )
    result_path = tmp_path / "preflight-use-parameters-invalid.json"

    process = _run_preflight(
        project,
        godot_bin,
        _manifest(project, tests=["test_item"]),
        result_path,
    )

    assert process.returncode == 2, process.stdout + process.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["status"] == "error"
    assert payload["suites"] == []
    assert "res://test/integration_suite.gd" in payload["error"]
    assert expected_error in payload["error"]


def test_preflight_trims_case_selector_to_matching_value_set(
    godot_bin, tmp_path
):
    """A ``name[case]`` selector filters the declaration to the selected case.

    The manifest entry is rewritten to the owning method so the runner
    receives one case whose values are exactly the selected value set.
    """
    body = dedent("""
        func before_all() -> void:
        \tparameterize(["value", "label"], [[1, "admin"], [2, "user"]])

        func test_ranked(value: int, label: String) -> void:
        \tpass
        """).strip()
    project = _prepare_project(
        tmp_path,
        godot_bin,
        {"test/integration_suite.gd": _suite_source(body=body)},
    )
    result_path = tmp_path / "preflight-case-selector.json"

    process = _run_preflight(
        project,
        godot_bin,
        _manifest(project, tests=["test_ranked[1-admin]"]),
        result_path,
    )

    assert process.returncode == 0, process.stdout + process.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    tests = payload["suites"][0]["tests"]
    assert len(tests) == 1
    assert tests[0]["name"] == "test_ranked"
    assert tests[0]["parameters"] == {
        "names": ["value", "label"],
        "values": [[1, "admin"]],
    }


@pytest.mark.parametrize(
    ("selector", "expected_error"),
    [
        ("test_ranked[nobody]", "has no case '[nobody]'"),
        ("test_plain[admin]", "is not parameterized"),
    ],
    ids=["unknown-case", "non-parameterized"],
)
def test_preflight_rejects_invalid_case_selectors(
    godot_bin, tmp_path, selector, expected_error
):
    """Case selectors that address no case produce exit-code-2 diagnostics."""
    body = dedent("""
        func before_all() -> void:
        \tparameterize(["value", "label"], [[1, "admin"], [2, "user"]])

        func test_ranked(value: int, label: String) -> void:
        \tpass

        func test_plain() -> void:
        \tpass
        """).strip()
    project = _prepare_project(
        tmp_path,
        godot_bin,
        {"test/integration_suite.gd": _suite_source(body=body)},
    )
    result_path = tmp_path / "preflight-case-selector-invalid.json"

    process = _run_preflight(
        project,
        godot_bin,
        _manifest(project, tests=[selector]),
        result_path,
    )

    assert process.returncode == 2, process.stdout + process.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["status"] == "error"
    assert payload["suites"] == []
    assert "res://test/integration_suite.gd" in payload["error"]
    assert expected_error in payload["error"]


def test_preflight_resolves_parameterize_for_bridge_suites(godot_bin, tmp_path):
    """Bridge (GutTest) suites get the same parameterization resolution.

    The bridge shim inherits the native machinery, so preflight resolves a
    ``before_all`` declaration on a GutTest suite and attaches parameters
    metadata exactly as it does for GdToolsTest suites.
    """
    body = dedent("""
        func before_all() -> void:
        \tparameterize(["value", "label"], [[1, "admin"], [2, "user"]])

        func test_ranked(value: int, label: String) -> void:
        \tpass
        """).strip()
    bridge_source = (
        "extends GutTest\nclass_name BridgePreflightSuite\n\n" + body
    )
    project = _prepare_project(
        tmp_path,
        godot_bin,
        {"test/integration_suite.gd": bridge_source},
    )
    result_path = tmp_path / "preflight-bridge-parameterize.json"

    process = _run_preflight(
        project,
        godot_bin,
        _manifest(project, tests=["test_ranked"]),
        result_path,
    )

    assert process.returncode == 0, process.stdout + process.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    suite = payload["suites"][0]
    test = suite["tests"][0]
    assert test["parameters"] == {
        "names": ["value", "label"],
        "values": [[1, "admin"], [2, "user"]],
    }


def test_preflight_rejects_malformed_bridge_declarations(godot_bin, tmp_path):
    """Malformed bridge declarations inherit preflight validation (exit 2)."""
    body = dedent("""
        func before_all() -> void:
        \tparameterize(["value"], [[1, "admin"], [2, "user"]])

        func test_ranked(value: int) -> void:
        \tpass
        """).strip()
    bridge_source = "extends GutTest\nclass_name BridgeInvalidSuite\n\n" + body
    project = _prepare_project(
        tmp_path,
        godot_bin,
        {"test/integration_suite.gd": bridge_source},
    )
    result_path = tmp_path / "preflight-bridge-invalid.json"

    process = _run_preflight(
        project,
        godot_bin,
        _manifest(project, tests=["test_ranked"]),
        result_path,
    )

    assert process.returncode == 2, process.stdout + process.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["status"] == "error"
    assert payload["suites"] == []
    assert "res://test/integration_suite.gd" in payload["error"]
    assert "parameter set 0 has 2 value(s); expected 1" in payload["error"]


def test_preflight_ignores_api_mentions_in_string_literals(godot_bin, tmp_path):
    """Mentions of the parameterization APIs inside strings are not declarations.

    A before_all line like ``var hint := "call parameterize(names, values)``
    must not be mistaken for a live declaration, and a string in a test body
    mentioning ``use_parameters`` must not resolve as one either.
    """
    body = dedent("""
        func before_all() -> void:
        \tvar hint := "call parameterize(names, values) before writing tests."
        \tparameterize(["value"], [[1], [2]])

        func test_ranked(value: int) -> void:
        \tvar note := "the legacy form is use_parameters(values) in the body."
        \tassert_true(value > 0)
        """).strip()
    source = _suite_source(body=body)
    project = _prepare_project(
        tmp_path,
        godot_bin,
        {"test/integration_suite.gd": source},
    )
    result_path = tmp_path / "preflight-string-mentions.json"

    process = _run_preflight(
        project,
        godot_bin,
        _manifest(project, tests=["test_ranked"]),
        result_path,
    )

    assert process.returncode == 0, process.stdout + process.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["status"] == "ok"
    suite = payload["suites"][0]
    test = suite["tests"][0]
    assert test["parameters"] == {"names": ["value"], "values": [[1], [2]]}
