from fastapi.testclient import TestClient
from app.main import app
from app.analyzer import analyze

client = TestClient(app)

def test_health():
    assert client.get("/health").json()["status"] == "ok"

def test_coupon():
    result = client.post("/requirements/analyze", json={"requirement": "Apply a coupon during checkout"})
    assert result.status_code == 200
    assert "Reject expired coupon" in result.json()["scenarios"]

def test_empty_rejected():
    assert client.post("/requirements/analyze", json={"requirement": ""}).status_code == 422

def test_short_rejected():
    assert client.post("/requirements/analyze", json={"requirement": "cart"}).status_code == 422

def test_cart():
    assert "Add item to cart" in analyze("Add a product to cart")["scenarios"]

def test_unknown_requires_review():
    assert analyze("Customer edits their profile")["status"] == "needs_review"

def test_deduplicated():
    x = analyze("Cart and checkout cart")
    assert len(x["scenarios"]) == len(set(x["scenarios"]))

def test_mode():
    assert analyze("Apply a coupon")["mode"] == "rule_based"


def test_whitespace_rejected():
    assert client.post("/requirements/analyze", json={"requirement": " " * 20}).status_code == 422

def test_trimmed_length_rejected():
    assert client.post("/requirements/analyze", json={"requirement": "       cart       "}).status_code == 422

def test_no_substring_feature_match():
    assert analyze("Customer buys a cartoon book")["scenarios"] == []

def test_repeat_cart_product():
    assert "Add the same product twice" in analyze("Add items to the cart")["scenarios"]

def test_direct_blank_rejected():
    import pytest
    with pytest.raises(ValueError):
        analyze("   ")

def test_excess_length_rejected():
    assert client.post("/requirements/analyze", json={"requirement": "x" * 5001}).status_code == 422
