import json,os
from pathlib import Path
from playwright.sync_api import expect
from .pages import __file__ as pages_file

class LocatorFailure(RuntimeError):pass

CANDIDATES={'role_coupon':{'kind':'role','role':'button','name':'Apply coupon'},'testid_coupon':{'kind':'testid','value':'apply-coupon'}}

def test_coupon_locator(page):
 page.get_by_test_id('add-P1').click()
 expect(page.get_by_test_id('subtotal')).to_have_text('1000.00')
 page.get_by_test_id('coupon-input').fill('SAVE10')
 candidate=os.getenv('QA_HEALING_CANDIDATE','')
 snapshot=os.getenv('QA_HEALING_APPROVED_SNAPSHOT','')
 specification=CANDIDATES[candidate] if candidate else json.loads(snapshot)['coupon'] if snapshot else json.loads(Path(pages_file).with_name('locators.json').read_text(encoding='utf-8'))['coupon']
 locator=page.get_by_role(specification['role'],name=specification['name'],exact=True) if specification['kind']=='role' else page.get_by_test_id(specification['value']) if specification['kind']=='testid' else page.locator(specification['value'])
 count=locator.count()
 path=Path(os.environ['QA_EVIDENCE_DIR'])/'test_coupon_locator';path.mkdir(exist_ok=True)
 (path/'locator-check.json').write_text(json.dumps({'locator':specification,'matches':count,'candidate':candidate,'intent':'apply_coupon'},indent=2),encoding='utf-8')
 if count!=1:
  category='locator_not_found' if count==0 else 'ambiguous_locator'
  (path/'failure-kind.json').write_text(json.dumps({'category':category,'intent':'apply_coupon','matches':count}),encoding='utf-8')
  raise LocatorFailure('LOCATOR_NOT_FOUND' if count==0 else 'AMBIGUOUS_LOCATOR')
 if not locator.is_visible() or not locator.is_enabled():raise LocatorFailure('LOCATOR_NOT_ACTIONABLE')
 locator.click()
 expect(page.get_by_test_id('payable')).to_have_text('900.00')
 expect(page.get_by_test_id('message')).to_have_text('Coupon applied')
