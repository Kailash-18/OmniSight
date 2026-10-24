"""Tests for RetryPolicy."""

import pytest
from automation.retry_policy import RetryPolicy


def test_retry_policy_succeeds_first_try():
    calls = 0

    def work():
        nonlocal calls
        calls += 1
        return "success"

    policy = RetryPolicy(max_attempts=3, initial_delay_sec=0.01)
    res = policy.execute(work)
    assert res == "success"
    assert calls == 1


def test_retry_policy_retries_and_succeeds():
    calls = 0

    def flaky():
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ConnectionError("Temporary glitch")
        return "recovered"

    policy = RetryPolicy(max_attempts=4, initial_delay_sec=0.01, retryable_exceptions=(ConnectionError,))
    res = policy.execute(flaky)
    assert res == "recovered"
    assert calls == 3


def test_retry_policy_exhausts_and_raises():
    calls = 0

    def always_fails():
        nonlocal calls
        calls += 1
        raise ValueError("Permanent invalid value")

    policy = RetryPolicy(max_attempts=2, initial_delay_sec=0.01)
    with pytest.raises(ValueError, match="Permanent invalid value"):
        policy.execute(always_fails)
    assert calls == 2
