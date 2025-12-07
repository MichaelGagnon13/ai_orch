import pytest

from app import app


@pytest.fixture
def client():
    return app.test_client()


def test_sum_ok(client):
    response = client.post("/sum", json={"numbers": [1, 2, 3]})
    assert response.status_code == 200
    assert response.get_json()["result"] == 6


def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_sum_bad_payload(client):
    r = client.post("/sum", json={"numbers": "oops"})
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_budget_ok(client):
    r = client.get("/budget")
    assert r.status_code == 200
    assert r.get_json() == {"profile": "large"}


def test_sum_float(client):
    r = client.post("/sum", json={"numbers": [1, 2, 3.5]})
    assert r.status_code == 200
    assert r.get_json() == {"result": 6.5}


def test_version_ok(client):
    r = client.get("/version")
    assert r.status_code == 200
    assert r.get_json() == {"version": "0.1.0"}


def test_mean_ok(client):
    r = client.post("/mean", json={"numbers": [2, 4, 6]})
    assert r.status_code == 200
    assert r.get_json()["result"] == 4


def test_mean_bad_payload(client):
    r = client.post("/mean", json={"numbers": []})
    assert r.status_code == 400


# --- tests /median ---
def test_median_ok_odd(client):
    resp = client.post("/median", json={"numbers": [1, 3, 7]})
    assert resp.status_code == 200
    assert resp.get_json()["result"] == 3


def test_median_ok_even(client):
    resp = client.post("/median", json={"numbers": [1, 4, 9, 10]})
    assert resp.status_code == 200
    assert resp.get_json()["result"] == 6.5


def test_median_bad_payload(client):
    resp = client.post("/median", json={"numbers": "oops"})
    assert resp.status_code == 400


def test_stats_ok(client):
    r = client.get("/stats")
    assert r.status_code == 200
    j = r.get_json()
    assert "tasks_logged" in j and isinstance(j["tasks_logged"], int)
