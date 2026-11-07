from playwright.sync_api import sync_playwright
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox']);page=b.new_page(viewport={'width':1440,'height':1100});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('file:///home/sandbox/repo/artifacts/utility-comparison-20261107/cli-smoke/report.html');page.wait_for_timeout(200)
 page.locator('#utility-science-panel').scroll_into_view_if_needed();page.screenshot(path='/downloads/utility-comparison/science-desktop.png');print('desktop overflow',page.evaluate('document.documentElement.scrollWidth>innerWidth'),'errors',errors)
 page.select_option('#science-schedule','95M-final');print('domain text',page.locator('#utility-science-grid').inner_text());page.screenshot(path='/downloads/utility-comparison/science-95M.png');assert '30 domain failures' in page.locator('#utility-science-grid').inner_text()
 page.set_viewport_size({'width':320,'height':1100});page.locator('#utility-science-panel').scroll_into_view_if_needed();page.screenshot(path='/downloads/utility-comparison/science-320.png');print('mobile overflow',page.evaluate('document.documentElement.scrollWidth>innerWidth'));assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
 page.select_option('#science-law','bounded_ewma_mixture');assert '23 domain failures' in page.locator('#utility-science-grid').inner_text();assert errors==[];b.close()
