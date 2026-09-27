import pytest
import time
from app.core.telemetry import Span, Trace, Tracer, tracer
from httpx import AsyncClient, ASGITransport
from app.main import app

def test_span_lifecycle():
    span = Span(name="test_span", span_id="0123456789abcdef", parent_span_id="fedcba9876543210", attributes={"env": "test"})
    assert span.name == "test_span"
    assert span.span_id == "0123456789abcdef"
    assert span.parent_span_id == "fedcba9876543210"
    assert span.attributes["env"] == "test"
    assert span.status == "OK"
    assert span.duration_ms == 0.0

    time.sleep(0.01)
    span.finish(status="OK")
    assert span.duration_ms > 0.0
    data = span.to_dict()
    assert data["name"] == "test_span"
    assert data["duration_ms"] == span.duration_ms
    assert data["status"] == "OK"

def test_trace_w3c_compliance():
    trace = Trace(name="root_request")
    # trace_id must be 16 bytes = 32 hex chars
    assert len(trace.trace_id) == 32
    assert all(c in "0123456789abcdef" for c in trace.trace_id)
    # root_span_id must be 8 bytes = 16 hex chars
    assert len(trace.root_span_id) == 16
    assert all(c in "0123456789abcdef" for c in trace.root_span_id)

    # traceparent format: 00-{trace_id}-{span_id}-01
    tp = trace.traceparent
    parts = tp.split("-")
    assert len(parts) == 4
    assert parts[0] == "00"
    assert parts[1] == trace.trace_id
    assert parts[2] == trace.root_span_id
    assert parts[3] == "01"

def test_trace_nested_spans():
    with tracer.start_trace("pipeline") as trace:
        root_span_id = trace.root_span_id

        with trace.span("step_1", {"tag": "agent"}) as s1:
            time.sleep(0.005)
            assert s1.parent_span_id == root_span_id
            assert s1.attributes["tag"] == "agent"

        with trace.span("step_2", {"tag": "rag"}) as s2:
            time.sleep(0.005)
            assert s2.parent_span_id == root_span_id

    trace_dict = trace.to_dict()
    assert trace_dict["trace_id"] == trace.trace_id
    assert len(trace_dict["spans"]) == 3  # root + s1 + s2
    names = [s["name"] for s in trace_dict["spans"]]
    assert names == ["pipeline", "step_1", "step_2"]
    for s in trace_dict["spans"]:
        assert s["duration_ms"] >= 0

def test_span_error_handling():
    with tracer.start_trace("error_trace") as trace:
        try:
            with trace.span("faulty_span"):
                raise ValueError("simulated execution failure")
        except ValueError:
            pass

    faulty = [s for s in trace.spans if s.name == "faulty_span"][0]
    assert faulty.status == "ERROR"
    assert "simulated execution failure" in faulty.attributes.get("error.message", "")

@pytest.mark.asyncio
async def test_http_chat_distributed_tracing():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/v1/chat", json={
            "message": "Calculate compute cost for 4 nodes",
            "use_rag": True,
            "stream": False
        })
        assert response.status_code == 200
        # Check HTTP W3C tracing headers
        assert "x-trace-id" in response.headers or "X-Trace-ID" in response.headers
        assert "traceparent" in response.headers
        traceparent = response.headers.get("traceparent")
        assert traceparent.startswith("00-")

        # Check JSON payload telemetry
        data = response.json()
        assert "trace_id" in data
        assert len(data["trace_id"]) == 32
        assert "trace_spans" in data
        span_names = [s["name"] for s in data["trace_spans"]]
        assert "chat_http" in span_names
        assert "rag_retrieval" in span_names
        assert "llm_inference" in span_names
