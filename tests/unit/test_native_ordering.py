"""Unit tests for the seeded native suite ordering module."""

import random
import time

import pytest

from gd_tools.native_test.ordering import (
    apply_random_order,
    generate_seed,
    resolve_seed,
)
from gd_tools.native_test.protocol import NativeSuite, NativeTest

pytestmark = pytest.mark.unit


def _suite(name, test_names=("test_a",)):
    """Build a minimal native suite with the given method names."""
    return NativeSuite(
        name=name,
        path=f"res://tests/{name}.gd",
        tests=[NativeTest(name=test_name) for test_name in test_names],
    )


def _suites(count, test_names=("test_a", "test_b", "test_c")):
    """Build ``count`` suites, each with the given methods."""
    return [_suite(f"Suite{i}", test_names) for i in range(count)]


def _suite_order(result):
    """Suite names in execution order."""
    return [suite.name for suite in result.suites]


def _method_order(result, suite_name):
    """Method names of one suite, in execution order."""
    for suite in result.suites:
        if suite.name == suite_name:
            return _method_names(suite)
    raise AssertionError(f"suite {suite_name} not in result")


def _method_names(suite):
    """Method names of one suite, in the order the suite holds them."""
    return [test.name for test in suite.tests]


# --- seed resolution ---


def test_resolve_seed_prefers_the_explicit_seed():
    """An explicit seed wins over a configured one."""
    assert resolve_seed(11, 22) == 11


def test_resolve_seed_falls_back_to_the_configured_seed():
    """A configured seed is used when no explicit seed is given."""
    assert resolve_seed(None, 22) == 22


def test_resolve_seed_generates_when_both_are_absent():
    """With neither seed set, a fresh seed is generated."""
    resolved = resolve_seed(None, None)

    assert isinstance(resolved, int)
    assert 0 <= resolved < (1 << 31)


def test_generate_seed_is_a_non_negative_31_bit_integer():
    """Generated seeds fit the reported 31-bit unsigned range."""
    for _ in range(50):
        seed = generate_seed()
        assert 0 <= seed < (1 << 31)


def test_generate_seed_differs_across_calls():
    """Generated seeds vary between runs rather than repeating."""
    seeds = {generate_seed() for _ in range(20)}

    assert len(seeds) > 1


def test_resolve_seed_accepts_zero():
    """Seed 0 is a legal seed and must not be treated as absent."""
    assert resolve_seed(0, 22) == 0


# --- determinism and replay ---


def test_same_seed_reproduces_an_identical_order():
    """The same seed over the same input replays the same order (FR-16)."""
    suites = _suites(6)

    first = apply_random_order(suites, 1234)
    second = apply_random_order(suites, 1234)

    assert _suite_order(first) == _suite_order(second)
    assert _method_order(first, "Suite0") == _method_order(second, "Suite0")


def test_different_seeds_produce_different_orders():
    """Different seeds over the same input shuffle differently."""
    suites = _suites(6)

    first = apply_random_order(suites, 1)
    second = apply_random_order(suites, 2)

    assert _suite_order(first) != _suite_order(second)


def test_method_order_is_shuffled():
    """Methods inside a suite are reordered, not left as declared."""
    suites = [_suite("Suite0", ("test_a", "test_b", "test_c", "test_d"))]

    result = apply_random_order(suites, 99)

    assert sorted(_method_order(result, "Suite0")) == [
        "test_a",
        "test_b",
        "test_c",
        "test_d",
    ]
    assert _method_order(result, "Suite0") != [
        "test_a",
        "test_b",
        "test_c",
        "test_d",
    ]


def test_method_shuffle_is_deterministic_across_runs():
    """Method order depends only on the seed and the input."""
    suites = [_suite("Suite0", ("test_a", "test_b", "test_c", "test_d"))]

    first = apply_random_order(suites, 7)
    second = apply_random_order(suites, 7)

    assert _method_order(first, "Suite0") == _method_order(second, "Suite0")


# --- permutation integrity ---


def test_result_is_a_permutation_of_the_input():
    """Every suite and method survives exactly once (FR-7, FR-8)."""
    suites = _suites(8)

    result = apply_random_order(suites, 321)

    assert sorted(_suite_order(result)) == sorted(s.name for s in suites)
    for suite in suites:
        before = sorted(test.name for test in suite.tests)
        after = sorted(_method_order(result, suite.name))
        assert before == after


def test_input_is_not_mutated():
    """The caller's suite list and method lists are left untouched."""
    suites = _suites(5)
    before = [(s.name, _method_names(s)) for s in suites]

    apply_random_order(suites, 55)

    after = [(s.name, _method_names(s)) for s in suites]
    assert before == after


# --- small-input handling ---


def test_single_suite_is_returned_unchanged():
    """A one-suite input keeps its (only) suite."""
    result = apply_random_order([_suite("Only")], 3)

    assert _suite_order(result) == ["Only"]


def test_empty_input_yields_empty_result():
    """An empty suite list is valid and yields no suites."""
    result = apply_random_order([], 3)

    assert result.suites == []
    assert result.seed == 3


def test_short_lists_are_not_shuffled(monkeypatch):
    """Lists shorter than two entries are never shuffled.

    ``random.shuffle`` is a no-op on a one-element sequence, so the guard
    only makes the skip explicit. The spy records the length of every list
    actually handed to ``random.shuffle``.
    """
    lengths = []
    original = random.Random.shuffle

    def spy(self, sequence, *args, **kwargs):
        lengths.append(len(sequence))
        return original(self, sequence, *args, **kwargs)

    monkeypatch.setattr(random.Random, "shuffle", spy)

    apply_random_order(
        [_suite("Single", ("only",)), _suite("Pair", ("t1", "t2"))], 7
    )

    # The suite list (2 entries) and the two-method suite (2); the
    # single-method suite is skipped.
    assert lengths == [2, 2]


# --- performance ---


def test_ordering_is_fast_for_a_large_suite_set():
    """1,000 suites / 10,000 tests order well under the 50 ms budget."""
    suites = [
        _suite(f"Suite{i}", tuple(f"test_{j}" for j in range(10)))
        for i in range(1000)
    ]

    start = time.perf_counter()
    result = apply_random_order(suites, 4242)
    elapsed = time.perf_counter() - start

    assert len(result.suites) == 1000
    assert elapsed < 0.05
