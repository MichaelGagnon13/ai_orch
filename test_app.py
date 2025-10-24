import pytest
from app import app

@pytest.fixture
def client():
    return app.test_client()

def test_sum_ok(client):
    response = client.post('/sum', json={'numbers': [1, 2, 3]})
    assert response.status_code == 200
    assert response.get_json()['result'] == 6


def test_health_ok(client):
    resp = client.get('/health')
    assert resp.status_code == 200
    assert resp.get_json() == {'status': 'ok'}


def test_sum_bad_payload(client):
    r = client.post('/sum', json={'numbers':'oops'})
    assert r.status_code == 400
    assert 'error' in r.get_json()


def test_budget_ok(client):
    r = client.get('/budget')
    assert r.status_code == 200
    assert r.get_json() == {'profile': 'large'}
