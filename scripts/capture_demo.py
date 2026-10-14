"""Record synthetic app views without showing or logging private credentials."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
def main():
 login=json.loads((ROOT/'.secrets/demo-login.json').read_text());images=ROOT/'docs/screenshots';images.mkdir(parents=True,exist_ok=True);videos=ROOT/'docs/demo';videos.mkdir(parents=True,exist_ok=True)
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True)
  context=browser.new_context(http_credentials=login,viewport={'width':1440,'height':1000},record_video_dir=str(ROOT/'reports/deployment-video'),record_video_size={'width':1440,'height':1000})
  page=context.new_page();page.goto('http://127.0.0.1:8080/operations');page.get_by_text('checkpoints: postgresql',exact=True).wait_for();page.screenshot(path=str(images/'operations.png'),full_page=True);page.wait_for_timeout(1500)
  page.goto('http://127.0.0.1:8080/executions');page.get_by_role('heading',name='Test Execution',exact=False).wait_for();page.screenshot(path=str(images/'executions.png'),full_page=True);page.wait_for_timeout(1500)
  page.goto('http://127.0.0.1:8080/releases');page.get_by_role('button',name='deployment-verified: NO_GO / awaiting_review').first.click();page.get_by_role('heading',name='deployment-verified: NO GO').wait_for();page.screenshot(path=str(images/'release-readiness.png'),full_page=True);page.wait_for_timeout(2000)
  video=page.video;context.close();video.save_as(str(videos/'deployment.webm'));browser.close()
 print('Synthetic screenshots and short demo recorded; no credentials displayed')
if __name__=='__main__':main()
