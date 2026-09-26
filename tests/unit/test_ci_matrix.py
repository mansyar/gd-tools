"""Unit tests for the CI workflow's Godot compatibility matrix.

The Godot-dependent stages run across a version x OS matrix so that the
support claim in ``product.md`` (Godot 4.5+ on Windows, macOS and Linux)
is backed by an actually-verified one. Nothing in the product code
enforces that matrix, so these tests pin its shape: a matrix silently
collapsing back to a single version, or a hardcoded POSIX ``GODOT_BIN``
reappearing, would otherwise only be noticed by a user on an
unexercised platform.

``workflow.md`` does not require tests for configuration files. This file
is the deliberate exception: the matrix is a claim about platform support
that fails silently, and a handful of assertions is cheaper than
discovering it from a bug report.
"""

import re
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

CI_PATH = (
    Path(__file__).parent.parent.parent / ".github" / "workflows" / "ci.yml"
)
ACTION_PATH = (
    Path(__file__).parent.parent.parent
    / ".github"
    / "actions"
    / "install-godot"
    / "action.yml"
)

GODOT_STAGES = ["integration", "e2e"]
EXPECTED_VERSIONS = ["4.5.2", "4.6.1", "4.7.1"]
EXPECTED_OSES = ["ubuntu-latest", "windows-latest"]


@pytest.fixture(scope="module")
def ci() -> dict:
    """Parsed ``ci.yml``."""
    return yaml.safe_load(CI_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def godot_jobs(ci: dict) -> dict:
    """The Godot-dependent jobs, keyed by job name."""
    jobs = ci["jobs"]
    return {name: jobs[name] for name in GODOT_STAGES if name in jobs}


# --- Matrix shape ---


@pytest.mark.parametrize("stage", GODOT_STAGES)
def test_each_godot_stage_has_a_version_axis(godot_jobs: dict, stage: str):
    """Every Godot stage pins an explicit, current set of Godot versions."""
    matrix = godot_jobs[stage]["strategy"]["matrix"]
    assert matrix["godot-version"] == EXPECTED_VERSIONS


@pytest.mark.parametrize("stage", GODOT_STAGES)
def test_each_godot_stage_has_an_os_axis(godot_jobs: dict, stage: str):
    """Every Godot stage runs on Linux and Windows."""
    matrix = godot_jobs[stage]["strategy"]["matrix"]
    assert matrix["os"] == EXPECTED_OSES


@pytest.mark.parametrize("stage", GODOT_STAGES)
def test_each_godot_stage_runs_on_the_matrix_os(godot_jobs: dict, stage: str):
    """``runs-on`` must follow the OS axis, not stay pinned to one runner."""
    assert godot_jobs[stage]["runs-on"] == "${{ matrix.os }}"


@pytest.mark.parametrize("stage", GODOT_STAGES)
def test_each_godot_stage_expands_to_six_jobs(godot_jobs: dict, stage: str):
    """3 versions x 2 OSes = 6 jobs per stage, 12 across the two stages."""
    matrix = godot_jobs[stage]["strategy"]["matrix"]
    assert len(matrix["godot-version"]) * len(matrix["os"]) == 6


@pytest.mark.parametrize("stage", GODOT_STAGES)
def test_axes_are_separate_so_a_failure_names_both_dimensions(
    godot_jobs: dict, stage: str
):
    """Combined axis strings would hide which combination failed.

    A single ``include``-style combined string renders as one opaque job
    name, whereas separate axes give GitHub a readable grid.
    """
    matrix = godot_jobs[stage]["strategy"]["matrix"]
    assert "godot-version" in matrix and "os" in matrix
    assert "include" not in matrix


# --- R4: matrix hygiene ---


@pytest.mark.parametrize("stage", GODOT_STAGES)
def test_fail_fast_is_disabled(godot_jobs: dict, stage: str):
    """One failing cell must not cancel the other five."""
    assert godot_jobs[stage]["strategy"]["fail-fast"] is False


@pytest.mark.parametrize("stage", GODOT_STAGES)
def test_no_cell_continues_on_error(godot_jobs: dict, stage: str):
    """Every cell is blocking; a non-blocking axis must be a tracked decision."""
    assert "continue-on-error" not in godot_jobs[stage]


@pytest.mark.parametrize("stage", GODOT_STAGES)
def test_artifact_names_are_unique_per_cell(godot_jobs: dict, stage: str):
    """``upload-artifact@v4`` errors on duplicate names within a run.

    A fixed artifact name would hard-fail all six cells rather than
    silently overwrite, so the matrix values must be in the name.
    """
    steps = godot_jobs[stage]["steps"]
    upload = next(
        s
        for s in steps
        if str(s.get("uses", "")).startswith("actions/upload-artifact")
    )
    name = upload["with"]["name"]
    assert "matrix.godot-version" in name
    assert "matrix.os" in name


@pytest.mark.parametrize("stage", GODOT_STAGES)
def test_godot_stages_stay_off_the_python_axis(godot_jobs: dict, stage: str):
    """A single Python version only; adding the axis would mean 36 jobs."""
    steps = godot_jobs[stage]["steps"]
    setup = next(
        s
        for s in steps
        if str(s.get("uses", "")).startswith("actions/setup-python")
    )
    version = setup["with"]["python-version"]
    assert isinstance(
        version, str
    ), "python-version must be a scalar, not a matrix axis"


# --- R2: no hardcoded POSIX binary path ---


def test_no_hardcoded_posix_godot_path_remains():
    """``GODOT_BIN`` must not be a fixed POSIX path anywhere in the workflow.

    A hardcoded ``/usr/local/bin/godot`` cannot exist on a Windows runner,
    and the suite would then skip or fail for the wrong reason.
    """
    text = CI_PATH.read_text(encoding="utf-8")
    assert "/usr/local/bin/godot" not in text


def test_godot_version_is_not_pinned_by_a_global_env_var(ci: dict):
    """The version axis owns the Godot version; a global would override it."""
    assert "GODOT_VERSION" not in ci.get("env", {})


def test_ci_env_var_is_still_exported(ci: dict):
    """``CI=true`` is what makes ``require_godot_binary`` fail rather than skip."""
    assert ci["env"]["CI"] == "true"


# --- R1: the shared install step ---


@pytest.mark.parametrize("stage", GODOT_STAGES)
def test_both_stages_use_the_shared_install_action(
    godot_jobs: dict, stage: str
):
    """One shared action, so the two stages cannot drift apart."""
    steps = godot_jobs[stage]["steps"]
    uses = [
        s for s in steps if s.get("uses", "").startswith("./.github/actions/")
    ]
    assert len(uses) == 1
    assert uses[0]["uses"] == "./.github/actions/install-godot"
    assert uses[0]["with"]["version"] == "${{ matrix.godot-version }}"


def test_install_action_is_a_composite_action():
    """A composite action is what lets one script serve both platforms."""
    action = yaml.safe_load(ACTION_PATH.read_text(encoding="utf-8"))
    assert action["runs"]["using"] == "composite"


def test_install_action_selects_the_asset_per_platform():
    """Linux and Windows ship different asset names; the step must branch."""
    text = ACTION_PATH.read_text(encoding="utf-8")
    assert "_linux.x86_64.zip" in text
    assert "_win64.exe.zip" in text


def test_install_action_exports_godot_bin_for_native_python():
    """Git Bash reports ``/d/a/...``; native Windows Python cannot open it.

    ``cygpath -w`` is what makes ``GODOT_BIN`` resolvable by the Windows
    Python that pytest runs under.
    """
    text = ACTION_PATH.read_text(encoding="utf-8")
    assert "cygpath -w" in text
    assert "GODOT_BIN=" in text and "$GITHUB_ENV" in text


def test_install_action_verifies_the_binary_runs():
    """Criterion 11: every job must prove Godot actually executes."""
    text = ACTION_PATH.read_text(encoding="utf-8")
    assert re.search(r"godot --version", text)


def test_install_action_uses_unguarded_curl():
    """A silent 404 must fail the job, not install nothing.

    ``curl -f`` is what turns a 404 into a non-zero exit. Without it the
    pipeline continues and every test skips.
    """
    text = ACTION_PATH.read_text(encoding="utf-8")
    assert re.search(r"curl\s+-[a-zA-Z]*f", text)


def _executed_scripts() -> str:
    """The shell scripts the install action actually runs, comments removed.

    Prose in the action is allowed to *mention* ``sudo`` while explaining
    why it is gone; what matters is that no executed line uses it.
    """
    action = yaml.safe_load(ACTION_PATH.read_text(encoding="utf-8"))
    lines: list[str] = []
    for step in action["runs"]["steps"]:
        for raw in str(step.get("run", "")).splitlines():
            stripped = raw.strip()
            if stripped and not stripped.startswith("#"):
                lines.append(stripped)
    return "\n".join(lines)


def test_no_bash_only_construct_runs_on_windows():
    """``sudo``/``wget`` must not be executed anywhere in the shared step.

    The old per-stage install used ``wget`` and ``sudo mv`` directly, which
    is exactly why the Windows cells could never run.
    """
    scripts = _executed_scripts()
    for construct in ("sudo", "wget"):
        assert not re.search(
            rf"\b{construct}\b", scripts
        ), f"{construct!r} has no Windows equivalent and must not execute"


def test_chmod_only_runs_in_the_non_windows_branch():
    """``chmod`` is fine, but only after the Windows case has branched away."""
    scripts = _executed_scripts()
    windows_branch = scripts.index('= "Windows"')
    linux_branch = scripts.index("else", windows_branch)
    assert linux_branch < scripts.index(
        "chmod"
    ), "chmod must sit inside the non-Windows branch"


def test_curl_fails_loudly_on_a_missing_asset():
    """A 404 must abort the job, not install nothing and skip every test."""
    assert re.search(r"curl\s+-\S*f", _executed_scripts())
