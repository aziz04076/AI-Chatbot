import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import init_db

@pytest.mark.asyncio
async def test_chat_endpoints():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Health
        health = await ac.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "healthy"

        # 2. Chat HTTP
        chat_resp = await ac.post("/api/v1/chat", json={
            "message": "What is the recommended vLLM gpu memory utilization?",
            "model_name": "nexus-llama3-8b-v1"
        })
        assert chat_resp.status_code == 200
        data = chat_resp.json()
        assert "content" in data
        assert data["confidence_score"] > 0.5
        assert len(data["follow_ups"]) > 0

        # 3. Model list
        models = await ac.get("/api/v1/models")
        assert models.status_code == 200
        assert "nexus-llama3-8b-v1" in models.json()["available_models"]

        # 4. Analytics
        analytics = await ac.get("/api/v1/analytics/metrics")
        assert analytics.status_code == 200
        assert "system_health" in analytics.json()
