"""Coverage plan generator module.

Parses GDScript source files using gdtoolkit's Lark parser, walks
the resulting AST to identify trackable statements and branch points,
and emits an instrumentation plan JSON file.

The generated plan is consumed by the GDScript runtime tracker
(Track 10) and pre/post-run hooks (Track 11) for code coverage
instrumentation.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path, PurePath

from gdtoolkit.parser import parser as gd_parser
from lark import Tree
from lark.visitors import Visitor

from gd_tools.errors import CoveragePlanError
from gd_tools.file_discovery import discover_gd_files

# --- Data structures (FR-1) ---


@dataclass
class LinePlan:
    """A single trackable point in a GDScript file.

    Attributes:
        line: 1-indexed line number in the source file.
        id: Unique identifier within the file (sequential 0-indexed).
        type: Either "statement" or "branch".
        branch_type: Branch type string if type is "branch", else None.
    """

    line: int
    id: int
    type: str
    branch_type: str | None = None


@dataclass
class FilePlan:
    """Per-file entry in a coverage plan.

    Attributes:
        file_id: Sequential 0-indexed file identifier.
        path: Godot resource path with ``res://`` prefix.
        source_hash: SHA-256 hash prefixed with ``sha256:``.
        lines: List of trackable points in this file.
    """

    file_id: int
    path: str
    source_hash: str
    lines: list[LinePlan] = field(default_factory=list)


@dataclass
class CoveragePlan:
    """Top-level container for a coverage plan.

    Attributes:
        version: Schema version (currently 1).
        generated_by: Name of the tool that generated this plan.
        files: List of per-file plans.
    """

    version: int
    generated_by: str
    files: list[FilePlan] = field(default_factory=list)


# --- JSON I/O (FR-5) ---


def write_plan_json(plan: CoveragePlan, output_path: str) -> None:
    """Serialize a :class:`CoveragePlan` to a JSON file.

    Args:
        plan: The coverage plan to serialize.
        output_path: Path to the output JSON file.
    """
    data = {
        "version": plan.version,
        "generated_by": plan.generated_by,
        "files": [
            {
                "file_id": fp.file_id,
                "path": fp.path,
                "source_hash": fp.source_hash,
                "lines": [
                    {
                        "line": lp.line,
                        "id": lp.id,
                        "type": lp.type,
                        "branch_type": lp.branch_type,
                    }
                    for lp in fp.lines
                ],
            }
            for fp in plan.files
        ],
    }
    Path(output_path).write_text(json.dumps(data, indent=2), encoding="utf-8")


def read_plan_json(path: str) -> CoveragePlan:
    """Deserialize a JSON file to a :class:`CoveragePlan` object.

    Args:
        path: Path to the JSON plan file.

    Returns:
        The deserialized :class:`CoveragePlan`.

    Raises:
        CoveragePlanError: If the file is missing, contains invalid
            JSON, or has a schema mismatch.
    """
    plan_path = Path(path)
    if not plan_path.exists():
        raise CoveragePlanError(f"Plan file not found: {path}")

    try:
        data = json.loads(plan_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CoveragePlanError(f"Invalid JSON in plan file: {exc}") from exc

    if not isinstance(data, dict):
        raise CoveragePlanError("Plan JSON must be a JSON object")

    version = data.get("version")
    if version != 1:
        raise CoveragePlanError(
            f"Unsupported plan version: {version} (expected 1)"
        )

    if "generated_by" not in data:
        raise CoveragePlanError("Missing required field: generated_by")

    if "files" not in data:
        raise CoveragePlanError("Missing required field: files")

    files: list[FilePlan] = []
    for fdata in data["files"]:
        lines = [
            LinePlan(
                line=lp["line"],
                id=lp["id"],
                type=lp["type"],
                branch_type=lp.get("branch_type"),
            )
            for lp in fdata.get("lines", [])
        ]
        files.append(
            FilePlan(
                file_id=fdata["file_id"],
                path=fdata["path"],
                source_hash=fdata["source_hash"],
                lines=lines,
            )
        )

    return CoveragePlan(
        version=data["version"],
        generated_by=data["generated_by"],
        files=files,
    )


# --- AST Parsing (FR-3) ---


def parse_gdscript(source: str) -> Tree:
    """Parse GDScript source and return a Lark AST tree with metadata.

    Args:
        source: Raw GDScript source code.

    Returns:
        A Lark :class:`~lark.Tree` with line metadata enabled.
    """
    return gd_parser.parse(source, gather_metadata=True)


# --- Coverage Visitor (FR-2, FR-3) ---


class CoverageVisitor(Visitor):
    """Lark AST visitor that identifies trackable statements and branches.

    Walks the parsed GDScript AST and collects :class:`LinePlan` entries
    for each trackable statement and branch point.

    Attributes:
        points: List of collected trackable points.
    """

    def __init__(self) -> None:
        self.points: list[LinePlan] = []
        self._next_id: int = 0

    def _add_point(
        self,
        tree: Tree,
        point_type: str,
        branch_type: str | None = None,
    ) -> None:
        """Extract line number and append a new :class:`LinePlan`.

        Args:
            tree: The AST node being tracked.
            point_type: Either "statement" or "branch".
            branch_type: Branch type string if ``point_type`` is
                "branch", otherwise ``None``.
        """
        self.points.append(
            LinePlan(
                line=tree.meta.line,
                id=self._next_id,
                type=point_type,
                branch_type=branch_type,
            )
        )
        self._next_id += 1

    # --- Statement methods ---

    def expr_stmt(self, tree: Tree) -> None:
        """Track expression statements."""
        self._add_point(tree, "statement")

    def return_stmt(self, tree: Tree) -> None:
        """Track return statements."""
        self._add_point(tree, "statement")

    def func_var_assigned(self, tree: Tree) -> None:
        """Track inferred-type variable assignments in functions."""
        self._add_point(tree, "statement")

    def func_var_typed_assgnd(self, tree: Tree) -> None:
        """Track typed variable assignments in functions."""
        self._add_point(tree, "statement")

    def func_var_inf(self, tree: Tree) -> None:
        """Track ``:=`` inferred-type variable assignments."""
        self._add_point(tree, "statement")

    def break_stmt(self, tree: Tree) -> None:
        """Track break statements."""
        self._add_point(tree, "statement")

    def continue_stmt(self, tree: Tree) -> None:
        """Track continue statements."""
        self._add_point(tree, "statement")

    # --- Branch methods ---

    def if_branch(self, tree: Tree) -> None:
        """Track if branch as ``if_true``."""
        self._add_point(tree, "branch", "if_true")

    def elif_branch(self, tree: Tree) -> None:
        """Track elif branch as ``elif_true``."""
        self._add_point(tree, "branch", "elif_true")

    def else_branch(self, tree: Tree) -> None:
        """Track else branch as ``if_false``."""
        self._add_point(tree, "branch", "if_false")

    def while_stmt(self, tree: Tree) -> None:
        """Track while loop body."""
        self._add_point(tree, "branch", "loop_body")

    def for_stmt(self, tree: Tree) -> None:
        """Track for loop body."""
        self._add_point(tree, "branch", "loop_body")

    def for_stmt_typed(self, tree: Tree) -> None:
        """Track typed for loop body."""
        self._add_point(tree, "branch", "loop_body")

    def match_branch(self, tree: Tree) -> None:
        """Track each match case as ``match_case``."""
        self._add_point(tree, "branch", "match_case")


# --- Plan Generation (FR-4, FR-6) ---


def generate_plan(
    project_root: str,
    source_dirs: list[str] | None = None,
    exclude_dirs: list[str] | None = None,
    test_dirs: list[str] | None = None,
) -> CoveragePlan:
    """Generate a coverage plan for a Godot project.

    Discovers all ``.gd`` files in ``project_root``, parses each one,
    runs :class:`CoverageVisitor` to identify trackable points, and
    assembles a :class:`CoveragePlan` with sequential ``file_id`` values.

    Args:
        project_root: Root directory of the Godot project.
        source_dirs: Optional list of source directories (unused,
            all discovered files are included).
        exclude_dirs: Directories to exclude from discovery.
            Defaults to :data:`~gd_tools.config.DEFAULT_EXCLUDES`.
        test_dirs: Directories whose files should be excluded from
            coverage targets. Defaults to ``["test", "tests"]``.

    Returns:
        A :class:`CoveragePlan` with one :class:`FilePlan` per
        discovered file.
    """
    if exclude_dirs is None:
        from gd_tools.config import DEFAULT_EXCLUDES

        exclude_dirs = DEFAULT_EXCLUDES.copy()

    if test_dirs is None:
        test_dirs = ["test", "tests"]

    gd_files = discover_gd_files(project_root, excludes=exclude_dirs)

    # Filter out files whose path contains a test directory component
    gd_files = [
        f
        for f in gd_files
        if not any(td in PurePath(f).parts for td in test_dirs)
    ]

    file_plans: list[FilePlan] = []
    for file_id, gd_file in enumerate(gd_files):
        source = Path(gd_file).read_text(encoding="utf-8")
        source_hash = (
            "sha256:" + hashlib.sha256(source.encode("utf-8")).hexdigest()
        )

        tree = parse_gdscript(source)
        visitor = CoverageVisitor()
        visitor.visit(tree)

        # Build res:// path
        rel_path = Path(gd_file).relative_to(project_root)
        res_path = "res://" + str(rel_path).replace("\\", "/")

        file_plans.append(
            FilePlan(
                file_id=file_id,
                path=res_path,
                source_hash=source_hash,
                lines=visitor.points,
            )
        )

    return CoveragePlan(
        version=1,
        generated_by="gd-tools",
        files=file_plans,
    )
