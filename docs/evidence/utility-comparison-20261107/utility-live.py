import subprocess,time,json,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path('/home/sandbox/repo');log=open('/tmp/strict-live-server.log','w');server=subprocess.Popen(['python3','-m','emfin_v2.explorer','--port','8779'],cwd=root,stdout=log,stderr=log)
try:
 for _ in range(80):
  try:urllib.request.urlopen('http://127.0.0.1:8779/',timeout=1);break
  except Exception:time.sleep(.25)
 with sync_playwright() as p:
  b=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox']);page=b.new_page(viewport={'width':1440,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.goto('http://127.0.0.1:8779/');page.locator('#funding_mode').evaluate("el => {let p=el.parentElement;while(p){if(p.tagName==='DETAILS')p.open=true;p=p.parentElement}}");page.select_option('#objective_kind','hara_payment_floor');page.select_option('#funding_mode','pay_all_99');page.click('#apply');page.wait_for_function("!document.getElementById('apply').disabled",timeout=30000)
  print('strict result',page.locator('#strict-results').inner_text());print('mode',page.evaluate('data.controls.funding_mode'),'utility',page.evaluate('data.controls.objective_kind'),'errors',errors);assert page.evaluate('data.dashboard.native_utility.gamma')==9.7
  assert page.evaluate('data.controls.funding_mode')=='pay_all_99';assert page.evaluate('data.dashboard.funding_mode')=='pay_all_99'
  before=page.evaluate('data');Path('/tmp/strict-live.json').write_text(json.dumps(before))
  html=page.content().replace('const STATIC=false','const STATIC=true');Path('/downloads/strict-funding/live-export.html').write_text(html)
  page.select_option('#radius_calibration_mode','past_empirical');page.click('#apply');page.wait_for_function("!document.getElementById('apply').disabled",timeout=30000)
  assert page.evaluate('data.dashboard.radius_calibration.budget_conflict');print('empirical:',page.locator('#radius-note').inner_text());page.locator('#strict-panel').scroll_into_view_if_needed();page.screenshot(path='/downloads/utility-comparison/live-empirical.png')
  page.set_viewport_size({'width':320,'height':1100});assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
  # Native full-config route uses the measured coarse config; controls survive import.
  cfg=json.loads((root/'artifacts/strict-funding-20261107/corrected/pilot/results.json').read_text())['config']
  r=page.request.post('http://127.0.0.1:8779/run-config',data=cfg);print('run-config',r.status);assert r.status==200;obj=r.json();assert obj['controls']['funding_mode']=='pay_all_99'
  assert obj['dashboard']['strict_funding']['paths']==600
  b.close()
finally:server.terminate();server.wait(timeout=5);log.close()
