import json
from unittest.mock import MagicMock, patch
import httpx
import pytest
from pydantic import ValidationError
from app.agent import AgentResult, generate
from app.main import app
from fastapi.testclient import TestClient

VALID = dict(scenarios=['Accept valid coupon'], ambiguities=['Clarify expiry'], risks=['Incorrect discount'], summary='Review coupon rules before test design')

@pytest.fixture
def llm(monkeypatch):
    monkeypatch.setenv('QA_MODEL_MODE', 'llm')
    monkeypatch.setenv('QA_LLM_BASE_URL', 'https://example.invalid/v1')
    monkeypatch.setenv('QA_LLM_API_KEY', 'test-secret')
    monkeypatch.setenv('QA_LLM_MODEL', 'test-model')

@pytest.mark.parametrize('changes', [{'scenarios': []}, {'scenarios': ['   ']}, {'risks': ['']}, {'summary': ' '}, {'approved': True}])
def test_invalid_output_rejected(changes):
    with pytest.raises(ValidationError):
        AgentResult.model_validate(VALID | changes)

def test_demo_calls_no_provider(monkeypatch):
    monkeypatch.setenv('QA_MODEL_MODE', 'demo')
    with patch('app.agent.httpx.Client') as provider:
        result, mode = generate('Add products to the cart')
        provider.assert_not_called()
    assert mode == 'demo' and 'Add item to cart' in result.scenarios

@pytest.mark.parametrize('fenced', [False, True])
def test_llm_adapter_validates_json(llm, fenced):
    content = json.dumps(VALID)
    if fenced:
        content = '```json\n' + content + '\n```'
    response = MagicMock()
    response.json.return_value = {'choices': [{'message': {'content': content}}]}
    with patch('app.agent.httpx.Client') as factory:
        client = factory.return_value.__enter__.return_value
        client.post.return_value = response
        result, mode = generate('Apply coupon during checkout')
        payload = client.post.call_args.kwargs['json']
    assert mode == 'llm' and result.summary == VALID['summary']
    assert payload['model'] == 'test-model'
    assert payload['messages'][1]['content'] == 'Apply coupon during checkout'

def test_missing_config_fails(monkeypatch):
    monkeypatch.setenv('QA_MODEL_MODE', 'llm')
    monkeypatch.delenv('QA_LLM_API_KEY', raising=False)
    with pytest.raises(ValueError, match='configuration'):
        generate('Apply coupon during checkout')

def test_unknown_mode_fails(monkeypatch):
    monkeypatch.setenv('QA_MODEL_MODE', 'typo')
    with pytest.raises(ValueError, match='QA_MODEL_MODE'):
        generate('Apply coupon during checkout')

@pytest.mark.parametrize('failure', [ValueError('invalid JSON test-secret'), httpx.ReadTimeout('timeout test-secret')])
def test_provider_failures_return_safe_error(llm, failure):
    with patch('app.workflow.generate', side_effect=failure):
        response = TestClient(app).post('/workflows', json={'requirement': 'Apply coupon during checkout'})
    assert response.status_code == 502
    assert 'test-secret' not in response.text
