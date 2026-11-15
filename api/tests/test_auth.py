import os
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ["DEMO_MODE"] = "true"

import jwt
from fastapi.testclient import TestClient
from app.auth import create_token, ALGORITHM
from app.main import app

client = TestClient(app)


class U:  # minimal stand-in for a User row
    id = 1
    role = "auditor"


def test_me_requires_token():
    assert client.get("/api/auth/me").status_code == 401


def test_bad_token_rejected():
    r = client.get("/api/auth/me", headers={"Authorization": "Bearer nope"})
    assert r.status_code == 401


def test_token_roundtrip():
    tok = create_token(U())
    payload = jwt.decode(tok, "test-secret", algorithms=[ALGORITHM])
    assert payload["sub"] == "1" and payload["role"] == "auditor"