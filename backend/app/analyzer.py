import re

def analyze(text: str) -> dict:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Requirement cannot be empty")
    text = text.strip()
    lower = text.lower()
    scenarios = []
    ambiguities = []
    if re.search(r"\bcoupons?\b", lower):
        scenarios += ["Accept valid coupon", "Reject expired coupon", "Reject invalid coupon", "Verify discount calculation"]
        if not re.search(r"\b(discount|percentage|percent|amount)\b", lower):
            ambiguities.append("Discount calculation rule is unspecified")
        if not re.search(r"\b(expir(?:y|ation|ed)|validity)\b", lower):
            ambiguities.append("Coupon expiry behavior is unspecified")
    if re.search(r"\bcheckout\b", lower):
        scenarios += ["Checkout with valid cart", "Reject checkout with empty cart"]
    if re.search(r"\bcarts?\b", lower):
        scenarios += ["Add item to cart", "Add the same product twice", "Remove item from cart", "Reject quantity above stock", "Verify cart total"]
    if not scenarios:
        ambiguities.append("No supported e-commerce feature identified; human review required")
    return {"requirement": text.strip(), "scenarios": list(dict.fromkeys(scenarios)), "ambiguities": ambiguities, "status": "needs_review" if ambiguities else "analyzed", "mode": "rule_based"}
