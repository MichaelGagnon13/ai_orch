"""Tests de sécurité API - TASK-14"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_error_has_required_fields(client):
    response = client.post("/sum", json={})
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "code" in data
    assert "timestamp" in data
    assert "path" in data


def test_valid_request_works(client):
    response = client.post("/sum", json={"numbers": [1, 2, 3]})
    assert response.status_code == 200
    data = response.get_json()
    assert data["result"] == 6


def test_cors_headers_present(client):
    response = client.get("/health")
    assert "Access-Control-Allow-Origin" in response.headers


def test_health_works(client):
    response = client.get("/health")
    assert response.status_code == 200
