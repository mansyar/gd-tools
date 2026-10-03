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
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path, PurePath

from gdtoolkit.parser import parser as gd_parser
from lark import Tree
from lark.exceptions import LarkError
from lark.visitors import Visitor
from rich.console import Console

from gd_tools.atomic_io import atomic_write_text
from gd_tools.errors import CoveragePlanError
from gd_tools.file_discovery import discover_gd_files

PLAN_VERSION = 5
"""Current coverage plan JSON schema version.

Bumped 1 -> 2 when ``excluded_lines`` was introduced (Track 30) so
stale cached plans regenerate instead of silently dropping exclusions.

Bumped 2 -> 3 when ternary branch points became anchored to their
enclosing statement. Version 2 plans record ``LinePlan.line`` at a
ternary's first-operand line, so reusing one would re-inject trackers on
the stale lines and reproduce the parse failures this bump exists to
prevent.

Bumped 3 -> 4 when statement points on class-member declaration lines
and function signature lines were dropped, and 4 -> 5 when points on
bracket-continuation lines (inside open brackets, or after backslash
continuations) were dropped as well. Version 4 plans can carry such
points (a lambda body written inline squashes its statements onto the
continuation line), so reusing one would inject trackers where GDScript
permits no statement and break the instrumented file.
"""

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
        excluded_lines: Sorted 1-based line numbers excluded from
            instrumentation via ``# gd-tools: no cover`` annotations.
    """

    file_id: int
    path: str
    source_hash: str
    lines: list[LinePlan] = field(default_factory=list)
    excluded_lines: list[int] = field(default_factory=list)


@dataclass
class CoveragePlan:
    """Top-level container for a coverage plan.

    Attributes:
        version: Schema version (see :data:`PLAN_VERSION`).
        generated_by: Name of the tool that generated this plan.
        files: List of per-file plans.
    """

    version: int
    generated_by: str
    files: list[FilePlan] = field(default_factory=list)


@dataclass
class CacheStatus:
    """Outcome of a cached plan generation attempt.

    Attributes:
        hit: ``True`` if the cached plan was reused without regeneration.
        reason: Human-readable explanation of the cache outcome
            (e.g. ``"3 files unchanged"`` or ``"1 changed"``).
    """

    hit: bool
    reason: str


# --- JSON I/O (FR-5) ---


def write_plan_json(plan: CoveragePlan, output_path: str) -> None:
    """Serialize a :class:`CoveragePlan` to a JSON file.

    The write is crash-safe: the plan cache is read back on later runs,
    so a truncated file must never replace a good one. See
    :mod:`gd_tools.atomic_io`.

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
                "excluded_lines": fp.excluded_lines,
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
    atomic_write_text(output_path, json.dumps(data, indent=2))


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
    if version != PLAN_VERSION:
        raise CoveragePlanError(
            f"Unsupported plan version: {version} (expected {PLAN_VERSION}). "
            "Delete this plan file or re-run gd-tools to regenerate it."
        )

    if "generated_by" not in data:
        raise CoveragePlanError("Missing required field: generated_by")

    if "files" not in data:
        raise CoveragePlanError("Missing required field: files")

    files_data = data["files"]
    if not isinstance(files_data, list):
        raise CoveragePlanError("Plan 'files' field must be a list")

    files: list[FilePlan] = []
    for fdata in files_data:
        if not isinstance(fdata, dict):
            raise CoveragePlanError("Each file entry must be a JSON object")
        for required in ("file_id", "path", "source_hash"):
            if required not in fdata:
                raise CoveragePlanError(
                    f"Missing required field in file entry: {required}"
                )
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
                excluded_lines=fdata.get("excluded_lines", []),
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


# --- Exclusion annotations (Track 30) ---

ANNOTATION_TOKEN = "# gd-tools: no cover"

_ANNOTATION_RE = re.compile(r"^gd-tools:\s*no cover(?:\s+(start|end))?$")
_FUNC_DEF_RE = re.compile(r"^\s*(?:static\s+)?func\b")

Annotation = tuple[int, str | None]
"""A (1-based line number, "start" | "end" | None) pair."""


def _scan_annotations(source: str) -> list[Annotation]:
    """Scan source lines for ``# gd-tools: no cover`` comment annotations.

    Only real comments match: text inside single- or triple-quoted
    string literals is skipped by a lightweight per-line lexer.

    Args:
        source: Raw GDScript source code.

    Returns:
        Annotations in source order as ``(line, kind)`` pairs where
        ``kind`` is ``"start"``, ``"end"``, or ``None`` (line form).
    """
    annotations: list[Annotation] = []
    in_triple: str | None = None

    for lineno, raw in enumerate(source.splitlines(), 1):
        text = raw
        if in_triple is not None:
            end_idx = text.find(in_triple)
            if end_idx == -1:
                continue
            text = text[end_idx + len(in_triple) :]
            in_triple = None

        comment: str | None = None
        i = 0
        while i < len(text):
            ch = text[i]
            if text.startswith('"""', i) or text.startswith("'''", i):
                closer = text[i : i + 3]
                j = text.find(closer, i + 3)
                if j == -1:
                    in_triple = closer
                    break
                i = j + 3
                continue
            if ch in ('"', "'"):
                i += 1
                closed = False
                while i < len(text):
                    if text[i] == "\\":
                        i += 2
                        continue
                    if text[i] == ch:
                        i += 1
                        closed = True
                        break
                    i += 1
                if not closed:
                    break
                continue
            if ch == "#":
                comment = text[i + 1 :]
                break
            i += 1

        if comment is None:
            continue
        match = _ANNOTATION_RE.match(comment.strip())
        if match:
            annotations.append((lineno, match.group(1)))

    return annotations


def _func_span_end(lines: list[str], def_idx: int) -> int:
    """Return the last 1-based line of the function whose def is at ``def_idx``.

    A function body spans every subsequent non-blank line indented
    deeper than the ``func`` definition line. Blank lines do not
    extend the span.

    Args:
        lines: Source lines (0-indexed list).
        def_idx: 0-based index of the ``func`` definition line.

    Returns:
        The last body line as a 1-based line number (the def line
        itself when the body is empty).
    """
    def_indent = len(lines[def_idx]) - len(lines[def_idx].lstrip())
    end = def_idx
    for j in range(def_idx + 1, len(lines)):
        stripped = lines[j].strip()
        if not stripped:
            continue
        indent = len(lines[j]) - len(lines[j].lstrip())
        if indent <= def_indent:
            break
        end = j
    return end + 1


def find_excluded_lines(source: str) -> tuple[list[int], list[str]]:
    """Resolve ``# gd-tools: no cover`` annotations to excluded line numbers.

    Semantics are flat (first-match, no nesting):

    - An annotation (line or ``start`` form) on a ``func`` definition
      line excludes the entire function body.
    - ``start`` opens a block closed by the first matching ``end``;
      a nested ``start`` is ignored with a warning, a ``start`` with
      no ``end`` excludes to end of file with a warning, and a stray
      ``end`` is ignored with a warning.
    - Otherwise the annotation excludes its own line only.

    Args:
        source: Raw GDScript source code.

    Returns:
        A tuple of (sorted 1-based excluded line numbers, warning
        messages without file context).
    """
    lines = source.splitlines()
    annotations = _scan_annotations(source)

    func_spans: dict[int, int] = {}
    for idx, text in enumerate(lines):
        if _FUNC_DEF_RE.match(text):
            func_spans[idx + 1] = _func_span_end(lines, idx)

    excluded: set[int] = set()
    consumed: set[int] = set()
    warnings: list[str] = []

    # Function-level exclusions take precedence and are handled first.
    for lineno, kind in annotations:
        if lineno in func_spans and kind in (None, "start"):
            excluded.update(range(lineno, func_spans[lineno] + 1))
            consumed.add(lineno)

    open_start: int | None = None
    for lineno, kind in annotations:
        if lineno in consumed or lineno in excluded:
            continue
        if kind == "start":
            if open_start is None:
                open_start = lineno
            else:
                warnings.append(
                    f"line {lineno}: nested '{ANNOTATION_TOKEN} start' ignored"
                )
        elif kind == "end":
            if open_start is not None:
                excluded.update(range(open_start, lineno + 1))
                open_start = None
            else:
                warnings.append(
                    f"line {lineno}: '{ANNOTATION_TOKEN} end' without "
                    "matching start ignored"
                )
        else:
            excluded.add(lineno)

    if open_start is not None:
        warnings.append(
            f"line {open_start}: unterminated '{ANNOTATION_TOKEN} start' "
            "- excluding to end of file"
        )
        excluded.update(range(open_start, len(lines) + 1))

    return sorted(excluded), warnings


# --- Coverage Visitor (FR-2, FR-3) ---

#: AST node names tracked as statements.
STATEMENT_NODES = frozenset(
    {
        "expr_stmt",
        "return_stmt",
        "func_var_assigned",
        "func_var_typed_assgnd",
        "func_var_inf",
        "break_stmt",
        "continue_stmt",
    }
)

#: AST node names for control-flow statements. These are not tracked as
#: statements themselves, but each begins with a keyword, so its line is a legal
#: tracker insertion point and may anchor a ternary found in its header.
STATEMENT_HEADER_NODES = frozenset(
    {
        "if_stmt",
        "while_stmt",
        "for_stmt",
        "for_stmt_typed",
        "match_stmt",
    }
)

#: Every node whose line may serve as a tracker insertion point: a ternary is
#: anchored to the nearest enclosing node in this set. Class-body initializers
#: (``var x = ...`` inside a ``class``) are deliberately absent -- no statement
#: node encloses them and their line is not a legal insertion point.
ANCHOR_NODES = STATEMENT_NODES | STATEMENT_HEADER_NODES


#: AST node names for class-level member variable declarations. A point
#: recorded on a member declaration's own line would have its tracker
#: injected into the class body, where GDScript permits no statement, so
#: those lines are never legal insertion points.
CLASS_MEMBER_NODES = frozenset({"class_var_stmt", "static_class_var_stmt"})


def _collect_illegal_lines(root: Tree) -> set[int]:
    """Collect the lines on which no tracker call may be injected.

    The collector inserts each tracker as its own line immediately *before*
    the recorded line, so a recorded line must be one where a statement may
    begin. Two AST contexts violate that:

    - A class-member declaration line (``class_var_stmt`` and its
      ``static`` wrapper). Statements squash onto such lines when a lambda
      body is written inline, and injecting before the line would place a
      statement into the class body.
    - Any line within a function signature span (``func_header``), including
      multi-line signatures. A lambda in a default parameter squashes its
      body statement onto a signature line.

    Args:
        root: Root of the parsed GDScript AST.

    Returns:
        Set of 1-indexed line numbers where a tracker may not be injected.
    """
    illegal: set[int] = set()

    def walk(node: Tree) -> None:
        if node.data in CLASS_MEMBER_NODES:
            illegal.add(node.meta.line)
        elif node.data == "func_header":
            end_line = getattr(node.meta, "end_line", None) or node.meta.line
            illegal.update(range(node.meta.line, end_line + 1))
        for child in node.children:
            if isinstance(child, Tree):
                walk(child)

    walk(root)
    return illegal


def _collect_continuation_lines(source: str) -> set[int]:
    """Collect the lines that continue an expression from a previous line.

    A tracker is injected as its own line immediately before the recorded
    line, so the recorded line must be one where a statement may begin.
    Two textual contexts violate that regardless of AST shape:

    - A line whose start sits inside a bracket opened on an earlier line
      (the line continues a multi-line expression).
    - A line whose previous line ends with a backslash continuation.

    Both are detected by a small lexer that tracks bracket depth across
    lines while skipping string literals (including triple-quoted ones)
    and comments. A comment line ending in a backslash is over-marked:
    the point is dropped rather than mis-injected, which errs on the safe
    side.

    Args:
        source: Full GDScript source text.

    Returns:
        Set of 1-indexed line numbers where a tracker may not be injected.
    """
    illegal: set[int] = set()
    depth = 0
    quote: str | None = None
    escaped = False
    line = 1
    i = 0
    n = len(source)
    while i < n:
        ch = source[i]
        if quote is not None:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
            i += 1
            continue
        if ch in "\"'":
            triple = ch * 3
            if source[i : i + 3] == triple:
                end = source.find(triple, i + 3)
                if end == -1:
                    break
                line += source.count("\n", i, end + 3)
                i = end + 3
                continue
            quote = ch
            i += 1
            continue
        if ch == "#":
            while i < n and source[i] != "\n":
                i += 1
            continue
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth = max(depth - 1, 0)
        elif ch == "\n":
            ends_backslash = i > 0 and source[i - 1] == "\\"
            if depth > 0 or ends_backslash:
                illegal.add(line + 1)
            line += 1
        i += 1
    return illegal


def _map_ternary_anchors(root: Tree) -> dict[int, int]:
    """Map ``id()`` of each ``test_expr`` node to its anchor line.

    A ternary branch point is only instrumentable when recorded at a line
    where a statement may begin, so it is anchored to the nearest enclosing
    node in :data:`ANCHOR_NODES`. A ternary with no such node -- one inside a
    class-level initializer or a default parameter value -- has no legal
    insertion point and is not tracked.

    A recursive walk is required rather than the flat bottom-up visitor:
    :meth:`lark.visitors.Visitor.visit` exposes no ancestry, so a ternary
    encountered in a class-level ``const`` initializer would otherwise be
    attributed to whichever statement happened to be visited next -- for
    example a ``print()`` several lines later in the file.

    Keys are object identities valid only for the duration of a single
    traversal, so the map must be built and consumed within one
    :meth:`CoverageVisitor.visit` call.

    Args:
        root: Root of the parsed GDScript AST.

    Returns:
        Mapping from ``id()`` of each ``test_expr`` node to its anchor
        line, containing only anchorable ternaries.
    """
    anchors: dict[int, int] = {}

    def walk(node: Tree, enclosing: int | None) -> None:
        if node.data in ANCHOR_NODES:
            enclosing = node.meta.line
        if node.data == "test_expr" and enclosing is not None:
            anchors[id(node)] = enclosing
        for child in node.children:
            if isinstance(child, Tree):
                walk(child, enclosing)

    walk(root, None)
    return anchors


class CoverageVisitor(Visitor):
    """Lark AST visitor that identifies trackable statements and branches.

    Walks the parsed GDScript AST and collects :class:`LinePlan` entries
    for each trackable statement and branch point.

    Attributes:
        points: List of collected trackable points.
    """

    def __init__(
        self,
        excluded_lines: set[int] | None = None,
        source: str | None = None,
    ) -> None:
        self.points: list[LinePlan] = []
        self._next_id: int = 0
        self._excluded_lines = excluded_lines or set()
        self._source = source
        self._ternary_anchors: dict[int, int] = {}
        self._illegal_lines: set[int] = set()

    def visit(self, tree: Tree) -> Tree:
        """Resolve ternary anchors and illegal lines, then walk bottom-up.

        :meth:`visit` is overridden so that anchor resolution cannot be
        bypassed by a caller that only invokes ``visit()``, which is how
        :func:`generate_plan` drives this visitor.
        """
        self._ternary_anchors = _map_ternary_anchors(tree)
        self._illegal_lines = _collect_illegal_lines(tree)
        if self._source is not None:
            self._illegal_lines |= _collect_continuation_lines(self._source)
        return super().visit(tree)

    def _add_point(
        self,
        tree: Tree,
        point_type: str,
        branch_type: str | None = None,
        line: int | None = None,
    ) -> None:
        """Extract line number and append a new :class:`LinePlan`.

        Args:
            tree: The AST node being tracked.
            point_type: Either "statement" or "branch".
            branch_type: Branch type string if ``point_type`` is
                "branch", otherwise ``None``.
            line: Explicit 1-indexed line to record, or ``None`` to use
                the node's own line. Used by ternary branches, which are
                anchored to their enclosing statement. The exclusion
                check applies to whichever line is recorded.
                Points on lines where no tracker may be injected (class
                member declaration lines, function signature spans) are
                dropped silently rather than recorded.
        """
        resolved_line = line if line is not None else tree.meta.line
        if (
            resolved_line in self._excluded_lines
            or resolved_line in self._illegal_lines
        ):
            return
        self.points.append(
            LinePlan(
                line=resolved_line,
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

    def test_expr(self, tree: Tree) -> None:
        """Track ternary expression branches (true and false values).

        The ``test_expr`` AST node materializes exclusively for ternary
        expressions (``value_if_true if cond else value_if_false``). Both
        value-branches are tracked as separate branch points.

        Both points are anchored to the nearest enclosing node whose line is a
        legal tracker insertion point (see :data:`ANCHOR_NODES`), rather than
        the ternary's own line. A tracker call is injected *before* the planned
        line, so a ternary may only be planned on a line where a statement can
        begin. ``test_expr`` is the one tracked node whose first token is an
        arbitrary operand rather than a keyword, so its own line is only a
        statement boundary by coincidence. A ternary nested in a multi-line
        parenthesized expression would otherwise be planned on a continuation
        line and injected inside the open bracket.

        A ternary with no enclosing anchor node -- one inside a class-level
        ``const``/``var`` initializer, a ``@export`` initializer, or a default
        parameter value -- has no legal insertion point at all and is not
        tracked.
        """
        anchor = self._ternary_anchors.get(id(tree))
        if anchor is None:
            return
        self._add_point(tree, "branch", "ternary_true", line=anchor)
        self._add_point(tree, "branch", "ternary_false", line=anchor)


# --- Plan Generation (FR-4, FR-6) ---


def generate_plan(
    project_root: str,
    exclude_dirs: list[str] | None = None,
    test_dirs: list[str] | None = None,
) -> CoveragePlan:
    """Generate a coverage plan for a Godot project.

    Discovers all ``.gd`` files in ``project_root``, parses each one,
    runs :class:`CoverageVisitor` to identify trackable points, and
    assembles a :class:`CoveragePlan` with sequential ``file_id`` values.

    Args:
        project_root: Root directory of the Godot project.
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
    console = Console()
    stderr_console = Console(file=sys.stderr, soft_wrap=True)
    for file_id, gd_file in enumerate(gd_files):
        source = Path(gd_file).read_text(encoding="utf-8")
        source_hash = (
            "sha256:" + hashlib.sha256(source.encode("utf-8")).hexdigest()
        )

        try:
            tree = parse_gdscript(source)
            excluded, warnings = find_excluded_lines(source)
            visitor = CoverageVisitor(
                excluded_lines=set(excluded), source=source
            )
            visitor.visit(tree)
        except LarkError:
            console.print(
                f"[yellow]Warning: Skipping '{gd_file}' — "
                "syntax error prevents coverage parsing.[/yellow]"
            )
            continue

        for warning in warnings:
            stderr_console.print(
                f"[yellow]Warning: '{gd_file}' {warning}[/yellow]"
            )

        # Build res:// path
        rel_path = Path(gd_file).relative_to(project_root)
        res_path = "res://" + str(rel_path).replace("\\", "/")

        file_plans.append(
            FilePlan(
                file_id=file_id,
                path=res_path,
                source_hash=source_hash,
                lines=visitor.points,
                excluded_lines=excluded,
            )
        )

    return CoveragePlan(
        version=PLAN_VERSION,
        generated_by="gd-tools",
        files=file_plans,
    )


# --- Plan Caching (Track 37) ---


def _cached_plan_version(path: str) -> int | None:
    """Peek at a cached plan file's schema version.

    Args:
        path: Path to the cached ``plan.json``.

    Returns:
        The schema version, or ``None`` when the file cannot be read,
        is not valid JSON, or has no integer ``version`` field.
    """
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if isinstance(data, dict) and isinstance(data.get("version"), int):
        return data["version"]
    return None


def generate_plan_cached(
    project_root: str,
    exclude_dirs: list[str] | None = None,
    test_dirs: list[str] | None = None,
    cache_path: str | None = None,
    use_cache: bool = True,
) -> tuple[CoveragePlan, CacheStatus]:
    """Generate a coverage plan, reusing a cached plan when possible.

    When ``use_cache`` is ``True`` and a valid ``plan.json`` exists at
    ``cache_path``, the cached plan's file set and source hashes are
    compared against the currently discovered ``.gd`` files.  If every
    file path and hash matches, the cached plan is reused without AST
    parsing.  Otherwise — or when the cache is disabled, missing, or
    corrupt — a fresh plan is generated via :func:`generate_plan`.

    Args:
        project_root: Root directory of the Godot project.
        exclude_dirs: Directories to exclude from discovery.
            Defaults to :data:`~gd_tools.config.DEFAULT_EXCLUDES`.
        test_dirs: Directories whose files should be excluded from
            coverage targets. Defaults to ``["test", "tests"]``.
        cache_path: Path to the cached ``plan.json``. If ``None`` or
            the file does not exist, the cache is always missed.
        use_cache: If ``False``, force full regeneration regardless
            of cache state.

    Returns:
        A tuple of ``(CoveragePlan, CacheStatus)``. ``CacheStatus.hit``
        is ``True`` when the cached plan was reused; ``reason`` explains
        the outcome (e.g. ``"3 files unchanged"`` or ``"1 changed"``).
    """
    # Resolve defaults the same way generate_plan does.
    if exclude_dirs is None:
        from gd_tools.config import DEFAULT_EXCLUDES

        exclude_dirs = DEFAULT_EXCLUDES.copy()

    if test_dirs is None:
        test_dirs = ["test", "tests"]

    # --- Attempt cache hit ---
    if use_cache and cache_path is not None and Path(cache_path).exists():
        cached_version = _cached_plan_version(cache_path)
        if cached_version is not None and cached_version != PLAN_VERSION:
            fresh_plan = generate_plan(project_root, exclude_dirs, test_dirs)
            return fresh_plan, CacheStatus(
                hit=False,
                reason=(
                    f"cache plan version outdated "
                    f"(found {cached_version}, expected {PLAN_VERSION})"
                ),
            )
        try:
            cached_plan = read_plan_json(cache_path)
        except CoveragePlanError:
            cached_plan = None
        else:
            # Discover current files + compute hashes (no AST parsing).
            gd_files = discover_gd_files(project_root, excludes=exclude_dirs)
            gd_files = [
                f
                for f in gd_files
                if not any(td in PurePath(f).parts for td in test_dirs)
            ]

            current_hashes: dict[str, str] = {}
            for gd_file in gd_files:
                source = Path(gd_file).read_text(encoding="utf-8")
                # Skip files that generate_plan() would skip (syntax
                # errors) to avoid false cache misses.
                try:
                    parse_gdscript(source)
                except LarkError:
                    continue
                res_path = "res://" + str(
                    Path(gd_file).relative_to(project_root)
                ).replace("\\", "/")
                current_hashes[res_path] = (
                    "sha256:"
                    + hashlib.sha256(source.encode("utf-8")).hexdigest()
                )

            cached_hashes = {
                fp.path: fp.source_hash for fp in cached_plan.files
            }

            if current_hashes == cached_hashes:
                return cached_plan, CacheStatus(
                    hit=True,
                    reason=f"{len(cached_plan.files)} files unchanged",
                )

            # Determine the reason for the miss.
            current_paths = set(current_hashes)
            cached_paths = set(cached_hashes)
            added = len(current_paths - cached_paths)
            deleted = len(cached_paths - current_paths)
            changed = sum(
                1
                for p in current_paths & cached_paths
                if current_hashes[p] != cached_hashes[p]
            )

            parts: list[str] = []
            if added:
                parts.append(f"{added} added")
            if deleted:
                parts.append(f"{deleted} deleted")
            if changed:
                parts.append(f"{changed} changed")
            reason = ", ".join(parts) if parts else "file set changed"

            fresh_plan = generate_plan(project_root, exclude_dirs, test_dirs)
            return fresh_plan, CacheStatus(hit=False, reason=reason)

    # --- Cache miss: disabled, no path, missing, or corrupt ---
    if not use_cache:
        reason = "cache disabled"
    elif cache_path is None:
        reason = "no cache path provided"
    elif not Path(cache_path).exists():
        reason = "cache file missing"
    else:
        reason = "cache file corrupt or invalid"

    fresh_plan = generate_plan(project_root, exclude_dirs, test_dirs)
    return fresh_plan, CacheStatus(hit=False, reason=reason)
