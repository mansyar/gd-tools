"""Reconciliation of coverage targets the runtime could not instrument.

A coverage run measures what it could instrument. When a plan target cannot
be instrumented -- a stale plan naming a deleted file, or a script that
exists but does not load -- the run warns and continues (spec R1), so the
result is deliberately partial. The risk with any partial measurement is
that it looks complete, so this module makes the incompleteness explicit and
derivable.

Two questions, deliberately kept apart:

- **Which** targets were omitted? Derived as ``plan.files - data.files``.
  That is reliable only because R3 made the collectors seed an empty hit
  entry for every file they successfully instrument, so a file that was
  instrumented but never executed is present rather than absent.
- **Why** was each one omitted? Carried in the coverage data's additive
  ``omitted`` key (spec R5). A diff cannot know this: a stale plan and a
  broken script are different bugs with different fixes, and only the
  runtime, which ran the ``FileAccess.file_exists`` check, can tell them
  apart.

``omitted`` is authoritative for reasons only. If it and the data ever
disagreed about which files were instrumented, the derivation wins and a
generic reason is supplied -- otherwise a broken file could be reported as
clean.

This is the single reconciliation helper for both runtimes (spec R6). The
legacy seam is :func:`gd_tools.coverage.orchestrator._print_coverage_inline`
and the native seam calls the same function.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from gd_tools.coverage.plan_generator import CoveragePlan
from gd_tools.coverage.reporter import CoverageData, OmittedTarget

#: Used when a target is absent from the data yet undeclared in ``omitted``.
#: The two sources should never disagree, but if they do the derivation wins
#: and the reason says so rather than inventing a cause.
_UNKNOWN_REASON = (
    "the runtime did not report why this target could not be instrumented"
)
_UNKNOWN_FIX = (
    "re-run with --no-cache to regenerate the plan, and check the "
    "gd-tools log for warnings about this file"
)


@dataclass(frozen=True)
class OmissionReport:
    """The result of reconciling a plan against runtime coverage data.

    Attributes:
        omitted: Targets that were in the plan but not instrumented, each
            with a reason and a fix hint.
        plan_count: Total targets in the plan.
        instrumented_count: Targets the runtime actually instrumented.
    """

    omitted: list[OmittedTarget] = field(default_factory=list)
    plan_count: int = 0
    instrumented_count: int = 0

    @property
    def has_omissions(self) -> bool:
        """Whether any plan target went uninstrumented."""
        return bool(self.omitted)

    def __bool__(self) -> bool:
        """Truthy when something was omitted, so call sites can branch plainly."""
        return self.has_omissions


def reconcile_omissions(
    plan: CoveragePlan, data: CoverageData
) -> OmissionReport:
    """Identify the plan targets the runtime could not instrument.

    Args:
        plan: The instrumentation plan.
        data: The runtime coverage data.

    Returns:
        An :class:`OmissionReport`. A target counts as instrumented when it
        appears in ``data.files`` at all -- the empty-``hits`` entry R3
        produces for a file that was instrumented but never executed is
        present, and is correctly not an omission.
    """
    instrumented = {fc.file_id for fc in data.files}
    reasons = {o.file_id: o for o in data.omitted}
    plan_ids = [file_plan.file_id for file_plan in plan.files]

    omitted: list[OmittedTarget] = []
    for file_plan in plan.files:
        if file_plan.file_id in instrumented:
            continue
        declared = reasons.get(file_plan.file_id)
        omitted.append(
            declared
            if declared is not None
            else OmittedTarget(
                file_id=file_plan.file_id,
                path=file_plan.path,
                reason=_UNKNOWN_REASON,
                fix=_UNKNOWN_FIX,
            )
        )

    return OmissionReport(
        omitted=omitted,
        plan_count=len(plan.files),
        instrumented_count=len(instrumented & set(plan_ids)),
    )


def omission_gate_message(
    report: OmissionReport,
    min_percent: int | None,
) -> str | None:
    """Build the ``--min`` gate failure for a partial measurement (spec R6).

    The two conditions are deliberately not collapsed into one number. The
    percentage answers "how well is the code we measured covered"; this gate
    answers "was the measurement complete enough to gate on". Without it, a
    project could keep passing ``--min`` while its worst-covered files
    progressively failed to instrument and dropped out of the denominator.

    Without ``--min`` this returns ``None``: a plain
    ``gd-tools test --coverage`` must not fail because of an unrelated broken
    script. The omission is still reported, as a warning, by the terminal
    report.

    Args:
        report: The reconciliation result.
        min_percent: The ``--min`` threshold, or None when not requested.

    Returns:
        The gate failure message, or ``None`` when the gate is satisfied.
    """
    if min_percent is None or not report.has_omissions:
        return None

    lines = [
        f"Coverage measurement is incomplete: "
        f"{len(report.omitted)} of {report.plan_count} plan targets "
        f"could not be instrumented.",
        "",
    ]
    for target in report.omitted:
        lines.append(f"  {target.path}")
        lines.append(f"    Cause: {target.reason}")
        if target.fix:
            lines.append(f"    Fix:   {target.fix}")
    lines.append("")
    lines.append(
        f"--min {min_percent} was evaluated over the "
        f"{report.instrumented_count} target(s) that were instrumented, so "
        "the percentage above does not describe the whole project."
    )
    return "\n".join(lines)
