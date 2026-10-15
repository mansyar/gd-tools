"""Seeded ordering for native suite execution.

Random ordering is opt-in (``--random-order`` / ``[test] random_order``). A
single :class:`random.Random` stream seeded from the resolved seed shuffles
the suite order and then each suite's test-method order, so the whole
execution order is a pure function of ``(seed, suite set, test set)``.

Sharding is deliberately *not* affected by this module. ``--shard``
membership is computed from the deterministic discovery order before ordering
runs, so CI matrix jobs under different seeds still cover every suite exactly
once.

See the track spec FR-7, FR-8, FR-10, FR-11, FR-16.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from gd_tools.native_test.protocol import NativeSuite

#: Generated seeds are printed for the user to replay, so they are kept
#: short enough for a terminal line while staying wide enough not to repeat.
_SEED_BITS = 31


@dataclass(frozen=True)
class RandomOrderResult:
    """The resolved seed and the suites in shuffled execution order.

    Attributes:
        seed: The seed that produced ``suites``; replaying it reproduces
            the same order for the same suite and test sets.
        suites: Suites in execution order, each holding its methods in
            execution order. New objects; the input is never mutated.
    """

    seed: int
    suites: list[NativeSuite]


def generate_seed() -> int:
    """Return a fresh non-negative 31-bit seed.

    Uses :class:`random.SystemRandom` so successive runs do not repeat an
    order by accident.

    Returns:
        An integer in ``[0, 2**31)``.
    """
    return random.SystemRandom().randrange(1 << _SEED_BITS)


def resolve_seed(cli_seed: int | None, config_seed: int | None) -> int:
    """Resolve the effective seed from the CLI and config surfaces.

    Seed ``0`` is a legal seed, so both checks are ``is not None`` rather
    than truthiness tests.

    Args:
        cli_seed: The ``--seed`` value, or None when the flag was absent.
        config_seed: The ``[test] seed`` value, or None when unset.

    Returns:
        The explicit CLI seed when given, else the configured seed, else a
        freshly generated one.
    """
    if cli_seed is not None:
        return cli_seed
    if config_seed is not None:
        return config_seed
    return generate_seed()


def apply_random_order(
    suites: list[NativeSuite],
    seed: int,
) -> RandomOrderResult:
    """Shuffle suite and test-method execution order with ``seed``.

    The suite list is shuffled first, then each suite's methods are
    shuffled in the resulting suite order, drawing from one seeded stream.
    Sequences shorter than two entries are returned as-is rather than
    handed to ``random.shuffle``: the call would be a no-op (nothing to
    permute), so skipping it states the intent instead of relying on that
    detail of the standard library.

    Args:
        suites: Suites in deterministic discovery order. Not modified.
        seed: The shuffle seed.

    Returns:
        A :class:`RandomOrderResult` holding the seed and a new list of
        suites, each a copy carrying its shuffled methods.
    """
    rng = random.Random(seed)

    ordered = list(suites)
    if len(ordered) > 1:
        rng.shuffle(ordered)

    result: list[NativeSuite] = []
    for suite in ordered:
        tests = list(suite.tests)
        if len(tests) > 1:
            rng.shuffle(tests)
        result.append(suite.model_copy(update={"tests": tests}))

    return RandomOrderResult(seed=seed, suites=result)
