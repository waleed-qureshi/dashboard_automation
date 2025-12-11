import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_insights_ok():
    res = client.get('/api/insights')
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, dict)
