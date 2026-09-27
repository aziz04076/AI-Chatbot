import time
import os
import secrets
import contextvars
from contextlib import contextmanager
from typing import List, Dict, Any, Optional

# Context variable to hold active trace for asynchronous task safety
_current_trace: contextvars.ContextVar[Optional["Trace"]] = contextvars.ContextVar("current_trace", default=None)

class Span:
    """Represents an individual unit of work in distributed tracing."""
    def __init__(
        self,
        name: str,
        span_id: str,
        parent_span_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.span_id = span_id
        self.parent_span_id = parent_span_id
        self.start_time = time.perf_counter()
        self.end_time: Optional[float] = None
        self.duration_ms: float = 0.0
        self.status: str = "OK"
        self.attributes: Dict[str, Any] = attributes or {}

    def finish(self, status: str = "OK"):
        self.end_time = time.perf_counter()
        self.duration_ms = round((self.end_time - self.start_time) * 1000, 2)
        self.status = status

    def set_attribute(self, key: str, value: Any):
        self.attributes[key] = value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "attributes": self.attributes
        }

class Trace:
    """Manages root trace context and child span execution hierarchy."""
    def __init__(self, name: str = "root", attributes: Optional[Dict[str, Any]] = None):
        # 16-byte random hex (32 hex characters) for W3C compliance
        self.trace_id = secrets.token_hex(16)
        # 8-byte random hex (16 hex characters) for root span
        self.root_span_id = secrets.token_hex(8)
        self.spans: List[Span] = []
        self._span_stack: List[Span] = []

        root_span = Span(name=name, span_id=self.root_span_id, attributes=attributes)
        self.spans.append(root_span)
        self._span_stack.append(root_span)

    @property
    def traceparent(self) -> str:
        """Returns standard W3C traceparent header: 00-{trace_id}-{span_id}-01."""
        current_span_id = self._span_stack[-1].span_id if self._span_stack else self.root_span_id
        return f"00-{self.trace_id}-{current_span_id}-01"

    @contextmanager
    def span(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Context manager to record a child span."""
        parent_id = self._span_stack[-1].span_id if self._span_stack else self.root_span_id
        span_id = secrets.token_hex(8)
        new_span = Span(name=name, span_id=span_id, parent_span_id=parent_id, attributes=attributes)
        self.spans.append(new_span)
        self._span_stack.append(new_span)

        status = "OK"
        try:
            yield new_span
        except Exception as exc:
            status = "ERROR"
            new_span.set_attribute("error.message", str(exc))
            raise
        finally:
            new_span.finish(status=status)
            if self._span_stack and self._span_stack[-1] is new_span:
                self._span_stack.pop()

    def finish(self, status: str = "OK"):
        if self._span_stack:
            root_span = self._span_stack[0]
            root_span.finish(status=status)
            self._span_stack.clear()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "root_span_id": self.root_span_id,
            "traceparent": self.traceparent,
            "spans": [s.to_dict() for s in self.spans]
        }

class Tracer:
    """Thread-safe and async-safe tracer factory."""
    @contextmanager
    def start_trace(self, name: str = "request", attributes: Optional[Dict[str, Any]] = None):
        trace = Trace(name=name, attributes=attributes)
        token = _current_trace.set(trace)
        status = "OK"
        try:
            yield trace
        except Exception as exc:
            status = "ERROR"
            raise
        finally:
            trace.finish(status=status)
            _current_trace.reset(token)

    @staticmethod
    def get_current_trace() -> Optional[Trace]:
        return _current_trace.get()

tracer = Tracer()
