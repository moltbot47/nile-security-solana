"""Tests for the risk engine — circuit breaker and utility functions."""

from datetime import UTC, datetime, timedelta

from nile.services.risk_engine import (
    _active_breakers,
    activate_circuit_breaker,
    get_active_breakers,
    is_circuit_breaker_active,
)


def setup_function():
    """Clear circuit breakers before each test."""
    _active_breakers.clear()


# --- Circuit Breaker Tests ---


def test_circuit_breaker_initially_inactive():
    assert is_circuit_breaker_active("token-1") is False


def test_circuit_breaker_activates():
    expiry = activate_circuit_breaker("token-1", minutes=15)
    assert is_circuit_breaker_active("token-1") is True
    assert expiry > datetime.now(UTC)


def test_circuit_breaker_expires():
    """Expired breaker should return inactive."""
    _active_breakers["token-1"] = datetime.now(UTC) - timedelta(minutes=1)
    assert is_circuit_breaker_active("token-1") is False
    assert "token-1" not in _active_breakers  # Cleaned up


def test_get_active_breakers_filters_expired():
    activate_circuit_breaker("active-token", minutes=60)
    _active_breakers["expired-token"] = datetime.now(UTC) - timedelta(minutes=5)

    active = get_active_breakers()
    assert "active-token" in active
    assert "expired-token" not in active


def test_multiple_circuit_breakers():
    activate_circuit_breaker("token-a", minutes=10)
    activate_circuit_breaker("token-b", minutes=20)

    assert is_circuit_breaker_active("token-a") is True
    assert is_circuit_breaker_active("token-b") is True
    assert len(get_active_breakers()) == 2


def test_circuit_breaker_replaces_on_reactivate():
    first_expiry = activate_circuit_breaker("token-1", minutes=5)
    second_expiry = activate_circuit_breaker("token-1", minutes=30)

    assert second_expiry > first_expiry
    assert is_circuit_breaker_active("token-1") is True
