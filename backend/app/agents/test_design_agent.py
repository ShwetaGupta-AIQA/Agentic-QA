import re
from ..models.test_cases import Criterion, DesignOutput, TestCase
from ..services.model_adapter import structured_call

def criteria_for(requirement):
    clauses = [part.strip() for part in re.split(r';|\.(?=\s|$)|,\s*(?:and\s+)?', requirement) if part.strip()]
    return [Criterion(id=f'AC-{i:03}', text=text).model_dump() for i, text in enumerate(clauses, 1)]

def design(requirement, analysis, approved, mode, criteria):
    if not approved or not analysis.get('scenarios') or not criteria:
        raise ValueError('Complete approved requirements are required')
    scenarios = {f'SC-{i:03}': title for i, title in enumerate(analysis['scenarios'], 1)}
    if mode == 'llm':
        output = structured_call('Design candidate positive, negative and boundary tests from the approved requirement. '
            'Use supplied scenario and criterion IDs only. Mark uncertain outcomes needs_review. '
            'Do not invent confirmed rules or approve your own output.',
            {'requirement': requirement, 'analysis': analysis, 'scenarios': scenarios, 'criteria': criteria}, DesignOutput)
    else:
        def refs(pattern):
            found = [c['id'] for c in criteria if re.search(pattern, c['text'], re.I)]
            return found or [criteria[0]['id']]
        def scenario(pattern):
            return next((key for key, title in scenarios.items() if re.search(pattern, title, re.I)), next(iter(scenarios)))
        lower = requirement.lower()
        percent = re.search(r'(\d+(?:\.\d+)?)\s*%', requirement)
        confirmed_discount = bool(percent and float(percent[1]) <= 100)
        expiry = bool(re.search(r'expir|midnight', lower))
        once = bool(re.search(r'once|single.use', lower))
        floor = bool(re.search(r'(?:below|minimum|floor).*0', lower))
        rows = []
        if re.search(r'\bcoupons?\b', lower):
            rows = [
                ('Apply valid coupon and verify discount', 'positive', 'discount|coupon',
                 'Confirm ' + percent[1] + '% discount on an eligible cart' if confirmed_discount else 'Confirm discount against product rules', not confirmed_discount, refs('%|discount')),
                ('Reject invalid coupon code', 'negative', 'invalid', 'Invalid coupon is rejected without changing the payable amount; confirm product response', True, refs('coupon')),
                ('Reject expired coupon', 'negative', 'expired', 'Expired coupon is rejected; confirm error contract', True, refs('expir|midnight')),
                ('Coupon just before expiry', 'boundary', 'expired', 'Evaluate one second before configured expiry; confirm time precision and eligibility', True, refs('expir|midnight')),
                ('Coupon exactly at expiry', 'boundary', 'expired', 'Confirm whether the exact expiry instant is exclusive or inclusive', True, refs('expir|midnight')),
                ('Reject second use by same customer', 'negative', 'coupon', 'Reject a second redemption by the same customer' if once else 'Clarify per-customer redemption limits', not once, refs('once|single.use')),
                ('Payable amount never below zero', 'boundary', 'discount|coupon', 'Payable amount remains at least zero; confirm zero-cart eligibility' if floor else 'Clarify minimum payable amount and zero-cart eligibility', True, refs('below|minimum|floor')),
                ('Checkout successfully after discount', 'positive', 'checkout|coupon', 'Checkout uses the confirmed discounted payable amount; confirm rounding and tax order', True, refs('checkout|discount')),
            ]
        else:
            for key, title in scenarios.items():
                category = 'negative' if re.search(r'reject|invalid|empty', title, re.I) else 'positive'
                rows.append((title, category, re.escape(title), 'Confirm expected behavior with product acceptance criteria', True, [criteria[0]['id']]))
        cases = []
        for title, category, match, expected, review, ids in rows:
            cases.append({'title': title, 'category': category, 'priority': 'high', 'scenario_id': scenario(match),
                'criterion_ids': ids, 'preconditions': ['Use an isolated synthetic customer and cart; confirm eligibility'],
                'steps': [{'action': 'Prepare the synthetic fixture linked to this case'},
                          {'action': title}, {'action': 'Compare the observed result to the reviewed expected result'}],
                'expected_result': {'description': expected, 'needs_review': review}})
        output = DesignOutput.model_validate({'cases': cases})
    valid_criteria = {c['id'] for c in criteria}
    result = []
    for index, draft in enumerate(output.cases, 1):
        if draft.scenario_id not in scenarios or not set(draft.criterion_ids) <= valid_criteria:
            raise ValueError('Unknown traceability reference')
        result.append(TestCase(**draft.model_dump(), id=f'TC-{index:03}', requirement_id='REQ-001').model_dump())
    return result
