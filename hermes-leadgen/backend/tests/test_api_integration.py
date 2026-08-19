"""Exercises key endpoints through the real FastAPI HTTP layer (TestClient),
not just as direct Python calls. This is the layer that actually validates
`response_model`s against a JSON schema — a field typed `str` that actually
receives a `uuid.UUID` from the ORM passes a direct-call unit test but 500s
here, which is exactly the bug class this file exists to catch.
"""
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.core.db import get_db
from app.main import app
from app.models.lead import Lead
from app.models.user import User
from app.services.scoring_engine import seed_default_scoring_rules


def _client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    user = User(email="owner@example.com", password_hash="x", role="owner")
    db_session.add(user)
    db_session.commit()
    app.dependency_overrides[get_current_user] = lambda: user
    client = TestClient(app)
    yield client, user
    app.dependency_overrides.clear()


def test_scoring_rules_endpoint_serializes_cleanly(db_session):
    gen = _client(db_session)
    client, _ = next(gen)
    seed_default_scoring_rules(db_session)
    db_session.commit()

    resp = client.get("/api/scoring/rules")
    assert resp.status_code == 200
    rules = resp.json()
    assert len(rules) == 8
    assert all(isinstance(r["id"], str) for r in rules)


def test_leads_list_endpoint_serializes_cleanly(db_session):
    gen = _client(db_session)
    client, _ = next(gen)
    db_session.add(Lead(company_name="Acme Inc", website="https://acme.example.com"))
    db_session.commit()

    resp = client.get("/api/leads")
    assert resp.status_code == 200
    leads = resp.json()
    assert len(leads) == 1
    assert isinstance(leads[0]["id"], str)


def test_auth_me_endpoint_serializes_cleanly(db_session):
    gen = _client(db_session)
    client, user = next(gen)

    resp = client.get("/api/auth/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == str(user.id)
    assert body["email"] == user.email
