from datetime import datetime,timezone
from .risk_scoring import score
def age(timestamp,now):
 try:
  value=datetime.fromisoformat(timestamp.replace('Z','+00:00'))
  if value.tzinfo is None:return None
  return (now-value).total_seconds()/3600
 except (ValueError,AttributeError):return None

def evaluate(evidence,policy,now=None):
 now=now or datetime.now(timezone.utc);gates=[]
 def gate(key,value,passed,threshold,remediation,blocking=True):
  gates.append({'id':key,'status':'UNKNOWN' if value is None else 'PASS' if passed else 'FAIL','observed':value,'policy':threshold,'blocking':blocking,
   'source_ids':evidence.source_ids,'remediation':remediation})
 total=evidence.tests_total
 gate('executed_tests',total,total is not None and total>0,'At least one reconciled executed test','Run approved suites and supply complete execution records')
 rate=100*evidence.tests_passed/total if total and evidence.tests_passed is not None else None
 gate('pass_rate',rate,rate is not None and rate>=policy['pass_rate_min'],f">= {policy['pass_rate_min']}%",'Resolve failed assertions and rerun affected approved suites')
 gate('coverage',evidence.requirement_coverage,evidence.requirement_coverage is not None and evidence.requirement_coverage>=policy['coverage_min'],f">= {policy['coverage_min']}% execution coverage",'Execute missing mapped requirement suites')
 gate('critical_defects',evidence.critical_defects_open,evidence.critical_defects_open is not None and evidence.critical_defects_open<=policy['critical_open_max'],f"<= {policy['critical_open_max']} open",'Obtain reviewed defect evidence and resolve all open critical defects')
 gate('high_defects',evidence.high_defects_open,evidence.high_defects_open is not None and evidence.high_defects_open<=policy['high_open_max'],f"<= {policy['high_open_max']} open",'Review and reduce high-severity defect backlog')
 skipped=100*evidence.tests_skipped/total if total and evidence.tests_skipped is not None else None
 gate('skipped',skipped,skipped is not None and skipped<=policy['skipped_percent_max'],f"<= {policy['skipped_percent_max']}%",'Investigate skipped tests and supply execution evidence')
 gate('blocked',evidence.tests_blocked,evidence.tests_blocked is not None and evidence.tests_blocked<=policy['blocked_max'],f"<= {policy['blocked_max']}",'Unblock missing selected test results')
 gate('complete',evidence.execution_complete,evidence.execution_complete is True,'Complete terminal execution records, no errors/timeouts','Resolve infrastructure failures and rerun; incomplete evidence is not a pass')
 gate('approved_suites',evidence.execution_approved,evidence.execution_approved is True,'Human-approved registered suites','Use newly recorded approved suite executions')
 gate('contract',evidence.contract_matches,evidence.contract_matches is True,'commerce-v1 execution and manifest match','Reassess against a matching reviewed SUT contract')
 for key,timestamp in [('execution_freshness',evidence.oldest_execution_at),('review_freshness',evidence.review_at)]:
  hours=age(timestamp,now)
  passed=hours is not None and -policy['future_clock_tolerance_minutes']/60<=hours<=policy['freshness_hours']
  gate(key,hours,passed,f"<= {policy['freshness_hours']}h; no unexplained future timestamp",'Obtain fresh execution and authorized defect/risk review evidence')
 risk=score(evidence)
 gate('risk',risk,risk is not None and risk<=policy['risk_score_max'],f"<= {policy['risk_score_max']} policy points",'Investigate unresolved regression risks; score is a deterministic policy index')
 advisory=(evidence.high_defects_open or 0)>0 or (evidence.unresolved_regression_risks or 0)>0 or evidence.risk_level in ['medium','high']
 gate('residual_risk',bool(advisory),not advisory,'No residual high defects or unresolved/medium risks','Document and explicitly acknowledge residual conditions',False)
 blocked=any(gate['blocking'] and gate['status']!='PASS' for gate in gates)
 return {'recommendation':'NO_GO' if blocked else 'CONDITIONAL_GO' if advisory else 'GO','pass_rate':round(rate,2) if rate is not None else None,'risk_score':risk,
  'gates':gates,'conditions':[gate['remediation'] for gate in gates if not gate['blocking'] and gate['status']!='PASS']}
