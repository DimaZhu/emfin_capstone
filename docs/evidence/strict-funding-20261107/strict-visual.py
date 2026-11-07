from playwright.sync_api import sync_playwright
from pathlib import Path
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox']);page=b.new_page(viewport={'width':1440,'height':1050});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 for name in ['confirm','empirical-current','95M-final']:
  page.goto('file:///home/sandbox/repo/artifacts/strict-funding-20261107/corrected/'+name+'/report.html');page.wait_for_timeout(200)
  print(name,'errors',errors,'overflow',page.evaluate('document.documentElement.scrollWidth>innerWidth'))
  page.locator('#strict-panel').scroll_into_view_if_needed();page.screenshot(path='/downloads/strict-funding/'+name+'-desktop.png');page.set_viewport_size({'width':320,'height':1150});print(name,'mobile overflow',page.evaluate('document.documentElement.scrollWidth>innerWidth'));page.locator('#strict-panel').scroll_into_view_if_needed();page.screenshot(path='/downloads/strict-funding/'+name+'-320.png');page.set_viewport_size({'width':1440,'height':1050})
 b.close()
