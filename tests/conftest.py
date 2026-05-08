import pytest
import uuid
from app.main import app

import httpx

@pytest.fixture
async def test_client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def auth_headers(test_client):
    # Register a new user
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    password = "password123"
    reg_res = await test_client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "full_name": "Test User"
    })
    
    if reg_res.status_code != 201:
        print(f"DEBUG: Registration failed: {reg_res.text}")
        # If registration fails because user already exists (unlikely with uuid), try login
        login_res = await test_client.post("/api/v1/auth/login", json={
            "email": email,
            "password": password
        })
        token = login_res.json().get("access_token")
    else:
        token = reg_res.json().get("access_token")
        
    return {"Authorization": f"Bearer {token}"}
