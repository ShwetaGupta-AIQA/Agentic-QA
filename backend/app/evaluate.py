"""Small labeled demo-mode evaluation; no LLM accuracy claims."""
import json
import os
from .agent import generate

CASES = [
    ('Apply coupon during checkout', ['Reject expired coupon', 'Reject checkout with empty cart'], True),
    ('Add products to shopping cart', ['Add item to cart', 'Reject quantity above stock'], False),
    ('Customer edits their profile', ['Clarify requirement before designing executable tests'], True),
]

def evaluate():
    if os.getenv('QA_MODEL_MODE', 'demo').lower() != 'demo':
        raise ValueError('This labeled baseline evaluation requires demo mode')
    results = []
    for requirement, expected, review in CASES:
        analysis, mode = generate(requirement)
        passed = all(title in analysis.scenarios for title in expected) and bool(analysis.ambiguities) == review
        results.append({'requirement': requirement, 'passed': passed, 'mode': mode})
    return {'dataset': 'demo-v1', 'passed': sum(case['passed'] for case in results), 'total': len(results), 'cases': results}

if __name__ == '__main__':
    report = evaluate()
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['passed'] == report['total'] else 1)
