"""Labeled deterministic evaluation; no live LLM or semantic-quality claims."""
import argparse
import json
import os
from pathlib import Path
from .agent import generate
from .agents.test_design_agent import design, criteria_for
from .agents.test_data_agent import generate_data
from .models.test_cases import TestCase
from .models.test_data import TestData
from .services.coverage_evaluator import evaluate_coverage

def evaluate():
    if os.getenv('QA_MODEL_MODE','demo') != 'demo':
        raise ValueError('Labeled Test design baseline evaluation requires demo mode')
    dataset=json.loads((Path(__file__).resolve().parents[1]/'data/design_benchmark_dataset.json').read_text(encoding='utf-8'))
    rows=[]
    for sample in dataset:
        try:
            analysis,mode=generate(sample['requirement'])
            criteria=criteria_for(sample['requirement'])
            cases=design(sample['requirement'],analysis.model_dump(),True,mode,criteria)
            data=generate_data(sample['requirement'],cases,mode)
            for case in cases: TestCase.model_validate(case)
            for item in data: TestData.model_validate(item)
            titles=' '.join(case['title'].lower() for case in cases)
            covered=sum(all(term in titles for term in terms) for terms in sample['labels'].values())
            coverage=round(100*covered/len(sample['labels']),2)
            metrics=evaluate_coverage(cases,criteria,analysis.scenarios,data)
            passed=len(cases)>=sample['minimum_cases'] and metrics['traceability_percent']==100 and metrics['duplicate_percent']<=10 and coverage>=80
            rows.append({'id':sample['id'],'schema_valid':True,'passed':passed,'labeled_title_coverage_percent':coverage,'metrics':metrics})
        except Exception as exc:
            rows.append({'id':sample['id'],'schema_valid':False,'passed':False,'error_kind':type(exc).__name__})
    return {'dataset':'design_benchmark-demo-v1','mode':'demo','sample_count':len(rows),'passed':sum(row['passed'] for row in rows),
            'schema_valid_output_percent':round(100*sum(row['schema_valid'] for row in rows)/len(rows),2),
            'scope':'Three synthetic demo examples. Label coverage matches candidate titles only; it is not semantic acceptance validation, live model accuracy or execution coverage.', 'results':rows}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output');args=parser.parse_args()
    report=evaluate();text=json.dumps(report,indent=2)
    if args.output: Path(args.output).write_text(text+'\n',encoding='utf-8')
    print(text)
    raise SystemExit(0 if report['passed']==report['sample_count'] else 1)
