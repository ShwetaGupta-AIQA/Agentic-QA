def score(evidence):
 if any(value is None for value in [evidence.critical_defects_open,evidence.high_defects_open,evidence.risk_level,evidence.unresolved_regression_risks]):
  return None
 level={'low':0,'medium':10,'high':30}[evidence.risk_level]
 return min(100,evidence.critical_defects_open*50+evidence.high_defects_open*5+level+evidence.unresolved_regression_risks*5)
