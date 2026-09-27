import pytest
from app.services.eval_service import EvaluationService, eval_service
from app.schemas.eval import BenchmarkQuery, EvalBenchmarkReport
from httpx import AsyncClient, ASGITransport
from app.core.security import create_access_token
from app.core.database import init_db
from app.main import app

def test_compute_percentiles():
    """Verifies nearest-rank percentile calculations for p50, p95, p99."""
    # Empty
    assert EvaluationService.compute_percentiles([]) == (0.0, 0.0, 0.0)

    # Single
    assert EvaluationService.compute_percentiles([42.0]) == (42.0, 42.0, 42.0)

    # Standard distribution
    latencies = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    p50, p95, p99 = EvaluationService.compute_percentiles(latencies)
    assert p50 == 55.0
    assert p95 > p50
    assert p99 >= p95

def test_detect_hallucination():
    """Verifies detection of counter-factual claims and ungrounded statements."""
    service = EvaluationService()

    # 1. Uncontested grounded context
    context = ["PodDisruptionBudget enforces minAvailable: 2 to prevent downtime."]
    grounded_text = "Verified specification: PodDisruptionBudget enforces minAvailable: 2 for downtime prevention."
    is_hallu, score = service.detect_hallucination(grounded_text, context, ["PDB is deprecated"])
    assert is_hallu is False
    assert score >= 0.50

    # 2. Contains unsupported counter-factual assertion
    bad_text = "According to specs, PDB is deprecated in v1.29."
    is_hallu_bad, score_bad = service.detect_hallucination(bad_text, context, ["PDB is deprecated in v1.29"])
    assert is_hallu_bad is True
    assert score_bad == 0.15

def test_run_benchmark():
    """Verifies that full benchmark evaluation computes valid statistical metrics."""
    report = eval_service.run_benchmark()
    assert isinstance(report, EvalBenchmarkReport)
    assert report.total_queries == 10
    assert 0.0 <= report.retrieval_precision_at_k <= 1.0
    assert 0.0 <= report.retrieval_recall_at_k <= 1.0
    assert 0.0 <= report.mean_reciprocal_rank <= 1.0
    assert 0.0 <= report.hallucination_rate <= 100.0
    assert abs((report.hallucination_rate + report.faithfulness_score) - 100.0) < 0.01
    assert report.latency_p50_ms <= report.latency_p95_ms
    assert len(report.query_results) == 10
    assert all(r.status in ["passed", "flagged", "failed"] for r in report.query_results)

@pytest.mark.asyncio
async def test_analytics_eval_endpoints():
    """Verifies GET /api/v1/analytics/eval and POST /api/v1/analytics/eval/run."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # GET eval report
        res_get = await ac.get("/api/v1/analytics/eval")
        assert res_get.status_code == 200
        data_get = res_get.json()
        assert "retrieval_precision_at_k" in data_get
        assert "hallucination_rate" in data_get
        assert "latency_p50_ms" in data_get
        assert len(data_get["query_results"]) == 10

        # POST run eval benchmark (guarded with RBAC operator+)
        op_token = create_access_token("eval_runner", role="operator")
        res_post = await ac.post("/api/v1/analytics/eval/run", headers={"Authorization": f"Bearer {op_token}"})
        assert res_post.status_code == 200
        data_post = res_post.json()
        assert data_post["total_queries"] == 10
        assert data_post["composite_score"] > 0
