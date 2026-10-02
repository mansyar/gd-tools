"""Core implementation for the ``gd-tools install-hooks`` command.

Wires gd-tools into the `pre-commit <https://pre-commit.com>`_ framework
by generating two files in the project root:

- ``.pre-commit-hooks.yaml`` — hook metadata describing the gd-tools
  hooks (the machine-readable contract for the framework).
- ``.pre-commit-config.yaml`` — a ``repos: local:`` entry block with the
  selected hooks, merged into any existing configuration.

The command is idempotent: re-runs match previously-added gd-tools
entries by hook id and update them in place, add missing entries, and
never touch foreign (non-gd-tools) hooks or keys.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from .errors import GdToolsError

# Statuses for a single hook within an InstallResult.
STATUS_ADDED = "added"
STATUS_UPDATED = "updated"

# Aggregate statuses for an install run.
STATUS_INSTALLED = "installed"
STATUS_NOTHING_TO_DO = "nothing-to-do"

# Canonical hook order and ids.
HOOK_IDS: dict[str, str] = {
    "format": "gd-tools-format",
    "lint": "gd-tools-lint",
    "test": "gd-tools-test",
}

# Only GDScript files are relevant for the format and lint hooks.
FILE_FILTER = r"\.gd$"

HOOKS_FILE_NAME = ".pre-commit-hooks.yaml"
CONFIG_FILE_NAME = ".pre-commit-config.yaml"


def _hook_definition(name: str) -> dict:
    """Return the pre-commit hook definition for a feature name.

    Args:
        name: One of ``format``, ``lint``, or ``test``.

    Returns:
        The hook definition dict.

    Raises:
        GdToolsError: If ``name`` is not a known hook (exit 2).
    """
    if name == "format":
        return {
            "id": HOOK_IDS["format"],
            "name": "gd-tools format --check",
            "entry": "gd-tools format --check",
            "language": "system",
            "files": FILE_FILTER,
        }
    if name == "lint":
        return {
            "id": HOOK_IDS["lint"],
            "name": "gd-tools lint",
            "entry": "gd-tools lint",
            "language": "system",
            "files": FILE_FILTER,
        }
    if name == "test":
        return {
            "id": HOOK_IDS["test"],
            "name": "gd-tools test",
            "entry": "gd-tools test",
            "language": "system",
            "pass_filenames": False,
        }
    raise GdToolsError(
        f"Unknown hook {name!r}; expected one of: " f"{', '.join(HOOK_IDS)}",
    )


@dataclass(frozen=True)
class HookResult:
    """Outcome for a single selected hook.

    Attributes:
        name: Feature name (``format``, ``lint``, ``test``).
        id: The pre-commit hook id (``gd-tools-format`` ...).
        status: ``STATUS_ADDED`` or ``STATUS_UPDATED``.
    """

    name: str
    id: str
    status: str


@dataclass(frozen=True)
class InstallResult:
    """Aggregate outcome of an install-hooks run.

    Attributes:
        hooks_file: Path of the generated ``.pre-commit-hooks.yaml``.
        config_file: Path of the written/merged
            ``.pre-commit-config.yaml``.
        hooks: Per-hook outcomes in selection order.
        deselected_present: Feature names of gd-tools hooks found in the
            existing config but not part of the new selection. They are
            reported and left intact.
        status: ``STATUS_INSTALLED`` or ``STATUS_NOTHING_TO_DO``.
    """

    hooks_file: Path
    config_file: Path
    hooks: tuple[HookResult, ...]
    deselected_present: tuple[str, ...]
    status: str


def _write_hooks_file(project_root: Path, selection: tuple[str, ...]) -> Path:
    """Generate ``.pre-commit-hooks.yaml`` for the selected hooks.

    Args:
        project_root: The project directory.
        selection: Selected feature names in canonical order.

    Returns:
        The path of the written file.
    """
    data = [_hook_definition(name) for name in selection]
    content = yaml.safe_dump(data, sort_keys=False, default_flow_style=False)
    path = project_root / HOOKS_FILE_NAME
    path.write_text(content, encoding="utf-8")
    return path


def _load_config_data(config_path: Path) -> dict:
    """Load an existing pre-commit config, or a fresh skeleton.

    Args:
        config_path: Path of ``.pre-commit-config.yaml``.

    Returns:
        The parsed mapping (``{"repos": [...]}``).

    Raises:
        GdToolsError: If the file exists but is malformed YAML
            (exit 2).
    """
    if not config_path.exists():
        return {"repos": []}
    try:
        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise GdToolsError(
            f"Malformed {CONFIG_FILE_NAME}: {exc}",
        ) from exc
    if not isinstance(data, dict):
        data = {}
    if not isinstance(data.get("repos"), list):
        data["repos"] = []
    return data


def _merge_config(
    project_root: Path, selection: tuple[str, ...]
) -> tuple[Path, tuple[HookResult, ...], tuple[str, ...]]:
    """Merge the selected gd-tools hooks into the pre-commit config.

    Existing gd-tools entries are matched by hook id and updated in
    place; missing entries are appended to the ``repo: local`` block.
    Foreign hooks are never modified. gd-tools hooks present in the
    config but not selected are reported via the return value and left
    intact.

    Args:
        project_root: The project directory.
        selection: Selected feature names.

    Returns:
        Tuple of (config path, per-hook results, deselected-but-present
        feature names).
    """
    config_path = project_root / CONFIG_FILE_NAME
    data = _load_config_data(config_path)
    repos = data["repos"]

    local: dict = next(
        (
            repo
            for repo in repos
            if isinstance(repo, dict) and repo.get("repo") == "local"
        ),
        None,
    )
    if local is None:
        local = {"repo": "local", "hooks": []}
        repos.append(local)
    if not isinstance(local.get("hooks"), list):
        local["hooks"] = []

    results: list[HookResult] = []
    for name in selection:
        definition = _hook_definition(name)
        hook_id = definition["id"]
        existing = next(
            (
                hook
                for hook in local["hooks"]
                if isinstance(hook, dict) and hook.get("id") == hook_id
            ),
            None,
        )
        if existing is None:
            local["hooks"].append(dict(definition))
            status = STATUS_ADDED
        else:
            existing.update(definition)
            status = STATUS_UPDATED
        results.append(HookResult(name=name, id=hook_id, status=status))

    selected_ids = {HOOK_IDS[name] for name in selection}
    deselected = tuple(
        name
        for name, hook_id in HOOK_IDS.items()
        if hook_id not in selected_ids
        and any(
            isinstance(hook, dict) and hook.get("id") == hook_id
            for hook in local["hooks"]
        )
    )

    content = yaml.safe_dump(data, sort_keys=False, default_flow_style=False)
    config_path.write_text(content, encoding="utf-8")
    return config_path, tuple(results), deselected


def install_hooks(
    selection: tuple[str, ...],
    project_root: Path | None = None,
) -> InstallResult:
    """Install (or update) gd-tools pre-commit hooks for a project.

    Args:
        selection: Feature names to enable (``format``, ``lint``,
            ``test``). An empty selection performs no writes.
        project_root: The project directory. Defaults to the current
            working directory.

    Returns:
        An :class:`InstallResult` describing the outcome.

    Raises:
        GdToolsError: For unknown hook names or malformed existing
            config (exit 2).
    """
    root = project_root if project_root is not None else Path.cwd()
    hooks_file = root / HOOKS_FILE_NAME
    config_file = root / CONFIG_FILE_NAME

    if not selection:
        return InstallResult(
            hooks_file=hooks_file,
            config_file=config_file,
            hooks=(),
            deselected_present=(),
            status=STATUS_NOTHING_TO_DO,
        )

    _write_hooks_file(root, selection)
    config_file, results, deselected = _merge_config(root, selection)
    return InstallResult(
        hooks_file=hooks_file,
        config_file=config_file,
        hooks=results,
        deselected_present=deselected,
        status=STATUS_INSTALLED,
    )
