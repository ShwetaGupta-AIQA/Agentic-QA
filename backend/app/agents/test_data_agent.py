import re
from decimal import Decimal, ROUND_HALF_UP
from ..models.test_data import DataOutput, TestData
from ..services.model_adapter import structured_call

def generate_data(requirement, cases, mode):
    if not cases:
        raise ValueError('Validated cases with stable IDs are required')
    if mode == 'llm':
        output = structured_call('Create synthetic data for every supplied test case. '
            'Use supplied test_case_id values only. Include expiry timestamps and redemption history where relevant. '
            'Mark assumptions needs_review. Use only the allowed fixture fields. Never use real customer data.',
            {'requirement': requirement, 'test_cases': cases}, DataOutput)
    else:
        rate = re.search(r'(\d+(?:\.\d+)?)\s*%', requirement)
        percent = Decimal(rate[1]) if rate and Decimal(rate[1]) <= 100 else None
        datasets = []
        for case in cases:
            title = case['title'].lower()
            total = Decimal('0') if 'below zero' in title else Decimal('1000')
            values = {'customer_id': 'synthetic-customer-001', 'scenario': case['title']}
            if 'coupon' in requirement.lower():
                values.update(coupon='SAVE10', cart_total=str(total), redemption_history=[])
                if 'invalid coupon' in title: values['coupon'] = 'INVALID'
                if 'expired coupon' in title: values['coupon'] = 'EXPIRED10'
                if 'second use' in title:
                    values['coupon'] = 'USED10'
                    values['redemption_history'] = ['USED10']
                if 'expir' in title:
                    values['expires_at_utc'] = '2030-01-02T00:00:00Z'
                    values['now_utc'] = ('2030-01-01T23:59:59Z' if 'before' in title else
                                         '2030-01-02T00:00:00Z' if 'exactly' in title else '2030-01-02T00:00:01Z')
                if percent is not None and case['category'] != 'negative':
                    discount = (total * percent / 100).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
                    values.update(discount_percent=str(percent), expected_discount=str(discount), expected_payable=str(max(Decimal(0), total - discount)))
            else:
                values.update(quantity=1, stock=10)
            datasets.append({'test_case_id': case['id'], 'kind': {'positive': 'valid', 'negative': 'invalid', 'boundary': 'edge'}[case['category']],
                'values': values, 'expected_behavior': case['expected_result']['description'],
                # Dates, cart eligibility, rounding and tax order are synthetic assumptions.
                'needs_review': True})
        output = DataOutput.model_validate({'datasets': datasets})
    case_ids = {case['id'] for case in cases}
    if {data.test_case_id for data in output.datasets} != case_ids:
        raise ValueError('Test data must cover exactly the supplied case IDs')
    return [TestData(**data.model_dump(), id=f'TD-{i:03}').model_dump() for i, data in enumerate(output.datasets, 1)]
