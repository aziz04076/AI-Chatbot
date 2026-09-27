import asyncio
import time
import random
import logging
from enum import Enum
from typing import Callable, Any, Optional, Dict, List, AsyncGenerator

logger = logging.getLogger("NexusAI-CircuitBreaker")

class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class CircuitBreakerOpenException(Exception):
    """Raised when an operation is attempted while the circuit breaker is OPEN."""
    pass

class CircuitBreaker:
    """
    Production-grade Circuit Breaker with Exponential Backoff and Jitter.
    Protects downstream LLM endpoints from cascading failures and socket exhaustion.
    """
    def __init__(
        self,
        name: str = "llm_circuit_breaker",
        failure_threshold: int = 3,
        recovery_timeout: float = 15.0,
        half_open_max_calls: int = 1,
        max_retries: int = 3,
        base_delay: float = 0.5,
        max_delay: float = 5.0
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

        self._state: CircuitState = CircuitState.CLOSED
        self._failure_count: int = 0
        self._success_count: int = 0
        self._total_calls: int = 0
        self._fallbacks_triggered: int = 0
        self._half_open_calls: int = 0
        self._last_failure_time: Optional[float] = None
        self._last_state_change: float = time.time()
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        # Check if recovery timeout has elapsed to transition from OPEN to HALF_OPEN
        if self._state == CircuitState.OPEN and self._last_failure_time:
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._transition_to(CircuitState.HALF_OPEN)
        return self._state

    def _transition_to(self, new_state: CircuitState):
        if self._state != new_state:
            logger.warning(f"[{self.name}] State transition: {self._state.value} -> {new_state.value}")
            self._state = new_state
            self._last_state_change = time.time()
            if new_state == CircuitState.HALF_OPEN:
                self._half_open_calls = 0
            elif new_state == CircuitState.CLOSED:
                self._failure_count = 0
                self._half_open_calls = 0

    def record_success(self):
        self._success_count += 1
        if self._state == CircuitState.HALF_OPEN:
            logger.info(f"[{self.name}] Canary probe succeeded. Resetting circuit to CLOSED.")
            self._transition_to(CircuitState.CLOSED)
        elif self._state == CircuitState.CLOSED:
            self._failure_count = 0

    def record_failure(self, error: Exception):
        self._failure_count += 1
        self._last_failure_time = time.time()
        logger.warning(f"[{self.name}] Recorded failure #{self._failure_count}: {error}")

        if self._state == CircuitState.HALF_OPEN:
            logger.warning(f"[{self.name}] Canary probe failed in HALF_OPEN. Re-opening circuit.")
            self._transition_to(CircuitState.OPEN)
        elif self._state == CircuitState.CLOSED and self._failure_count >= self.failure_threshold:
            logger.error(f"[{self.name}] Failure threshold {self.failure_threshold} reached. Tripping circuit to OPEN.")
            self._transition_to(CircuitState.OPEN)

    def calculate_backoff(self, attempt: int) -> float:
        """Computes exponential backoff with full random jitter."""
        factor = min(self.max_delay, self.base_delay * (2 ** attempt))
        # Uniform jitter: +/- 20%
        jitter = random.uniform(0.8, 1.2)
        return round(factor * jitter, 3)

    async def execute_stream(
        self,
        primary_generator_factory: Callable[..., AsyncGenerator[str, None]],
        fallback_generator_factory: Callable[..., AsyncGenerator[str, None]],
        *args,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Executes a streaming call with circuit breaker gating, exponential backoff,
        and automatic fallback to a secondary generator.
        """
        self._total_calls += 1
        current_state = self.state

        # Fast-fail to fallback if circuit is OPEN
        if current_state == CircuitState.OPEN:
            logger.info(f"[{self.name}] Circuit is OPEN. Fast-failing directly to fallback mock model.")
            self._fallbacks_triggered += 1
            async for token in fallback_generator_factory(*args, **kwargs):
                yield token
            return

        if current_state == CircuitState.HALF_OPEN:
            if self._half_open_calls >= self.half_open_max_calls:
                logger.info(f"[{self.name}] HALF_OPEN limit reached ({self._half_open_calls}). Delegating to fallback.")
                self._fallbacks_triggered += 1
                async for token in fallback_generator_factory(*args, **kwargs):
                    yield token
                return
            self._half_open_calls += 1

        # Attempt call with exponential backoff retries
        success = False
        last_error = None

        for attempt in range(self.max_retries):
            try:
                # Consume and stream first chunk to verify stream initialization
                stream = primary_generator_factory(*args, **kwargs)
                first_item_yielded = False

                async for chunk in stream:
                    if not first_item_yielded:
                        first_item_yielded = True
                        self.record_success()
                        success = True
                    yield chunk

                if first_item_yielded or success:
                    return

            except Exception as exc:
                last_error = exc
                logger.warning(f"[{self.name}] Attempt {attempt + 1}/{self.max_retries} failed: {exc}")
                if attempt < self.max_retries - 1 and self.state != CircuitState.OPEN:
                    delay = self.calculate_backoff(attempt)
                    logger.info(f"[{self.name}] Backing off for {delay}s before retry...")
                    await asyncio.sleep(delay)

        # Retries exhausted or exception raised
        if last_error:
            self.record_failure(last_error)

        logger.info(f"[{self.name}] Primary stream failed after retries. Routing to fallback generator.")
        self._fallbacks_triggered += 1
        async for token in fallback_generator_factory(*args, **kwargs):
            yield token

    def get_metrics(self) -> Dict[str, Any]:
        """Returns live observability statistics for telemetry & dashboards."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout_seconds": self.recovery_timeout,
            "consecutive_failures": self._failure_count,
            "successful_calls": self._success_count,
            "total_calls": self._total_calls,
            "fallbacks_triggered": self._fallbacks_triggered,
            "last_failure_time": self._last_failure_time,
            "last_state_change": self._last_state_change,
            "uptime_seconds": round(time.time() - self._last_state_change, 1)
        }

# Global circuit breaker singleton for LLM inference
llm_circuit_breaker = CircuitBreaker(
    name="llm_inference_breaker",
    failure_threshold=3,
    recovery_timeout=15.0,
    max_retries=3,
    base_delay=0.5,
    max_delay=4.0
)
