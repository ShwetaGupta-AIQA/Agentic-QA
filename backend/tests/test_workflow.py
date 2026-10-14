from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_approval_lifecycle(monkeypatch):
    monkeypatch.setenv('QA_MODEL_MODE', 'demo')
    r = client.post('/workflows', json={'requirement':'Apply coupon during checkout'})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data['status'] == 'awaiting_approval'
    assert data['mode'] == 'demo'
    assert data['analysis']['scenarios']
    run_id = data['run_id']
    assert client.get(f'/workflows/{run_id}').status_code == 200
    done = client.post(f'/workflows/{run_id}/decision', json={'decision':'approve'})
    assert done.status_code == 200, done.text
    assert done.json()['status'] == 'approved'
    assert client.post(f'/workflows/{run_id}/decision', json={'decision':'approve'}).status_code == 409

def test_rejection(monkeypatch):
    monkeypatch.setenv('QA_MODEL_MODE', 'demo')
    run_id = client.post('/workflows', json={'requirement':'Add products to shopping cart'}).json()['run_id']
    r = client.post(f'/workflows/{run_id}/decision', json={'decision':'reject'})
    assert r.json()['status'] == 'rejected'

def test_invalid_requirement():
    assert client.post('/workflows', json={'requirement':'short'}).status_code == 422

def test_unknown_run():
    assert client.get('/workflows/not-a-run').status_code == 404


def test_invalid_decision_does_not_resume(monkeypatch):
    monkeypatch.setenv('QA_MODEL_MODE', 'demo')
    run = client.post('/workflows', json={'requirement': 'Apply coupon during checkout'}).json()
    assert client.post(f"/workflows/{run['run_id']}/decision", json={'decision': 'autoapprove'}).status_code == 422
    assert client.get(f"/workflows/{run['run_id']}").json()['status'] == 'awaiting_approval'

def test_artifact_requires_approval(monkeypatch):
    monkeypatch.setenv('QA_MODEL_MODE', 'demo')
    run = client.post('/workflows', json={'requirement': 'Apply coupon during checkout'}).json()
    url = f"/workflows/{run['run_id']}"
    assert client.get(url + '/artifact').status_code == 409
    client.post(url + '/decision', json={'decision': 'approve'})
    assert client.get(url + '/artifact').json()['status'] == 'approved'

def test_rejected_artifact_blocked(monkeypatch):
    monkeypatch.setenv('QA_MODEL_MODE', 'demo')
    run = client.post('/workflows', json={'requirement': 'Add products to shopping cart'}).json()
    url = f"/workflows/{run['run_id']}"
    client.post(url + '/decision', json={'decision': 'reject'})
    assert client.get(url + '/artifact').status_code == 409
    assert client.post(url + '/decision', json={'decision': 'approve'}).status_code == 409

def test_resume_does_not_call_model_again(monkeypatch):
    from unittest.mock import patch
    from app.agent import generate
    monkeypatch.setenv('QA_MODEL_MODE', 'demo')
    with patch('app.workflow.generate', wraps=generate) as model:
        run = client.post('/workflows', json={'requirement': 'Apply coupon during checkout'}).json()
        client.post(f"/workflows/{run['run_id']}/decision", json={'decision': 'approve'})
        assert model.call_count == 1

def test_workflow_whitespace_rejected():
    assert client.post('/workflows', json={'requirement': ' ' * 20}).status_code == 422
