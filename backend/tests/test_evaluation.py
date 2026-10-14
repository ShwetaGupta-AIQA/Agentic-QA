from app.evaluate import evaluate

def test_labeled_demo_dataset(monkeypatch):
    monkeypatch.setenv('QA_MODEL_MODE', 'demo')
    result = evaluate()
    assert result['passed'] == result['total'] == 3
