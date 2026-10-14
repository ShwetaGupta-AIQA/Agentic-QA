"""Reproducible policy evaluation on labeled synthetic scenarios; no authorization."""
import json
from datetime import datetime,timezone,timedelta
from pathlib import Path
from .models.release import ReleaseEvidence
from .services.quality_gates import evaluate
from .services.evidence_aggregator import POLICY_FILE

def run():
 now=datetime.now(timezone.utc);timestamp=now.isoformat();policy=json.loads(POLICY_FILE.read_text())
 base=dict(release_id='synthetic-evaluation',tests_total=100,tests_passed=100,tests_failed=0,tests_errors=0,tests_skipped=0,tests_blocked=0,requirement_coverage=100.0,critical_defects_open=0,high_defects_open=0,risk_level='low',unresolved_regression_risks=0,oldest_execution_at=timestamp,review_at=timestamp,execution_approved=True,contract_matches=True,execution_complete=True,source_ids=['synthetic:labeled-fixture','policy:'+policy['version']])
 cases=[('healthy',{},'GO'),('residual-high',dict(high_defects_open=1),'CONDITIONAL_GO'),('residual-risk',dict(risk_level='medium'),'CONDITIONAL_GO'),('critical',dict(critical_defects_open=1),'NO_GO'),('missing-review',dict(critical_defects_open=None,high_defects_open=None,risk_level=None,review_at=None),'NO_GO'),('low-pass',dict(tests_passed=94,tests_failed=6),'NO_GO'),('low-coverage',dict(requirement_coverage=89.0),'NO_GO'),('skipped',dict(tests_passed=97,tests_skipped=3),'NO_GO'),('blocked',dict(tests_passed=99,tests_blocked=1),'NO_GO'),('stale',dict(oldest_execution_at=(now-timedelta(hours=25)).isoformat()),'NO_GO'),('unapproved',dict(execution_approved=False),'NO_GO'),('wrong-contract',dict(contract_matches=False),'NO_GO')]
 results=[];blocking=0;enforced=0;references=0;totalgates=0
 for name,changes,expected in cases:
  report=evaluate(ReleaseEvidence(**(base|changes)),policy,now)
  blocked=any(g['blocking'] and g['status']!='PASS' for g in report['gates'])
  blocking+=blocked;enforced+=blocked and report['recommendation']=='NO_GO'
  totalgates+=len(report['gates']);references+=sum(bool(g['source_ids']) for g in report['gates'])
  results.append(dict(case=name,expected=expected,actual=report['recommendation'],correct=report['recommendation']==expected))
 return dict(scope='Labeled synthetic policy fixtures only; live provenance verified separately',cases=results,correct=sum(c['correct'] for c in results),total=len(results),blocking_cases=blocking,blocking_enforced=enforced,blocking_enforcement_percent=100*enforced/blocking,referenced_gates=references,total_gates=totalgates,synthetic_gate_reference_percent=100*references/totalgates,decision_types=sorted(set(c['actual'] for c in results)))
if __name__=='__main__':
 result=run();target=Path(__file__).resolve().parents[2]/'reports/benchmarks/release-evaluation.json';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='cases'}));assert result['correct']==result['total']
