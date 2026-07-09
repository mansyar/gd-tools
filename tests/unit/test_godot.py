"""Unit tests for the Godot binary detection and invocation module.

Covers GodotInfo dataclass, binary resolution chain, version
detection/validation, GUT version mapping, and the subprocess wrapper.
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gd_tools.config import GodotConfig
from gd_tools.errors import ConfigError, GodotNotFoundError
from gd_tools.godot import (
    GUT_VERSION_MAP,
    GodotInfo,
    check_version_compatible,
    find_godot,
    get_godot_version,
    get_gut_version_for_godot,
    run_godot,
)

# --- GodotInfo dataclass ---


@pytest.mark.unit
def test_godot_info_construction_valid():
    """Test GodotInfo construction with valid path, version, is_valid."""
    info = GodotInfo(path="/usr/bin/godot", version="4.5.1", is_valid=True)
    assert info.path == "/usr/bin/godot"
    assert info.version == "4.5.1"
    assert info.is_valid is True


@pytest.mark.unit
def test_godot_info_construction_unknown_version():
    """Test GodotInfo with version='unknown' and is_valid=False."""
    info = GodotInfo(path="/some/path", version="unknown", is_valid=False)
    assert info.path == "/some/path"
    assert info.version == "unknown"
    assert info.is_valid is False


# --- _check_config ---


@pytest.mark.unit
@patch("gd_tools.godot._is_executable", return_value=True)
def test_check_config_returns_path_when_set_and_exists(mock_exec):
    """Test _check_config returns path when binary is set and executable."""
    from gd_tools.godot import _check_config

    config = GodotConfig(binary="/usr/bin/godot")
    result = _check_config(config)
    assert result == "/usr/bin/godot"


@pytest.mark.unit
@patch("gd_tools.godot._is_executable", return_value=True)
def test_check_config_returns_none_when_not_set(mock_exec):
    """Test _check_config returns None when binary is None."""
    from gd_tools.godot import _check_config

    config = GodotConfig()
    result = _check_config(config)
    assert result is None


@pytest.mark.unit
@patch("gd_tools.godot._is_executable", return_value=False)
def test_check_config_returns_none_when_not_executable(mock_exec):
    """Test _check_config returns None when path doesn't exist."""
    from gd_tools.godot import _check_config

    config = GodotConfig(binary="/nonexistent/godot")
    result = _check_config(config)
    assert result is None


# --- _check_env_vars ---


@pytest.mark.unit
@patch("gd_tools.godot._is_executable", return_value=True)
def test_check_env_vars_godot_bin_first(mock_exec, monkeypatch):
    """Test GODOT_BIN is checked first and returned."""
    from gd_tools.godot import _check_env_vars

    monkeypatch.setenv("GODOT_BIN", "/custom/godot")
    monkeypatch.setenv("GODOT4_BIN", "/custom/godot4")
    monkeypatch.setenv("GODOT_PATH", "/custom/path")
    result = _check_env_vars()
    assert result == "/custom/godot"


@pytest.mark.unit
@patch("gd_tools.godot._is_executable", return_value=True)
def test_check_env_vars_godot4_bin_fallback(mock_exec, monkeypatch):
    """Test GODOT4_BIN is checked when GODOT_BIN not set."""
    from gd_tools.godot import _check_env_vars

    monkeypatch.delenv("GODOT_BIN", raising=False)
    monkeypatch.setenv("GODOT4_BIN", "/custom/godot4")
    monkeypatch.setenv("GODOT_PATH", "/custom/path")
    result = _check_env_vars()
    assert result == "/custom/godot4"


@pytest.mark.unit
@patch("gd_tools.godot._is_executable", return_value=True)
def test_check_env_vars_godot_path_last(mock_exec, monkeypatch):
    """Test GODOT_PATH is checked when first two not set."""
    from gd_tools.godot import _check_env_vars

    monkeypatch.delenv("GODOT_BIN", raising=False)
    monkeypatch.delenv("GODOT4_BIN", raising=False)
    monkeypatch.setenv("GODOT_PATH", "/custom/path")
    result = _check_env_vars()
    assert result == "/custom/path"


@pytest.mark.unit
@patch("gd_tools.godot._is_executable", return_value=True)
def test_check_env_vars_returns_none_when_unset(mock_exec, monkeypatch):
    """Test returns None when no env vars are set."""
    from gd_tools.godot import _check_env_vars

    monkeypatch.delenv("GODOT_BIN", raising=False)
    monkeypatch.delenv("GODOT4_BIN", raising=False)
    monkeypatch.delenv("GODOT_PATH", raising=False)
    result = _check_env_vars()
    assert result is None


@pytest.mark.unit
@patch("gd_tools.godot._is_executable", return_value=False)
def test_check_env_vars_returns_none_when_not_executable(
    mock_exec, monkeypatch
):
    """Test returns None when env var set but path not executable."""
    from gd_tools.godot import _check_env_vars

    monkeypatch.setenv("GODOT_BIN", "/bad/path")
    result = _check_env_vars()
    assert result is None


# --- _check_path ---


@pytest.mark.unit
@patch("gd_tools.godot.shutil.which")
def test_check_path_godot_first(mock_which):
    """Test shutil.which('godot') is checked first."""
    from gd_tools.godot import _check_path

    mock_which.return_value = "/usr/bin/godot"
    result = _check_path()
    assert result == "/usr/bin/godot"
    assert mock_which.call_count == 1


@pytest.mark.unit
@patch("gd_tools.godot.shutil.which")
def test_check_path_godot4_fallback(mock_which):
    """Test shutil.which('godot4') is checked as fallback."""
    from gd_tools.godot import _check_path

    mock_which.side_effect = [None, "/usr/bin/godot4"]
    result = _check_path()
    assert result == "/usr/bin/godot4"
    assert mock_which.call_count == 2


@pytest.mark.unit
@patch("gd_tools.godot.shutil.which", return_value=None)
def test_check_path_returns_none_when_not_found(mock_which):
    """Test returns None when neither godot nor godot4 found."""
    from gd_tools.godot import _check_path

    result = _check_path()
    assert result is None


# --- _check_common_locations ---


@pytest.mark.unit
@patch("gd_tools.godot._is_executable")
@patch("gd_tools.godot.sys")
def test_check_common_locations_windows(mock_sys, mock_exec):
    """Test Windows locations checked on win32 platform."""
    from gd_tools.godot import _check_common_locations

    mock_sys.platform = "win32"
    # Windows common locations - first path is executable
    mock_exec.side_effect = lambda p: p == r"C:\Program Files\Godot\godot.exe"
    result = _check_common_locations()
    assert result == r"C:\Program Files\Godot\godot.exe"


@pytest.mark.unit
@patch("gd_tools.godot._is_executable")
@patch("gd_tools.godot.sys")
def test_check_common_locations_macos(mock_sys, mock_exec):
    """Test macOS locations checked on darwin platform."""
    from gd_tools.godot import _check_common_locations

    mock_sys.platform = "darwin"
    mock_exec.side_effect = (
        lambda p: p == "/Applications/Godot.app/Contents/MacOS/Godot"
    )
    result = _check_common_locations()
    assert result == "/Applications/Godot.app/Contents/MacOS/Godot"


@pytest.mark.unit
@patch("gd_tools.godot._is_executable")
@patch("gd_tools.godot.sys")
def test_check_common_locations_linux(mock_sys, mock_exec):
    """Test Linux locations checked on linux platform."""
    from gd_tools.godot import _check_common_locations

    mock_sys.platform = "linux"
    mock_exec.side_effect = lambda p: p == "/usr/bin/godot"
    result = _check_common_locations()
    assert result == "/usr/bin/godot"


@pytest.mark.unit
@patch("gd_tools.godot._is_executable", return_value=False)
@patch("gd_tools.godot.sys")
def test_check_common_locations_returns_none(mock_sys, mock_exec):
    """Test returns None when no locations match."""
    from gd_tools.godot import _check_common_locations

    mock_sys.platform = "linux"
    result = _check_common_locations()
    assert result is None


# --- find_godot ---


@pytest.mark.unit
@patch("gd_tools.godot._check_common_locations", return_value=None)
@patch("gd_tools.godot._check_path", return_value=None)
@patch("gd_tools.godot._check_env_vars", return_value="/env/godot")
@patch("gd_tools.godot._check_config", return_value="/config/godot")
@patch("gd_tools.godot.check_version_compatible", return_value=True)
@patch("gd_tools.godot.get_godot_version", return_value="4.5.1")
def test_find_godot_config_takes_priority(
    mock_ver, mock_compat, mock_cfg, mock_env, mock_path, mock_common
):
    """Test config takes priority over env vars."""
    config = GodotConfig(binary="/config/godot")
    result = find_godot(config)
    assert result.path == "/config/godot"
    assert result.version == "4.5.1"
    assert result.is_valid is True
    mock_env.assert_not_called()


@pytest.mark.unit
@patch("gd_tools.godot._check_common_locations", return_value=None)
@patch("gd_tools.godot._check_path", return_value="/path/godot")
@patch("gd_tools.godot._check_env_vars", return_value="/env/godot")
@patch("gd_tools.godot._check_config", return_value=None)
@patch("gd_tools.godot.check_version_compatible", return_value=True)
@patch("gd_tools.godot.get_godot_version", return_value="4.5.1")
def test_find_godot_env_takes_priority_over_path(
    mock_ver, mock_compat, mock_cfg, mock_env, mock_path, mock_common
):
    """Test env vars take priority over PATH."""
    config = GodotConfig()
    result = find_godot(config)
    assert result.path == "/env/godot"
    mock_path.assert_not_called()


@pytest.mark.unit
@patch("gd_tools.godot._check_common_locations", return_value=None)
@patch("gd_tools.godot._check_path", return_value="/path/godot")
@patch("gd_tools.godot._check_env_vars", return_value=None)
@patch("gd_tools.godot._check_config", return_value=None)
@patch("gd_tools.godot.check_version_compatible", return_value=True)
@patch("gd_tools.godot.get_godot_version", return_value="4.5.1")
def test_find_godot_path_takes_priority_over_common(
    mock_ver, mock_compat, mock_cfg, mock_env, mock_path, mock_common
):
    """Test PATH takes priority over common locations."""
    config = GodotConfig()
    result = find_godot(config)
    assert result.path == "/path/godot"
    mock_common.assert_not_called()


@pytest.mark.unit
@patch("gd_tools.godot._check_common_locations", return_value=None)
@patch("gd_tools.godot._check_path", return_value=None)
@patch("gd_tools.godot._check_env_vars", return_value=None)
@patch("gd_tools.godot._check_config", return_value=None)
def test_find_godot_raises_when_not_found(
    mock_cfg, mock_env, mock_path, mock_common
):
    """Test GodotNotFoundError raised when nothing found."""
    config = GodotConfig()
    with pytest.raises(GodotNotFoundError) as exc_info:
        find_godot(config)
    assert "Godot binary not found" in str(exc_info.value)


@pytest.mark.unit
@patch("gd_tools.godot._check_common_locations", return_value=None)
@patch("gd_tools.godot._check_path", return_value=None)
@patch("gd_tools.godot._check_env_vars", return_value="/found/godot")
@patch("gd_tools.godot._check_config", return_value=None)
@patch("gd_tools.godot.check_version_compatible", return_value=True)
@patch("gd_tools.godot.get_godot_version", return_value="4.5.1")
def test_find_godot_returns_valid_info(
    mock_ver, mock_compat, mock_cfg, mock_env, mock_path, mock_common
):
    """Test find_godot returns GodotInfo with correct attributes."""
    config = GodotConfig()
    result = find_godot(config)
    assert isinstance(result, GodotInfo)
    assert result.path == "/found/godot"
    assert result.version == "4.5.1"
    assert result.is_valid is True


@pytest.mark.unit
@patch("gd_tools.godot._check_common_locations", return_value=None)
@patch("gd_tools.godot._check_path", return_value=None)
@patch("gd_tools.godot._check_env_vars", return_value="/found/godot")
@patch("gd_tools.godot._check_config", return_value=None)
@patch(
    "gd_tools.godot.get_godot_version", side_effect=GodotNotFoundError("fail")
)
def test_find_godot_version_detection_failure(
    mock_ver, mock_cfg, mock_env, mock_path, mock_common
):
    """Test find_godot handles version detection failure gracefully."""
    config = GodotConfig()
    result = find_godot(config)
    assert result.path == "/found/godot"
    assert result.version == "unknown"
    assert result.is_valid is False


@pytest.mark.unit
@patch("gd_tools.godot._check_common_locations", return_value=None)
@patch("gd_tools.godot._check_path", return_value=None)
@patch("gd_tools.godot._check_env_vars", return_value=None)
@patch("gd_tools.godot._check_config", return_value=None)
@patch("gd_tools.godot.sys")
def test_find_godot_not_found_message_macos(
    mock_sys, mock_cfg, mock_env, mock_path, mock_common
):
    """Test not-found error includes macOS install instructions."""
    mock_sys.platform = "darwin"
    config = GodotConfig()
    with pytest.raises(GodotNotFoundError) as exc_info:
        find_godot(config)
    msg = str(exc_info.value)
    assert "Godot binary not found" in msg
    assert "godotengine.org/download/macos" in msg
    assert "brew install --cask godot" in msg


@pytest.mark.unit
@patch("gd_tools.godot._check_common_locations", return_value=None)
@patch("gd_tools.godot._check_path", return_value=None)
@patch("gd_tools.godot._check_env_vars", return_value=None)
@patch("gd_tools.godot._check_config", return_value=None)
@patch("gd_tools.godot.sys")
def test_find_godot_not_found_message_linux(
    mock_sys, mock_cfg, mock_env, mock_path, mock_common
):
    """Test not-found error includes Linux install instructions."""
    mock_sys.platform = "linux"
    config = GodotConfig()
    with pytest.raises(GodotNotFoundError) as exc_info:
        find_godot(config)
    msg = str(exc_info.value)
    assert "Godot binary not found" in msg
    assert "godotengine.org/download/linux" in msg
    assert "flatpak install org.godotengine.Godot" in msg


# --- get_godot_version ---


@pytest.mark.unit
@patch("gd_tools.godot.subprocess.run")
def test_get_godot_version_stable(mock_run):
    """Test parsing a stable version like 4.5.1-stable."""
    mock_run.return_value = MagicMock(stdout="4.5.1-stable\n", returncode=0)
    assert get_godot_version("/usr/bin/godot") == "4.5.1"


@pytest.mark.unit
@patch("gd_tools.godot.subprocess.run")
def test_get_godot_version_dev(mock_run):
    """Test parsing a dev version like 4.6-dev."""
    mock_run.return_value = MagicMock(stdout="4.6-dev\n", returncode=0)
    assert get_godot_version("/usr/bin/godot") == "4.6.0"


@pytest.mark.unit
@patch("gd_tools.godot.subprocess.run")
def test_get_godot_version_no_patch(mock_run):
    """Test parsing a version without patch like 4.7."""
    mock_run.return_value = MagicMock(stdout="4.7\n", returncode=0)
    assert get_godot_version("/usr/bin/godot") == "4.7.0"


@pytest.mark.unit
@patch("gd_tools.godot.subprocess.run")
def test_get_godot_version_stable_suffix(mock_run):
    """Test parsing a version with stable.suffix like 4.5.stable.linux."""
    mock_run.return_value = MagicMock(stdout="4.5.stable.linux\n", returncode=0)
    assert get_godot_version("/usr/bin/godot") == "4.5.0"


@pytest.mark.unit
@patch("gd_tools.godot.subprocess.run")
def test_get_godot_version_failure_raises(mock_run):
    """Test GodotNotFoundError raised on subprocess failure."""
    mock_run.return_value = MagicMock(
        stdout="", stderr="not found", returncode=1
    )
    with pytest.raises(GodotNotFoundError):
        get_godot_version("/usr/bin/godot")


@pytest.mark.unit
@patch("gd_tools.godot.subprocess.run")
def test_get_godot_version_unparseable_output_raises(mock_run):
    """Test GodotNotFoundError raised on unparseable version output."""
    mock_run.return_value = MagicMock(
        stdout="not-a-version\n", stderr="", returncode=0
    )
    with pytest.raises(GodotNotFoundError):
        get_godot_version("/usr/bin/godot")


@pytest.mark.unit
@patch("gd_tools.godot.subprocess.run", side_effect=OSError("not found"))
def test_get_godot_version_oserror_raises(mock_run):
    """Test GodotNotFoundError raised when binary fails to run."""
    with pytest.raises(GodotNotFoundError):
        get_godot_version("/usr/bin/godot")


# --- check_version_compatible ---


@pytest.mark.unit
@pytest.mark.parametrize(
    "version,expected",
    [
        ("4.5.0", True),
        ("4.5.1", True),
        ("4.6.0", True),
        ("4.7.0", True),
        ("4.4.9", False),
        ("3.5.0", False),
        ("5.0.0", True),
        ("invalid", False),
        ("4.5", False),
    ],
)
def test_check_version_compatible(version, expected):
    """Test version compatibility check against 4.5.0 threshold."""
    assert check_version_compatible(version) is expected


# --- GUT_VERSION_MAP and get_gut_version_for_godot ---


@pytest.mark.unit
def test_gut_version_map_contents():
    """Test GUT_VERSION_MAP has correct Godot-to-GUT version mappings."""
    assert GUT_VERSION_MAP == {
        "4.5": "9.5.0",
        "4.6": "9.6.0",
        "4.7": "9.7.0",
    }


@pytest.mark.unit
@pytest.mark.parametrize(
    "godot_version,expected_gut",
    [
        ("4.5.1", "9.5.0"),
        ("4.6.0", "9.6.0"),
        ("4.7.0", "9.7.0"),
    ],
)
def test_get_gut_version_for_godot(godot_version, expected_gut):
    """Test GUT version mapping uses major.minor prefix."""
    assert get_gut_version_for_godot(godot_version) == expected_gut


@pytest.mark.unit
def test_get_gut_version_for_godot_unmapped_raises():
    """Test ConfigError raised for unmapped Godot version."""
    with pytest.raises(ConfigError):
        get_gut_version_for_godot("4.4.0")


@pytest.mark.unit
def test_get_gut_version_for_godot_malformed_raises():
    """Test ConfigError raised for malformed Godot version."""
    with pytest.raises(ConfigError):
        get_gut_version_for_godot("4")


# --- run_godot ---


@pytest.mark.unit
def test_run_godot_passes_path_and_args():
    """Test run_godot passes --path and args correctly to subprocess.run."""
    mock_result = MagicMock(spec=subprocess.CompletedProcess)
    with patch(
        "gd_tools.godot.subprocess.run", return_value=mock_result
    ) as mock_run:
        run_godot(
            binary="/usr/bin/godot",
            project_path=Path("/project"),
            args=["--headless", "--script", "test.gd"],
        )
    mock_run.assert_called_once()
    cmd = mock_run.call_args.args[0]
    assert cmd[0] == "/usr/bin/godot"
    assert cmd[1] == "--path"
    assert cmd[2] == str(Path("/project"))
    assert cmd[3:] == ["--headless", "--script", "test.gd"]


@pytest.mark.unit
def test_run_godot_merges_env_caller_precedence():
    """Test run_godot merges env with os.environ, caller values take precedence."""
    with patch.dict(
        "os.environ", {"EXISTING_VAR": "original", "OTHER_VAR": "keep"}
    ):
        with patch(
            "gd_tools.godot.subprocess.run", return_value=MagicMock()
        ) as mock_run:
            run_godot(
                binary="/usr/bin/godot",
                project_path=Path("/project"),
                args=[],
                env={"EXISTING_VAR": "overridden", "NEW_VAR": "added"},
            )
    call_env = mock_run.call_args.kwargs["env"]
    assert call_env["EXISTING_VAR"] == "overridden"
    assert call_env["OTHER_VAR"] == "keep"
    assert call_env["NEW_VAR"] == "added"


@pytest.mark.unit
def test_run_godot_uses_capture_output_and_text():
    """Test run_godot uses capture_output=True and text=True."""
    with patch(
        "gd_tools.godot.subprocess.run", return_value=MagicMock()
    ) as mock_run:
        run_godot(
            binary="/usr/bin/godot",
            project_path=Path("/project"),
            args=[],
        )
    assert mock_run.call_args.kwargs["capture_output"] is True
    assert mock_run.call_args.kwargs["text"] is True


@pytest.mark.unit
def test_run_godot_raises_timeout_expired():
    """Test run_godot raises subprocess.TimeoutExpired when timeout exceeded."""
    with patch(
        "gd_tools.godot.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd=["godot"], timeout=10),
    ):
        with pytest.raises(subprocess.TimeoutExpired):
            run_godot(
                binary="/usr/bin/godot",
                project_path=Path("/project"),
                args=[],
                timeout=10,
            )


@pytest.mark.unit
def test_run_godot_returns_completed_process():
    """Test run_godot returns subprocess.CompletedProcess."""
    expected = subprocess.CompletedProcess(
        args=["godot", "--path", "/project"],
        returncode=0,
        stdout="OK",
        stderr="",
    )
    with patch("gd_tools.godot.subprocess.run", return_value=expected):
        result = run_godot(
            binary="/usr/bin/godot",
            project_path=Path("/project"),
            args=[],
        )
    assert result is expected
