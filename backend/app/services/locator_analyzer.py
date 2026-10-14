CANDIDATES={'role_coupon':{'kind':'role','role':'button','name':'Apply coupon'},'testid_coupon':{'kind':'testid','value':'apply-coupon'}}
def propose(failure,dom):
 if failure.get('category')!='locator_not_found' or failure.get('intent')!='apply_coupon':
  return []
 buttons=dom.get('buttons',[]);candidates=[]
 for key,spec in CANDIDATES.items():
  matches=[button for button in buttons if button.get('tag')=='BUTTON' and button.get('role')=='button' and button.get('visible',True) and button.get('enabled',True) and
     (button.get('name')==spec['name'] if spec['kind']=='role' else button.get('testid')==spec['value'])]
  if len(matches)==1 and matches[0].get('name')=='Apply coupon':
   candidates.append({'id':key,'locator':spec,'matches':1,'reason':'Unique coupon button semantics in captured local DOM; full test validation still required'})
 return candidates
