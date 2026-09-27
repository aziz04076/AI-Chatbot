import pytest
import asyncio
import time
from app.core.circuit_breaker import CircuitBreaker, CircuitState, llm_circuit_breaker
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_circuit_breaker_closed_success():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0.2, max_retries=2, base_delay=0.01)
    assert cb.state == CircuitState.CLOSED

    async def primary():
        yield "token1"
        yield "token2"

    async def fallback():
        yield "fallback"

    results = []
    async for chunk in cb.execute_stream(primary, fallback):
        results.append(chunk)

    assert results == ["token1", "token2"]
    assert cb.state == CircuitState.CLOSED
    assert cb._failure_count == 0
    assert cb._success_count == 1

@pytest.mark.asyncio
async def test_circuit_breaker_trips_to_open_on_threshold():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0.2, max_retries=1, base_delay=0.01)

    async def failing_primary():
        if True:
            raise ConnectionError("Upstream server unreachable")
        yield "never"

    async def fallback():
        yield "fallback_token"

    # Call 1: failure #1 -> still CLOSED
    res1 = [t async for t in cb.execute_stream(failing_primary, fallback)]
    assert res1 == ["fallback_token"]
    assert cb.state == CircuitState.CLOSED
    assert cb._failure_count == 1

    # Call 2: failure #2 -> still CLOSED
    res2 = [t async for t in cb.execute_stream(failing_primary, fallback)]
    assert res2 == ["fallback_token"]
    assert cb.state == CircuitState.CLOSED
    assert cb._failure_count == 2

    # Call 3: failure #3 -> trips to OPEN
    res3 = [t async for t in cb.execute_stream(failing_primary, fallback)]
    assert res3 == ["fallback_token"]
    assert cb.state == CircuitState.OPEN
    assert cb._failure_count == 3

@pytest.mark.asyncio
async def test_circuit_breaker_open_fast_fails_to_fallback():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1.0, max_retries=1)
    cb._state = CircuitState.OPEN
    cb._last_failure_time = time.time()

    primary_called = False

    async def primary():
        nonlocal primary_called
        primary_called = True
        yield "from_primary"

    async def fallback():
        yield "fast_fallback"

    res = [t async for t in cb.execute_stream(primary, fallback)]
    assert res == ["fast_fallback"]
    # Verify primary generator was NEVER invoked when OPEN
    assert not primary_called
    assert cb.state == CircuitState.OPEN

@pytest.mark.asyncio
async def test_circuit_breaker_recovery_half_open_to_closed():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1, max_retries=1, base_delay=0.01)
    cb._state = CircuitState.OPEN
    cb._last_failure_time = time.time() - 0.2  # Simulate recovery timeout passed

    # Checking state property triggers transition to HALF_OPEN
    assert cb.state == CircuitState.HALF_OPEN

    async def successful_primary():
        yield "probe_ok"

    async def fallback():
        yield "fallback"

    # Canary probe in HALF_OPEN succeeds
    res = [t async for t in cb.execute_stream(successful_primary, fallback)]
    assert res == ["probe_ok"]
    assert cb.state == CircuitState.CLOSED
    assert cb._failure_count == 0

@pytest.mark.asyncio
async def test_circuit_breaker_half_open_failure_reopens():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1, max_retries=1, base_delay=0.01)
    cb._state = CircuitState.HALF_OPEN
    cb._half_open_calls = 0

    async def failing_canary():
        if True:
            raise TimeoutError("Canary probe timed out")
        yield "never"

    async def fallback():
        yield "canary_fallback"

    res = [t async for t in cb.execute_stream(failing_canary, fallback)]
    assert res == ["canary_fallback"]
    assert cb.state == CircuitState.OPEN

def test_backoff_calculation():
    cb = CircuitBreaker(base_delay=0.5, max_delay=4.0)
    delay0 = cb.calculate_backoff(0)
    delay1 = cb.calculate_backoff(1)
    delay2 = cb.calculate_backoff(2)
    delay3 = cb.calculate_backoff(3)

    assert 0.3 <= delay0 <= 0.7   # 0.5 * [0.8, 1.2]
    assert 0.7 <= delay1 <= 1.3   # 1.0 * [0.8, 1.2]
    assert 1.5 <= delay2 <= 2.5   # 2.0 * [0.8, 1.2]
    assert 3.0 <= delay3 <= 4.8   # 4.0 * [0.8, 1.2] (capped at max_delay)

@pytest.mark.asyncio
async def test_analytics_circuit_breaker_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/v1/analytics/circuit-breaker")
        assert response.status_code == 200
        data = response.json()
        assert "state" in data
        assert data["state"] in ["CLOSED", "OPEN", "HALF_OPEN"]
        assert "failure_threshold" in data
        assert "consecutive_failures" in data
        assert "successful_calls" in data
        assert "fallbacks_triggered" in data
