def evaluate_coverage(cases, criteria, scenarios, datasets):
    total = len(cases)
    titles = [' '.join(case['title'].lower().split()) for case in cases]
    criterion_ids = {c['id'] for c in criteria}
    scenario_ids = {f'SC-{i:03}' for i in range(1, len(scenarios) + 1)}
    traced = sum(case['requirement_id'] == 'REQ-001' and case['scenario_id'] in scenario_ids and
                 bool(case['criterion_ids']) and set(case['criterion_ids']) <= criterion_ids for case in cases)
    referenced = {ref for case in cases for ref in case['criterion_ids']} & criterion_ids
    linked = {data['test_case_id'] for data in datasets} & {case['id'] for case in cases}
    return {'case_count': total, 'traceability_percent': round(100 * traced / total, 2) if total else 0,
            'duplicate_percent': round(100 * (total - len(set(titles))) / total, 2) if total else 0,
            'criterion_reference_coverage_percent': round(100 * len(referenced) / len(criteria), 2) if criteria else 0,
            'data_link_coverage_percent': round(100 * len(linked) / total, 2) if total else 0,
            'pending_review_count': sum(c['review_status'] == 'pending' or c['expected_result']['needs_review'] for c in cases),
            'note': 'Reference coverage measures linked clauses, not semantic acceptance-criteria coverage or executed tests.'}
