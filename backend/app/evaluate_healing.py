import argparse,json
from .services.locator_analyzer import propose
from .services.suite_registry import ROOT
def evaluate():
 data=json.loads((ROOT/'data/evaluation/healing_cases.json').read_text(encoding='utf-8'));rows=[]
 for sample in data:
  candidates=propose({'category':sample['category'],'intent':'apply_coupon'},{'buttons':sample['buttons']})
  rows.append({'id':sample['id'],'expected_eligible':sample['eligible'],'proposals':len(candidates),'correct':bool(candidates)==sample['eligible']})
 positives=[row for row in rows if row['expected_eligible']]
 return {'dataset':'locator-policy-v1','samples':len(rows),'correct':sum(row['correct'] for row in rows),
  'valid_proposal_percent':100*sum(row['correct'] for row in positives)/len(positives),
  'ineligible_proposals':sum(row['proposals']>0 for row in rows if not row['expected_eligible']),
  'scope':'Labeled synthetic DOM snapshots. Browser validation rates and human approval checks are separately reported; this is not general self-healing accuracy.','results':rows}
if __name__=='__main__':
 from pathlib import Path
 parser=argparse.ArgumentParser();parser.add_argument('--output');args=parser.parse_args();result=evaluate();text=json.dumps(result,indent=2)
 if args.output:Path(args.output).write_text(text+'\n',encoding='utf-8')
 print(text)
