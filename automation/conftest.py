import os,json
from pathlib import Path
import pytest
import httpx
from playwright.sync_api import sync_playwright

@pytest.fixture
def api():
 with httpx.Client(base_url=os.environ['QA_SUT_URL'],timeout=10) as client:
  response=client.post('/fixtures/reset',json={'defect':os.getenv('QA_VERIFY_DEFECT')=='1'})
  response.raise_for_status();yield client

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item,call):
 outcome=yield
 report=outcome.get_result();setattr(item,'report_'+report.when,report)

@pytest.fixture
def page(api,request):
 directory=Path(os.environ['QA_EVIDENCE_DIR'])/request.node.name;directory.mkdir(exist_ok=True)
 with sync_playwright() as playwright:
  browser=playwright.chromium.launch(headless=True)
  context=browser.new_context();context.tracing.start(screenshots=True,snapshots=True,sources=True)
  page=context.new_page();page.set_default_timeout(5000)
  page.goto(os.environ['QA_SUT_URL'])
  yield page
  report=getattr(request.node,'report_call',None)
  if report and report.failed:
   page.screenshot(path=str(directory/'failure.png'),full_page=True)
   (directory/'dom.html').write_text(page.content(),encoding='utf-8')
   buttons=page.locator('button').evaluate_all("(elements)=>elements.map(e=>({tag:e.tagName,role:e.getAttribute('role')||'button',name:e.getAttribute('aria-label')||e.textContent.trim(),testid:e.getAttribute('data-testid'),id:e.id,visible:e.getClientRects().length>0,enabled:!e.disabled}))")
   (directory/'dom.json').write_text(json.dumps({'buttons':buttons},indent=2),encoding='utf-8')
  context.tracing.stop(path=str(directory/'trace.zip'));context.close();browser.close()
