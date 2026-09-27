import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import init_db

@pytest.mark.asyncio
async def test_auth_workflow():
    await init_db()
    unique_suffix = str(uuid.uuid4())[:8]
    email = f"test_{unique_suffix}@nexus.ai"
    username = f"user_{unique_suffix}"
    password = "SecurePassword123!"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Register
        reg_resp = await ac.post("/api/v1/auth/register", json={
            "email": email,
            "username": username,
            "password": password
        })
        assert reg_resp.status_code == 201
        data = reg_resp.json()
        assert "access_token" in data
        assert data["user"]["email"] == email

        # 2. Login
        login_resp = await ac.post("/api/v1/auth/login", json={
            "username_or_email": email,
            "password": password
        })
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        assert token is not None

        # 3. Get profile
        me_resp = await ac.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_resp.status_code == 200
        assert me_resp.json()["username"] == username
