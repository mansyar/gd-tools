"""Regenerate expected plan JSON fixtures from GDScript test fixtures.

Run manually after modifying GDScript fixtures. Output must be manually
verified before committing.

Usage::

    python tools/generate_expected_plans.py
    python tools/generate_expected_plans.py --fixtures-dir <dir> --output-dir <dir>
"""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from gd_tools.coverage.plan_generator import generate_plan, write_plan_json

_FIXTURE_NAMES = [
    "simple",
    "branches",
    "loops",
    "match_stmt",
    "nested",
    "edge_cases",
]

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_FIXTURES_DIR = _PROJECT_ROOT / "tests" / "fixtures" / "gdscript"
_DEFAULT_OUTPUT_DIR = _PROJECT_ROOT / "tests" / "fixtures" / "plans"


def regenerate_expected_plans(
    fixtures_dir: Path, output_dir: Path
) -> list[Path]:
    """Regenerate expected plan JSON fixtures from .gd fixtures.

    For each .gd fixture, creates an isolated directory with only that
    file, runs ``generate_plan``, and writes the result to ``output_dir``.

    Args:
        fixtures_dir: Directory containing .gd test fixtures.
        output_dir: Directory to write expected plan JSON files.

    Returns:
        List of paths to generated JSON files.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    generated_files: list[Path] = []

    for name in _FIXTURE_NAMES:
        gd_file = fixtures_dir / f"{name}.gd"
        if not gd_file.exists():
            continue

        source = gd_file.read_text(encoding="utf-8")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / f"{name}.gd").write_text(source, encoding="utf-8")

            plan = generate_plan(str(tmp_path))
            output_file = output_dir / f"{name}.expected.json"
            write_plan_json(plan, str(output_file))
            generated_files.append(output_file)

    return generated_files


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for regenerating expected plan fixtures.

    Args:
        argv: Optional argument list (defaults to ``sys.argv``).
    """
    parser = argparse.ArgumentParser(
        description="Regenerate expected plan JSON fixtures from "
        ".gd fixtures."
    )
    parser.add_argument(
        "--fixtures-dir",
        type=Path,
        default=_DEFAULT_FIXTURES_DIR,
        help="Directory containing .gd test fixtures.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_DEFAULT_OUTPUT_DIR,
        help="Directory to write expected plan JSON files.",
    )
    args = parser.parse_args(argv)

    generated = regenerate_expected_plans(args.fixtures_dir, args.output_dir)

    print(f"Regenerated {len(generated)} expected plan fixtures:")
    for path in generated:
        print(f"  {path}")


if __name__ == "__main__":
    main()
